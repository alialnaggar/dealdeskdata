"""Check one explicitly specified synthetic BOM and every substitute candidate.

This is a rule demonstration, not certification of physical parts or a
catalogue-wide compatibility pass. Real parts need manufacturer evidence.
"""

from collections import defaultdict
from pathlib import Path
import json


HERE = Path(__file__).resolve().parent
SPEC_FIELDS = {
    "compute_kit": {"storage_host_interface", "network_slot_interface", "board_form_factor", "rated_watts"},
    "storage_drive": {"host_interface", "form_factor", "rated_watts"},
    "network_power_kit": {"network_interface", "psu_output_watts", "rated_watts"},
    "enclosure_kit": {"supported_board_form_factors", "supported_drive_form_factors",
                      "drive_slots", "power_budget_watts"},
}


def _positive_number(value):
    return type(value) in (int, float) and value > 0


def validate(portfolio, pilot):
    errors = []
    if pilot.get("purpose") != "synthetic interface and power rule demonstration; no sourced component identities":
        errors.append("pilot must explicitly declare its synthetic evidence boundary")
    bom_id = pilot.get("bom_id")
    headers = {row["bom_id"]: row for row in portfolio["bom_headers"]}
    header = headers.get(bom_id)
    if header is None or header.get("status") != "active" or header.get("output_quantity") != 1:
        return {"errors": errors + ["pilot needs one active single-output BOM"],
                "candidate_results": {}, "synthetic_fit_check_passed": False,
                "ready_for_full_generation": False}
    products = {row["product_id"]: row for row in portfolio["products"]}
    lines = [row for row in portfolio["bom_lines"] if row["bom_id"] == bom_id]
    ids = {row["component_product_id"] for row in lines}
    specs = pilot.get("component_specs")
    if not isinstance(specs, dict) or set(specs) != ids:
        return {"errors": errors + ["pilot specifications must cover exactly the BOM candidates"],
                "candidate_results": {}, "synthetic_fit_check_passed": False,
                "ready_for_full_generation": False}

    roles = defaultdict(list)
    for line in lines:
        cid = line["component_product_id"]
        role = products[cid]["attributes_json"].get("component_role")
        roles[role].append(line)
        spec = specs[cid]
        if not isinstance(spec, dict) or set(spec) != SPEC_FIELDS.get(role, set()):
            errors.append(f"{cid}: required {role} specification fields are incomplete or unexpected")
            continue
        for field in ("rated_watts", "psu_output_watts", "drive_slots", "power_budget_watts"):
            if field in spec and not _positive_number(spec[field]):
                errors.append(f"{cid}: {field} must be positive")
        for field, value in spec.items():
            if field not in {"rated_watts", "psu_output_watts", "drive_slots", "power_budget_watts"}:
                if isinstance(value, list):
                    if not value or any(not isinstance(item, str) or not item for item in value):
                        errors.append(f"{cid}: {field} must contain named values")
                elif not isinstance(value, str) or not value:
                    errors.append(f"{cid}: {field} must be named")
    if errors:
        return {"errors": errors, "candidate_results": {}, "synthetic_fit_check_passed": False,
                "ready_for_full_generation": False}

    expected = {"compute_kit": (1, 1), "storage_drive": (1, 2),
                "network_power_kit": (2, 1), "enclosure_kit": (1, 1)}
    for role, (count, quantity) in expected.items():
        if len(roles[role]) != count or any(row["required_quantity_per_output"] != quantity
                                            for row in roles[role]):
            errors.append(f"{bom_id}: {role} candidates or quantity differ from this pilot")
    if set(roles) != set(expected):
        errors.append(f"{bom_id}: unexpected or missing component roles")
    network = roles["network_power_kit"]
    if len(network) == 2 and (len({row["substitute_group_code"] for row in network}) != 1
                              or network[0]["substitute_group_code"] is None):
        errors.append(f"{bom_id}: network/power candidates must share a substitute group")
    if errors:
        return {"errors": errors, "candidate_results": {}, "synthetic_fit_check_passed": False,
                "ready_for_full_generation": False}

    compute = specs[roles["compute_kit"][0]["component_product_id"]]
    drive = specs[roles["storage_drive"][0]["component_product_id"]]
    enclosure = specs[roles["enclosure_kit"][0]["component_product_id"]]
    if drive["host_interface"] != compute["storage_host_interface"]:
        errors.append("storage drive interface does not match the compute kit")
    if compute["board_form_factor"] not in enclosure["supported_board_form_factors"]:
        errors.append("compute kit board does not fit the enclosure")
    if drive["form_factor"] not in enclosure["supported_drive_form_factors"]:
        errors.append("storage drive does not fit the enclosure")
    if enclosure["drive_slots"] < 2:
        errors.append("enclosure lacks slots for two drives")

    candidates = {}
    for line in network:
        cid = line["component_product_id"]
        kit = specs[cid]
        demand = compute["rated_watts"] + 2 * drive["rated_watts"] + kit["rated_watts"]
        candidate_errors = []
        if kit["network_interface"] != compute["network_slot_interface"]:
            candidate_errors.append("network interface does not match the compute kit")
        if demand > kit["psu_output_watts"]:
            candidate_errors.append("kit power supply is below calculated load")
        if demand > enclosure["power_budget_watts"]:
            candidate_errors.append("enclosure power budget is below calculated load")
        if candidate_errors:
            errors.extend(f"{cid}: {message}" for message in candidate_errors)
        candidates[cid] = {"calculated_load_watts": demand,
                           "psu_output_watts": kit["psu_output_watts"],
                           "checks_passed": not candidate_errors}

    return {"errors": errors, "candidate_results": candidates,
            "synthetic_fit_check_passed": not errors, "ready_for_full_generation": False}


if __name__ == "__main__":
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    pilot = json.loads((HERE / "phase1c_technical_fit_pilot.json").read_text())
    result = validate(portfolio, pilot)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))
