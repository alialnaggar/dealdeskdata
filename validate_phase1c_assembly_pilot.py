"""Preflight one connected configured build. This is a bounded pilot, not a generator."""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import json

import yaml

from validate_phase1c_column_rules import schema_columns
from phase1c_component_units import whole_component_requirements
from validate_phase1c_data_contract import validate_payload
from validate_phase1c_pilot import _day, _instant, _number, add_workdays, validate_pilot


HERE = Path(__file__).resolve().parent
EXTRA_TABLES = ("bom_headers", "bom_lines", "production_requirements", "production_capacity")


def connected_rows(base, extension):
    """Keep the existing eight-table pilot as the source of shared identities."""
    pilot = deepcopy(base)
    pilot["rows"]["products"].extend(deepcopy(extension["product_rows"]))
    pilot["rows"]["inventory"].extend(deepcopy(extension["inventory_rows"]))
    pilot["rows"]["deal_lines"] = [deepcopy(extension["deal_line"])]
    pilot["rows"].update({table: deepcopy(extension[table]) for table in EXTRA_TABLES})
    return pilot


def validate_assembly(base, extension, contract, schema_sql, config):
    expected = {"base", "product_rows", "inventory_rows", "deal_line", *EXTRA_TABLES, "cost_parameters"}
    if set(extension) != expected or extension["base"] != "phase1c_pilot_slice.json":
        return {"errors": ["assembly extension fields or base reference differ"], "findings": [],
                "ready_for_full_generation": False}
    pilot = connected_rows(base, extension)
    core = deepcopy(pilot)
    for table in EXTRA_TABLES:
        del core["rows"][table]
    base_result = validate_pilot(core, contract, schema_sql, config)
    errors = base_result["errors"][:]
    if errors:
        return {"errors": errors, "findings": [], "ready_for_full_generation": False}
    shape = schema_columns(schema_sql)
    for table in EXTRA_TABLES:
        if not isinstance(extension[table], list) or not extension[table]:
            errors.append(f"{table}: nonempty rows required")
            continue
        for row in extension[table]:
            if not isinstance(row, dict) or set(row) != set(shape[table]) or any(
                row[k] is None for k, spec in shape[table].items() if not spec["nullable"]
            ):
                errors.append(f"{table}: fields or required values differ from schema.sql")
    if errors:
        return {"errors": errors, "findings": [], "ready_for_full_generation": False}

    as_of = _instant(pilot["as_of_at"])
    line = extension["deal_line"]
    products = {p["product_id"]: p for p in pilot["rows"]["products"]}
    product = products[line["product_id"]]
    if product["fulfillment_mode"] != "make_to_order":
        errors.append("assembly line must quote a make-to-order product")
    candidates = []
    for bom in extension["bom_headers"]:
        errors.extend(f"{bom['bom_id']}: {e}" for e in validate_payload(
            "configuration_signature", bom["configuration_signature_json"], contract))
        if (bom["finished_product_id"] == product["product_id"] and
            bom["catalog_version"] == product["catalog_version"] and
            bom["configuration_signature_json"] == line["configuration_json"] and
            bom["status"] == "active" and _instant(bom["effective_from"]) <= as_of and
            (bom["effective_to"] is None or as_of < _instant(bom["effective_to"]))):
            candidates.append(bom)
    if len(candidates) != 1:
        errors.append("configured line must select exactly one effective active BOM")
    if errors:
        return {"errors": errors, "findings": [], "ready_for_full_generation": False}
    bom = candidates[0]
    selected_lines = [r for r in extension["bom_lines"] if r["bom_id"] == bom["bom_id"]]
    selected_reqs = [r for r in extension["production_requirements"] if r["bom_id"] == bom["bom_id"] and r["status"] == "active"]
    if not selected_lines or not selected_reqs or any(not r["is_mandatory"] or r["substitute_group_code"] for r in selected_lines):
        errors.append("pilot needs mandatory components and active operations without substitutes")
    if len({r["component_product_id"] for r in selected_lines}) != len(selected_lines):
        errors.append("duplicate component in selected BOM")
    if sorted({r["operation_seq"] for r in selected_reqs}) != list(range(1, max(
        (r["operation_seq"] for r in selected_reqs), default=0) + 1)):
        errors.append("operation sequence has a gap")

    build = _number(line["quantity"])
    output = _number(bom["output_quantity"])
    demand = {}
    material = Decimal(0)
    for row in selected_lines:
        component = products.get(row["component_product_id"])
        if (component is None or component["catalog_version"] != bom["catalog_version"] or
            component["fulfillment_mode"] != "component" or component["is_sellable"] or
            component["stock_uom"] != "component_unit"):
            errors.append(f"{row['bom_line_id']}: invalid component catalogue relationship")
            continue
        per_unit = _number(row["required_quantity_per_output"]) / output / (1 - _number(row["scrap_pct"]) / 100)
        demand[component["product_id"]] = build * per_unit
        material += per_unit * _number(component["standard_cost"])
    stock = pilot["rows"]["inventory"]
    location = config["fulfillment_production_calibration"]["proposed_parameters"]["production_capacity"]["workshop_location"]
    stock_required = whole_component_requirements(demand)
    for component_id in demand:
        relevant = [s for s in stock if s["product_id"] == component_id]
        available = sum((_number(s["quantity_on_hand"]) - _number(s["quantity_allocated"])
                         for s in relevant if s["location_id"] == location and
                         _instant(s["snapshot_at"]) <= as_of and as_of - _instant(s["snapshot_at"]) <= timedelta(hours=24)), Decimal(0))
        if available < stock_required[component_id]:
            errors.append(f"{component_id}: component stock is insufficient at build site")

    capacities = extension["production_capacity"]
    zone = contract["controlled_vocabularies"]["location_codes"][location]["time_zone"]
    horizon = as_of.date() + timedelta(days=config["fulfillment_production_calibration"]
                                            ["proposed_parameters"]["production_capacity"]["horizon_calendar_days"])
    operation_dates = []
    required_hours = {}
    next_day = as_of.date()
    for seq in sorted({r["operation_seq"] for r in selected_reqs}):
        group = [r for r in selected_reqs if r["operation_seq"] == seq]
        needs = {}
        for req in group:
            batches = (build / _number(req["batch_size"])).to_integral_value(rounding=ROUND_CEILING)
            need = batches * _number(req["setup_hours"]) + build * _number(req["hours_per_unit"])
            key = (req["capability_code"], req["resource_type"])
            needs[key] = need
            required_hours[req["requirement_id"]] = need
        date_options = sorted({_day(c["capacity_date"]) for c in capacities if next_day <= _day(c["capacity_date"]) <= horizon})
        chosen = None
        for day in date_options:
            if day.isoweekday() > 5:
                continue
            if all(any(c["location_id"] == location and c["capability_code"] == code and
                       c["resource_type"] == resource and _day(c["capacity_date"]) == day and
                       c["time_zone"] == zone and c["status"] == "active" and
                       _instant(c["snapshot_at"]) <= as_of and as_of - _instant(c["snapshot_at"]) <= timedelta(hours=24) and
                       _number(c["available_capacity_hours"]) - _number(c["allocated_capacity_hours"]) >= need
                       for c in capacities) for (code, resource), need in needs.items()):
                chosen = day
                break
        if chosen is None:
            errors.append(f"operation {seq}: no fresh fitting capacity within horizon")
            break
        operation_dates.append(chosen)
        next_day = add_workdays(chosen, 1, [1, 2, 3, 4, 5])

    params = extension["cost_parameters"]
    labor_hours = sum((_number(r["setup_hours"]) + _number(r["hours_per_unit"]) for r in selected_reqs
                       if r["resource_type"] == "workforce"), Decimal(0))
    labor = labor_hours * _number(params["workforce_cost_eur_per_hour"])
    total_cost = (material + labor) * (1 + _number(params["overhead_fraction"]))
    standard_cost = _number(product["standard_cost"])
    if abs(total_cost - standard_cost) > standard_cost * Decimal("0.05"):
        errors.append("assembled standard cost differs from material, labor and overhead rollup by more than 5%")
    return {"errors": errors, "findings": [] if errors else [{
        "code": "assembly_candidate", "bom_id": bom["bom_id"],
        "build_units": str(build), "component_demand": {k: str(v) for k, v in demand.items()},
        "component_stock_required": {k: str(v) for k, v in stock_required.items()},
        "required_hours": {k: str(v) for k, v in required_hours.items()},
        "operation_dates": [d.isoformat() for d in operation_dates],
        "cost_rollup_eur": str(total_cost.quantize(Decimal("0.01"))),
        "status": "feasible_uncommitted"
    }], "ready_for_full_generation": False}


def main():
    base = json.loads((HERE / "phase1c_pilot_slice.json").read_text())
    extension = json.loads((HERE / "phase1c_assembly_pilot.json").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    result = validate_assembly(base, extension, contract, (HERE / "schema.sql").read_text(), config)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
