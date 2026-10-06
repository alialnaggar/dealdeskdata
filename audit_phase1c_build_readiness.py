"""Audit the draft's evidence gaps without treating structural coverage as readiness.

The current component IDs and costs are synthetic. This audit reports the
specific missing evidence and margin outliers; it never changes calibration.
"""

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import json

import yaml


HERE = Path(__file__).resolve().parent


def audit(portfolio, costs, config):
    products = {p["product_id"]: p for p in portfolio["products"]}
    headers = {b["bom_id"]: b for b in portfolio["bom_headers"]}
    lines = defaultdict(list)
    for line in portfolio["bom_lines"]:
        lines[line["bom_id"]].append(line)

    # Platform membership is already checked by validate_portfolio. Actual
    # electrical/mechanical fit needs explicit per-part specifications.
    required_specs = {
        "compute": ("socket_or_controller_interface", "rated_watts"),
        "storage": ("host_interface", "form_factor"),
        "network_and_power": ("host_interface", "rated_watts"),
        "chassis_and_other": ("supported_form_factor", "power_budget_watts"),
    }
    missing = {}
    for component in (p for p in products.values() if p["fulfillment_mode"] == "component"):
        attrs = component["attributes_json"]
        fields = required_specs.get(attrs.get("component_family"), ())
        absent = [name for name in fields if attrs.get(name) is None]
        if absent:
            missing[component["product_id"]] = absent

    # Even populated fields would need cross-part checks and source evidence;
    # presence alone cannot certify that a configuration fits.
    affected = sorted(bid for bid in lines if bid in headers)
    margin_limits = config["commercial_supply"]["standard_cost"][
        "target_list_margin_percent_by_category"]
    outliers = []
    for row in costs["products"]:
        pid = row["product_id"]
        category = products[pid]["attributes_json"]["category"]
        price = Decimal(str(row["product_list_price_eur"]))
        cost = Decimal(str(row["product_standard_cost_eur"]))
        if price <= 0:
            raise ValueError(f"{pid}: list price must be positive")
        margin = (price - cost) / price * 100
        upper = Decimal(str(margin_limits[category]["p90"]))
        if margin > upper:
            outliers.append({"product_id": pid, "margin_pct": round(float(margin), 2),
                             "proposed_category_p90_pct": float(upper)})
    return {
        "component_specifications_missing": missing,
        "boms_awaiting_detailed_compatibility": affected,
        "margin_outliers_above_proposed_p90": outliers,
        "price_comparability_verified": False,
        "component_sourcing_verified": False,
        "ready_for_full_generation": False,
    }


if __name__ == "__main__":
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    print(json.dumps(audit(portfolio, costs, config), indent=2))
