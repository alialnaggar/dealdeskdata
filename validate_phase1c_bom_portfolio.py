"""Check proposed catalogue-to-BOM coverage before full data generation.

The checker validates an explicitly enumerated portfolio snapshot. It does not
invent configuration combinations, freeze calibration, or generate database rows.
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import argparse
import json

import yaml

from validate_phase1c_data_contract import validate_payload


HERE = Path(__file__).resolve().parent
PORTFOLIO_KEYS = {
    "catalog_version", "as_of_at", "products", "offered_configurations",
    "bom_headers", "bom_lines", "production_requirements",
}
PRODUCT_KEYS = {"product_id", "catalog_version", "is_sellable", "product_type",
                "fulfillment_mode", "attributes_json"}
BOM_HEADER_KEYS = {"bom_id", "finished_product_id", "catalog_version",
                   "configuration_signature_json", "output_quantity", "effective_from",
                   "effective_to", "status"}
BOM_LINE_KEYS = {"bom_line_id", "bom_id", "component_product_id",
                 "required_quantity_per_output", "scrap_pct", "substitute_group_code",
                 "priority", "is_mandatory"}
REQUIREMENT_KEYS = {"requirement_id", "bom_id", "operation_seq", "capability_code",
                    "resource_type", "setup_hours", "hours_per_unit", "batch_size", "status"}


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include a time-zone offset")
    return result


def _number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a number")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("number must be finite")
    return result


def _signature(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_portfolio(portfolio, config, contract):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    if not isinstance(portfolio, dict) or set(portfolio) != PORTFOLIO_KEYS:
        return {"errors": ["portfolio fields differ from the required contract"],
                "metrics": {}, "portfolio_coverage_valid": False,
                "ready_for_full_generation": False}

    try:
        as_of = _instant(portfolio["as_of_at"])
    except (TypeError, ValueError):
        return {"errors": ["as_of_at must be an ISO timestamp with timezone"],
                "metrics": {}, "portfolio_coverage_valid": False,
                "ready_for_full_generation": False}

    catalog = portfolio["catalog_version"]
    check(isinstance(catalog, str) and bool(catalog.strip()), "catalog_version must be nonempty")
    check(isinstance(portfolio["products"], list), "products must be a list")
    check(isinstance(portfolio["offered_configurations"], list), "offered_configurations must be a list")
    check(isinstance(portfolio["bom_headers"], list), "bom_headers must be a list")
    check(isinstance(portfolio["bom_lines"], list), "bom_lines must be a list")
    check(isinstance(portfolio["production_requirements"], list), "production_requirements must be a list")
    if errors:
        return {"errors": errors, "metrics": {}, "portfolio_coverage_valid": False,
                "ready_for_full_generation": False}

    proposal = config["fulfillment_production_calibration"]["proposed_parameters"]
    component_proposal = proposal["component_catalogue"]
    bom_proposal = proposal["BOMs"]
    expected_catalog = config["product_catalogue"]["metadata"]["catalogue_version"]
    check(catalog == expected_catalog, "portfolio catalogue version differs from calibration")

    products = {}
    for row in portfolio["products"]:
        if not isinstance(row, dict) or not isinstance(row.get("product_id"), str) or not row["product_id"]:
            errors.append("every product needs a nonempty product_id")
            continue
        product_id = row["product_id"]
        if set(row) != PRODUCT_KEYS:
            errors.append(f"{product_id}: product projection fields differ from the contract")
        if product_id in products:
            errors.append(f"duplicate product_id: {product_id}")
            continue
        products[product_id] = row
        if type(row.get("is_sellable")) is not bool:
            errors.append(f"{product_id}: is_sellable must be boolean")
        if row.get("catalog_version") != catalog:
            errors.append(f"{product_id}: product catalogue version differs")
        if not isinstance(row.get("attributes_json"), dict):
            errors.append(f"{product_id}: attributes_json must be an object")
        else:
            mode = row.get("fulfillment_mode")
            mode = "physical" if mode in {"make_to_order", "stocked_finished", "supplier_finished"} else mode
            for message in validate_payload("product_attributes", row["attributes_json"], contract, mode=mode):
                errors.append(f"{product_id}: {message}")
            if row.get("fulfillment_mode") == "make_to_order":
                attrs = row["attributes_json"]
                if (attrs.get("build_platform") not in contract["configured_builds"]["build_platforms"] or
                    not isinstance(attrs.get("offered_options"), list) or not attrs["offered_options"]):
                    errors.append(f"{product_id}: make-to-order platform and offered options are required")
            if row.get("fulfillment_mode") == "component":
                platforms = row["attributes_json"].get("supported_platforms")
                if not isinstance(platforms, list) or not platforms:
                    errors.append(f"{product_id}: component supported_platforms are required")

    sellable = {pid: row for pid, row in products.items() if row.get("is_sellable") is True}
    components = {pid: row for pid, row in products.items()
                  if row.get("fulfillment_mode") == "component"}
    make_to_order = {pid: row for pid, row in sellable.items()
                     if row.get("fulfillment_mode") == "make_to_order"}
    check(len(sellable) == config["dataset"]["sellable_products"],
          "sellable product count differs from the current catalogue target")
    check(len(components) == component_proposal["non_sellable_component_count"],
          "component count differs from the current proposal")
    check(len(products) == component_proposal["total_product_rows_with_120_sellable"],
          "total product rows differ from the current proposal")
    check(len(make_to_order) == bom_proposal["make_to_order_sellable_count"],
          "make-to-order SKU count differs from the current proposal")

    families = defaultdict(int)
    for pid, row in components.items():
        if row.get("is_sellable") is not False or row.get("product_type") != "component":
            errors.append(f"{pid}: component must be non-sellable and product_type=component")
        attrs = row.get("attributes_json")
        family = attrs.get("component_family") if isinstance(attrs, dict) else None
        if family not in component_proposal["family_counts"]:
            errors.append(f"{pid}: component_family is missing or not in the proposal")
        else:
            families[family] += 1
            expected_role = contract["configured_builds"]["component_roles_by_family"].get(family)
            if attrs.get("component_role") != expected_role:
                errors.append(f"{pid}: component_role does not match its family")
    observed_families = {family: families.get(family, 0) for family in component_proposal["family_counts"]}
    check(observed_families == component_proposal["family_counts"],
          "component family counts differ from the current proposal")

    offered = {}
    for item in portfolio["offered_configurations"]:
        if not isinstance(item, dict) or set(item) != {"product_id", "configuration_signature_json"}:
            errors.append("offered configuration fields differ from the contract")
            continue
        pid, signature = item["product_id"], item["configuration_signature_json"]
        if pid not in make_to_order:
            errors.append(f"{pid}: offered configuration does not belong to a make-to-order SKU")
            continue
        for message in validate_payload("configuration_signature", signature, contract):
            errors.append(f"{pid}: {message}")
        options = signature.get("selected_options") if isinstance(signature, dict) else None
        allowed = make_to_order[pid].get("attributes_json", {}).get("offered_options", [])
        if not isinstance(options, list) or len(options) != 1 or options[0] not in allowed:
            errors.append(f"{pid}: offered configuration must name one declared option")
        key = (pid, _signature(signature))
        if key in offered:
            errors.append(f"{pid}: duplicate offered configuration")
        offered[key] = signature
    for pid in make_to_order:
        if not any(key[0] == pid for key in offered):
            errors.append(f"{pid}: make-to-order SKU has no explicitly offered configuration")

    headers = {}
    active_headers = []
    for row in portfolio["bom_headers"]:
        if not isinstance(row, dict):
            errors.append("BOM header must be an object")
            continue
        if set(row) != BOM_HEADER_KEYS:
            errors.append(f"{row.get('bom_id', '<BOM>')}: header projection fields differ from the contract")
        bom_id = row.get("bom_id")
        if not isinstance(bom_id, str) or not bom_id:
            errors.append("BOM header needs a nonempty bom_id")
            continue
        if bom_id in headers:
            errors.append(f"duplicate bom_id: {bom_id}")
            continue
        headers[bom_id] = row
        pid = row.get("finished_product_id")
        if pid not in make_to_order:
            errors.append(f"{bom_id}: finished product is not a sellable make-to-order SKU")
        if row.get("catalog_version") != catalog:
            errors.append(f"{bom_id}: BOM catalogue version differs")
        for message in validate_payload("configuration_signature", row.get("configuration_signature_json"), contract):
            errors.append(f"{bom_id}: {message}")
        try:
            start = _instant(row["effective_from"])
            end = _instant(row["effective_to"]) if row.get("effective_to") is not None else None
            check(end is None or end > start, f"{bom_id}: effective_to must be later than effective_from")
            output = _number(row["output_quantity"])
            check(output > 0, f"{bom_id}: output_quantity must be positive")
        except (KeyError, TypeError, ValueError, InvalidOperation):
            errors.append(f"{bom_id}: effective interval or output quantity is invalid")
            continue
        key = (pid, _signature(row.get("configuration_signature_json")))
        if row.get("status") == "active":
            if start <= as_of and (end is None or as_of < end):
                active_headers.append(row)

    # Active intervals for one product/configuration must never overlap, even
    # if the current snapshot happens to fall outside the overlap.
    active_all = [row for row in headers.values() if row.get("status") == "active"]
    for index, left in enumerate(active_all):
        try:
            left_start = _instant(left["effective_from"])
            left_end = _instant(left["effective_to"]) if left.get("effective_to") is not None else None
        except (KeyError, TypeError, ValueError):
            continue
        left_key = (left.get("finished_product_id"), _signature(left.get("configuration_signature_json")))
        for right in active_all[index + 1:]:
            right_key = (right.get("finished_product_id"), _signature(right.get("configuration_signature_json")))
            if left_key != right_key:
                continue
            try:
                right_start = _instant(right["effective_from"])
                right_end = _instant(right["effective_to"]) if right.get("effective_to") is not None else None
            except (KeyError, TypeError, ValueError):
                continue
            if (left_end is None or right_start < left_end) and (right_end is None or left_start < right_end):
                errors.append(f"active BOM periods overlap for {left_key[0]} configuration")

    lines_by_bom = defaultdict(list)
    unique_lines = set()
    component_bom_usage = defaultdict(set)
    for line in portfolio["bom_lines"]:
        if not isinstance(line, dict):
            errors.append("BOM line must be an object")
            continue
        if set(line) != BOM_LINE_KEYS:
            errors.append(f"{line.get('bom_line_id', '<line>')}: BOM-line projection fields differ from the contract")
        bom_id = line.get("bom_id")
        component_id = line.get("component_product_id")
        if bom_id not in headers:
            errors.append(f"{line.get('bom_line_id', '<line>')}: BOM reference is missing")
            continue
        if component_id not in components:
            errors.append(f"{line.get('bom_line_id', '<line>')}: component reference is not a component product")
            continue
        key = (bom_id, component_id)
        if key in unique_lines:
            errors.append(f"{bom_id}: duplicate component line {component_id}")
        unique_lines.add(key)
        component = components[component_id]
        if component.get("catalog_version") != headers[bom_id].get("catalog_version"):
            errors.append(f"{bom_id}: component {component_id} is from a different catalogue version")
        product = make_to_order.get(headers[bom_id].get("finished_product_id"))
        if product is not None:
            attrs = product.get("attributes_json")
            component_attrs = component.get("attributes_json")
            platform = attrs.get("build_platform") if isinstance(attrs, dict) else None
            supported = (component_attrs.get("supported_platforms")
                         if isinstance(component_attrs, dict) else None)
            if not isinstance(supported, list) or platform not in supported:
                errors.append(f"{bom_id}: component {component_id} does not support build platform {platform}")
        if headers[bom_id].get("finished_product_id") == component_id:
            errors.append(f"{bom_id}: finished product cannot be its own component")
        try:
            qty = _number(line["required_quantity_per_output"])
            scrap = _number(line["scrap_pct"])
            output = _number(headers[bom_id]["output_quantity"])
            check(qty > 0, f"{bom_id}: component quantity must be positive")
            check(0 <= scrap < 100, f"{bom_id}: scrap percent must be in [0, 100)")
            per_finished_unit = qty / output / (1 - scrap / 100)
            bounds = bom_proposal["required_component_units_per_finished_unit"]
            check(Decimal(str(bounds[0])) <= per_finished_unit <= Decimal(str(bounds[2])),
                  f"{bom_id}: component units per finished product fall outside the proposal range")
        except (KeyError, TypeError, ValueError, InvalidOperation, ZeroDivisionError):
            errors.append(f"{bom_id}: component quantity or BOM output is invalid")
        if type(line.get("priority")) is not int or line["priority"] < 0:
            errors.append(f"{bom_id}: substitute priority must be a nonnegative integer")
        if type(line.get("is_mandatory")) is not bool:
            errors.append(f"{bom_id}: is_mandatory must be boolean")
        group = line.get("substitute_group_code")
        if group is not None and (not isinstance(group, str) or not group.strip()):
            errors.append(f"{bom_id}: substitute group code must be null or nonempty")
        lines_by_bom[bom_id].append(line)
        component_bom_usage[component_id].add(bom_id)

    active_ids = {row["bom_id"] for row in active_headers}
    for row in active_headers:
        bom_id = row["bom_id"]
        lines = lines_by_bom[bom_id]
        groups = defaultdict(list)
        mandatory_count = 0
        for line in lines:
            group = line.get("substitute_group_code")
            if group is None:
                if line.get("is_mandatory") is True:
                    mandatory_count += 1
                elif line.get("is_mandatory") is False:
                    errors.append(f"{bom_id}: optional ungrouped components are not supported by the current reader")
            else:
                groups[group].append(line)
        for group, candidates in groups.items():
            if len(candidates) < 2:
                errors.append(f"{bom_id}: substitute group {group} needs at least two alternatives")
            families = {components[line["component_product_id"]]["attributes_json"].get("component_family")
                        for line in candidates if line["component_product_id"] in components
                        and isinstance(components[line["component_product_id"]].get("attributes_json"), dict)}
            if len(families) > 1:
                errors.append(f"{bom_id}: substitute group {group} mixes component families")
            mandatory_count += 1  # The reader selects exactly one line from every declared group.
        bounds = bom_proposal["mandatory_components_per_BOM"]
        if not bounds[0] <= mandatory_count <= bounds[2]:
            errors.append(f"{bom_id}: required component/group count is outside the proposal range")
        if not lines:
            errors.append(f"{bom_id}: active offered BOM has no component lines")

    effective_by_key = defaultdict(list)
    for row in active_headers:
        effective_by_key[(row["finished_product_id"], _signature(row["configuration_signature_json"]))].append(row)
    for key in offered:
        matches = effective_by_key.get(key, [])
        if len(matches) != 1:
            errors.append(f"{key[0]}: each offered configuration must select exactly one effective active BOM")
    for key in effective_by_key:
        if key not in offered:
            errors.append(f"{key[0]}: active BOM exists for a configuration not listed as offered")

    variant_range = bom_proposal["effective_configured_BOM_variants_range"]
    check(variant_range[0] <= len(active_headers) <= variant_range[1],
          "effective BOM variant count is outside the current proposal range")
    substitute_boms = sum(any(line.get("substitute_group_code") for line in lines_by_bom[bom_id])
                          for bom_id in active_ids)
    substitute_share = substitute_boms / len(active_ids) if active_ids else 0
    check(substitute_share <= bom_proposal["BOMs_with_explicit_substitute_group_max_share"],
          "BOMs with substitute groups exceed the current proposal maximum")
    used_components = {cid for cid, bom_ids in component_bom_usage.items() if bom_ids & active_ids}
    shared_components = {cid for cid, bom_ids in component_bom_usage.items()
                         if len(bom_ids & active_ids) >= 2}
    shared_share = len(shared_components) / len(components) if components else 0
    check(len(used_components) == len(components), "every proposed component must be used by an effective BOM")
    check(shared_share >= component_proposal["shared_across_at_least_two_BOMs_min_share"],
          "component reuse across BOMs is below the current proposal minimum")

    requirements = defaultdict(list)
    for row in portfolio["production_requirements"]:
        if not isinstance(row, dict) or row.get("bom_id") not in headers:
            errors.append("production requirement references a missing BOM")
            continue
        if set(row) != REQUIREMENT_KEYS:
            errors.append(f"{row.get('requirement_id', '<requirement>')}: production projection fields differ from the contract")
        if row.get("status") == "active":
            requirements[row["bom_id"]].append(row)
    for bom_id in active_ids:
        reqs = requirements[bom_id]
        if not reqs:
            errors.append(f"{bom_id}: effective BOM has no active production requirements")
            continue
        sequences = {r.get("operation_seq") for r in reqs}
        if any(type(seq) is not int or seq < 1 for seq in sequences) or sequences != set(range(1, max(sequences) + 1)):
            errors.append(f"{bom_id}: production operation sequence must be contiguous from 1")
        capability_resources = set()
        for req in reqs:
            pair = (req.get("operation_seq"), req.get("capability_code"), req.get("resource_type"))
            if pair in capability_resources:
                errors.append(f"{bom_id}: duplicate operation/capability/resource requirement")
            capability_resources.add(pair)
            if req.get("resource_type") not in {"equipment", "workforce"}:
                errors.append(f"{bom_id}: invalid production resource type")
            try:
                check(_number(req["setup_hours"]) >= 0 and _number(req["hours_per_unit"]) >= 0,
                      f"{bom_id}: production hours cannot be negative")
                check(_number(req["batch_size"]) > 0, f"{bom_id}: production batch size must be positive")
            except (KeyError, TypeError, ValueError, InvalidOperation):
                errors.append(f"{bom_id}: production hours or batch size is invalid")

    return {
        "errors": errors,
        "metrics": {
            "sellable_products": len(sellable),
            "components": len(components),
            "make_to_order_skus": len(make_to_order),
            "offered_configurations": len(offered),
            "effective_bom_variants": len(active_headers),
            "components_shared_across_two_or_more_boms": len(shared_components),
            "shared_component_share": round(shared_share, 4),
            "boms_with_substitute_groups": substitute_boms,
            "substitute_group_bom_share": round(substitute_share, 4),
        },
        "portfolio_coverage_valid": not errors,
        # Other column rules, generated-row distributions and user review remain open.
        "ready_for_full_generation": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio", nargs="?", type=Path,
                        help="explicit portfolio JSON; no production data is generated")
    args = parser.parse_args()
    if args.portfolio is None:
        parser.error("provide an explicitly prepared portfolio JSON; checker will not fabricate one")
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    result = validate_portfolio(json.loads(args.portfolio.read_text()), config, contract)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
