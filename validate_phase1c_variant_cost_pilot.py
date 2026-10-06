"""Check one product's BOM cost variants against its single catalogue cost.

Illustrative inputs are supplied explicitly. This does not calibrate prices or
generate SQL rows. It follows the reader's one-unit material/labor/overhead
convention and reports whether one standard cost can fit all active variants.
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
import argparse
import json

import yaml


HERE = Path(__file__).resolve().parent


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a monetary number")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("monetary number must be finite")
    return result


def evaluate_cost_pilot(portfolio, pilot, config):
    errors = []
    product_id = pilot.get("product_id")
    products = {row["product_id"]: row for row in portfolio["products"]}
    product = products.get(product_id)
    if product is None or product.get("fulfillment_mode") != "make_to_order":
        return {"errors": ["pilot product must be a make-to-order sellable item"],
                "rollups_eur": {}, "ready_for_full_generation": False}
    headers = [row for row in portfolio["bom_headers"]
               if row["finished_product_id"] == product_id and row["status"] == "active"]
    if not headers:
        errors.append("pilot product has no active BOMs")
    try:
        rate = number(pilot["workforce_cost_eur_per_hour"])
        overhead = number(pilot["overhead_fraction"])
        standard = number(pilot["product_standard_cost_eur"])
        price = number(pilot["product_list_price_eur"])
        component_costs = {key: number(value) for key, value in pilot["component_standard_costs_eur"].items()}
        if (rate <= 0 or standard <= 0 or price <= 0 or not 0 <= overhead < 1 or
            any(value <= 0 for value in component_costs.values())):
            errors.append("pilot rates, costs and list price must be positive; overhead is in [0, 1)")
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return {"errors": ["pilot cost fields are missing or invalid"],
                "rollups_eur": {}, "ready_for_full_generation": False}
    bounds = config["fulfillment_production_calibration"]["proposed_parameters"]["cost_rollup"]
    if not (number(bounds["workforce_cost_eur_per_hour"][0]) <= rate <=
            number(bounds["workforce_cost_eur_per_hour"][2]) and
            number(bounds["overhead_fraction_of_material_plus_labor"][0]) <= overhead <=
            number(bounds["overhead_fraction_of_material_plus_labor"][2])):
        errors.append("labor rate or overhead is outside the proposed calibration bounds")
    chosen = pilot.get("selected_substitutes", {})
    if not isinstance(chosen, dict) or set(chosen) != {row["bom_id"] for row in headers}:
        errors.append("substitute selections must cover exactly the product's active BOMs")
        chosen = {}
    rollups = {}
    for header in headers:
        bom_id = header["bom_id"]
        lines = [row for row in portfolio["bom_lines"] if row["bom_id"] == bom_id]
        groups = defaultdict(list)
        selected = []
        for row in lines:
            if row["substitute_group_code"] is None:
                selected.append(row)
            else:
                groups[row["substitute_group_code"]].append(row)
        selection = chosen.get(bom_id, {})
        if not isinstance(selection, dict) or set(selection) != set(groups):
            errors.append(f"{bom_id}: substitute selections do not match declared groups")
            continue
        for group, candidates in groups.items():
            matches = [row for row in candidates if row["component_product_id"] == selection[group]]
            if len(matches) != 1:
                errors.append(f"{bom_id}: substitute choice for {group} is not a candidate")
            else:
                selected.append(matches[0])
        if any(f"{bom_id}: substitute choice" in error for error in errors):
            continue
        try:
            material = sum((number(row["required_quantity_per_output"]) /
                            number(header["output_quantity"]) /
                            (1 - number(row["scrap_pct"]) / 100) *
                            component_costs[row["component_product_id"]]
                            for row in selected), Decimal(0))
            labor_hours = sum((number(row["setup_hours"]) + number(row["hours_per_unit"])
                               for row in portfolio["production_requirements"]
                               if row["bom_id"] == bom_id and row["status"] == "active"
                               and row["resource_type"] == "workforce"), Decimal(0))
            rollups[bom_id] = (material + labor_hours * rate) * (1 + overhead)
        except (KeyError, TypeError, ValueError, InvalidOperation, ZeroDivisionError):
            errors.append(f"{bom_id}: selected part cost or operation hours are missing or invalid")
    tolerance = number(bounds["finished_standard_cost_rollup_tolerance_pct"]) / 100
    lower = max((value / (1 + tolerance) for value in rollups.values()), default=None)
    upper = min((value / (1 - tolerance) for value in rollups.values()), default=None)
    if lower is not None and upper is not None:
        if lower > upper:
            errors.append("variant costs cannot share one standard cost within tolerance")
        if not lower <= standard <= upper:
            errors.append("the stated product standard cost does not fit every variant")
        if len(rollups) > 1 and standard < max(rollups.values()):
            errors.append("one priced SKU needs a conservative standard cost covering its highest-cost variant")
    if standard >= price:
        errors.append("the stated list price has nonpositive catalogue margin")
    return {
        "errors": errors,
        "rollups_eur": {key: str(value.quantize(Decimal("0.01"))) for key, value in rollups.items()},
        "common_standard_cost_interval_eur": None if lower is None or upper is None else
            [str(lower.quantize(Decimal("0.01"))), str(upper.quantize(Decimal("0.01")))],
        "catalogue_margin_pct": str(((price - standard) / price * 100).quantize(Decimal("0.01"))),
        "ready_for_full_generation": False,
    }


def evaluate_build_cost_draft(portfolio, draft, config):
    """Reuse the single-product cost gate for every offered buildable SKU."""
    products = {row["product_id"] for row in portfolio["products"]
                if row["is_sellable"] and row["fulfillment_mode"] == "make_to_order"}
    rows = draft.get("products")
    if not isinstance(rows, list):
        return {"errors": ["products must be a list"], "products": {},
                "ready_for_full_generation": False}
    ids = [row.get("product_id") for row in rows if isinstance(row, dict)]
    errors = []
    if len(ids) != len(rows) or len(set(ids)) != len(ids) or set(ids) != products:
        errors.append("cost draft must cover each buildable product exactly once")
    components = {row["product_id"] for row in portfolio["products"]
                  if row["fulfillment_mode"] == "component"}
    costs = draft.get("component_standard_costs_eur")
    if not isinstance(costs, dict) or set(costs) != components:
        errors.append("component costs must cover the exact draft component catalogue")
        costs = costs if isinstance(costs, dict) else {}
    results = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("product_id") not in products:
            continue
        pilot = dict(row, component_standard_costs_eur=costs,
                     workforce_cost_eur_per_hour=draft.get("workforce_cost_eur_per_hour"),
                     overhead_fraction=draft.get("overhead_fraction"))
        result = evaluate_cost_pilot(portfolio, pilot, config)
        results[row["product_id"]] = result
        errors.extend(f"{row['product_id']}: {error}" for error in result["errors"])
    return {"errors": errors, "products": results,
            "checked_products": len(results),
            "checked_boms": sum(len(row["rollups_eur"]) for row in results.values()),
            "ready_for_full_generation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot", type=Path)
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text(encoding="utf-8"))
    data = json.loads(args.pilot.read_text(encoding="utf-8"))
    result = (evaluate_build_cost_draft(portfolio, data, config) if "products" in data else
              evaluate_cost_pilot(portfolio, data, config))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
