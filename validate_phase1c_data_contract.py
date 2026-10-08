"""Validate controlled vocabularies and structured JSON contracts before generation."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


def _is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _check_zone(zone):
    if not isinstance(zone, str) or not zone:
        return False
    try:
        ZoneInfo(zone)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def _check_percentages(values, label, errors):
    if not isinstance(values, dict) or not values:
        errors.append(f"{label} must be a nonempty mapping")
        return
    if any(not isinstance(value, (int, float)) or value < 0 for value in values.values()):
        errors.append(f"{label} must contain nonnegative numeric percentages")
    if abs(sum(values.values()) - 100) > 1e-9:
        errors.append(f"{label} must sum to 100")


def _valid_weekdays(days):
    return (isinstance(days, list) and bool(days)
            and all(type(day) is int and 1 <= day <= 7 for day in days)
            and len(days) == len(set(days)))


def validate_contract(contract):
    errors = []
    vocab = contract.get("controlled_vocabularies", {})
    calendar = contract.get("calendar", {})

    countries = vocab.get("countries", [])
    regions = vocab.get("destination_regions", {})
    if len(countries) != len(set(countries)) or not countries:
        errors.append("countries must be a nonempty unique list")
    if set(regions) != set(countries):
        errors.append("destination-region country keys must equal countries")
    for country, codes in regions.items():
        if not codes or len(codes) != len(set(codes)):
            errors.append(f"regions for {country} must be nonempty and unique")
        if any(not isinstance(code, str) or not code.startswith(country + "-") for code in codes):
            errors.append(f"regions for {country} must use the {country}- prefix")
    installation_countries = vocab.get("installation_service_countries", [])
    if not set(installation_countries) <= set(countries):
        errors.append("installation countries must be supported countries")
    service_regions = vocab.get("installation_service_regions", {})
    if set(service_regions) != set(installation_countries):
        errors.append("installation service-region keys must equal installation countries")
    for country, codes in service_regions.items():
        if not set(codes) <= set(regions.get(country, [])):
            errors.append(f"installation regions for {country} are not destination regions")
    _check_percentages(vocab.get("customer_industry_target_share_pct"), "industry shares", errors)
    if set(vocab.get("customer_industry_target_share_pct", {})) != set(vocab.get("customer_industry_codes", [])):
        errors.append("industry shares must cover the industry vocabulary")
    _check_percentages(vocab.get("customer_country_target_share_pct"), "customer country shares", errors)
    if set(vocab.get("customer_country_target_share_pct", {})) != set(countries):
        errors.append("customer country shares must cover supported countries")

    weekday_values = set(calendar.get("iso_weekday_numbers", {}).values())
    if weekday_values != set(range(1, 8)):
        errors.append("ISO weekday mapping must contain exactly 1 through 7")
    working = calendar.get("default_working_weekdays", [])
    if not _valid_weekdays(working) or set(working) != {1, 2, 3, 4, 5}:
        errors.append("default working weekdays must be unique ISO weekdays")
    if calendar.get("holidays_mode") == "omitted_from_phase1c" and not calendar.get("holiday_dates_must_be_empty"):
        errors.append("omitted holiday mode must require an empty holiday list")

    locations = vocab.get("location_codes", {})
    if not locations:
        errors.append("at least one location is required")
    for location, row in locations.items():
        if row.get("country_code") not in countries:
            errors.append(f"{location} has unsupported country")
        if row.get("region") not in regions.get(row.get("country_code"), []):
            errors.append(f"{location} has country-incompatible region")
        if not _check_zone(row.get("time_zone")):
            errors.append(f"{location} has invalid IANA time zone")
        days = row.get("working_weekdays", [])
        if not _valid_weekdays(days):
            errors.append(f"{location} has invalid working weekdays")

    pattern = vocab.get("salesperson_code_pattern")
    if not isinstance(pattern, str) or not re.fullmatch(pattern, "SALES-001"):
        errors.append("salesperson code pattern must accept SALES-001")
    if len(vocab.get("payment_terms_days", [])) != len(set(vocab.get("payment_terms_days", []))):
        errors.append("payment terms must be unique")

    supplier_calendar = contract.get("supplier_order_calendar", {})
    if supplier_calendar.get("required_keys") != ["working_weekdays", "holiday_dates", "time_zone"]:
        errors.append("supplier calendar required keys are incomplete or reordered")
    if not _valid_weekdays(supplier_calendar.get("working_weekdays")):
        errors.append("supplier working weekdays must use ISO 1 through 7")
    if supplier_calendar.get("holiday_dates") != []:
        errors.append("Phase 1C supplier holiday list must remain empty")

    component = contract.get("component_stock", {})
    if (component.get("initial_unit") != "component_unit" or component.get("indivisible") is not True or
        component.get("on_hand_and_allocated") != "whole_nonnegative_units" or
        component.get("requirement") != "aggregate_scrap_adjusted_theoretical_demand_across_selected_builds_then_ceil_per_component" or
        not component.get("no_quote_reservation")):
        errors.append("component stock contract must preserve whole units and aggregate rounding")
    configured = contract.get("configured_builds", {})
    roles = configured.get("component_roles_by_family", {})
    if (set(roles) != {"compute", "storage", "network_and_power", "chassis_and_other"}
        or len(set(roles.values())) != 4
        or any(not _is_nonempty_string(value) for value in roles.values())):
        errors.append("configured component roles must cover the four families uniquely")
    for key in ("build_platforms", "offered_option_codes"):
        values = configured.get(key)
        if (not isinstance(values, list) or not values or
            any(not _is_nonempty_string(value) for value in values) or
            len(values) != len(set(values))):
            errors.append(f"configured {key} must be nonempty unique strings")
    horizon = contract.get("production_horizon", {})
    if (horizon.get("boundary") != "latest_capacity_date_represented_at_the_candidate_location" or
        horizon.get("missing_or_stale_capacity_window") != "unknown" or
        horizon.get("confirmed_required_component_supply_after_boundary") != "unknown" or
        horizon.get("missing_window_unknown_reason") != "production_capacity_evidence_missing_or_stale" or
        horizon.get("unknown_reason") != "confirmed_component_supply_after_capacity_horizon" or
        horizon.get("supplier_offer_counts_as_binding_supply") is not False or
        horizon.get("infer_capacity_after_boundary") is not False):
        errors.append("production horizon contract must preserve uncertainty beyond represented capacity")
    if (configured.get("line_bom_match") != "product_catalogue_and_exact_configuration_signature_at_run_as_of" or
        configured.get("same_product_variant_demand") != "group_by_selected_BOM" or
        configured.get("unconfigured_finished_stock_with_multiple_variants") != "visible_but_not_confirming_either_variant" or
        configured.get("shared_component_stock") != "aggregate_and_round_once_per_component_at_site" or
        configured.get("result_attribution") != "per_BOM_and_quoted_line"):
        errors.append("configured build contract must separate BOM variants and unbound finished stock")
    substitution = configured.get("substitution_selection", {})
    if (substitution.get("one_selected_line_per_bom_and_group") is not True or
        substitution.get("preference_order") != "sufficient_selectable_units_then_lowest_priority_then_component_product_id" or
        substitution.get("selectable_units") != "fresh_component_stock_plus_confirmed_unexpired_inbound_at_active_production_locations" or
        substitution.get("shortage_behavior") != "choose_lowest_priority_then_component_product_id_and_expose_group_shortfall" or
        substitution.get("alternatives_not_double_counted") is not True):
        errors.append("configured build contract must define deterministic substitute selection")

    json_contracts = contract.get("json_contracts", {})
    required_contracts = {
        "products_attributes_json", "deal_terms_json", "deal_line_configuration_json",
        "requirements_json", "evidence_refs_json", "configuration_signature_json",
        "compatibility_condition_json", "provider_evidence_record", "agent_output_json",
    }
    if set(json_contracts) != required_contracts:
        errors.append("JSON contract set is incomplete")
    for key in ("products_attributes_json", "deal_terms_json", "deal_line_configuration_json"):
        if not isinstance(json_contracts.get(key), dict):
            errors.append(f"{key} must be an object contract")
    provider = json_contracts.get("provider_evidence_record", {})
    if "provider_id" not in provider.get("required_keys", []):
        errors.append("provider proof must require provider_id")
    if not provider.get("full_term_required_for_binding"):
        errors.append("binding provider proof must cover the full term")
    output = json_contracts.get("agent_output_json", {})
    if not output.get("no_private_chain_of_thought") or not output.get("route_is_not_approval"):
        errors.append("agent output contract must exclude private chain of thought and actual approval")
    return {"errors": errors, "ready_for_generation": not errors}


def validate_payload(kind, payload, contract, *, mode=None, product_attributes=None):
    """Small contract checks used by tests and future row validators."""
    errors = []
    jc = contract["json_contracts"]
    if kind == "supplier_calendar":
        spec = contract["supplier_order_calendar"]
        if not isinstance(payload, dict):
            errors.append("supplier calendar must be an object")
        else:
            if set(payload) != set(spec["required_keys"]):
                errors.append("supplier calendar keys must match contract")
            if not _valid_weekdays(payload.get("working_weekdays")):
                errors.append("supplier working weekdays are invalid")
            if payload.get("holiday_dates") != []:
                errors.append("supplier holidays are omitted in Phase 1C")
            if not _check_zone(payload.get("time_zone")):
                errors.append("supplier time zone is invalid")
    elif kind == "shipping_weekdays":
        if not _valid_weekdays(payload):
            errors.append("shipping weekdays must be a nonempty unique ISO weekday array")
    elif kind == "deal_terms":
        spec = jc["deal_terms_json"]
        if not isinstance(payload, dict):
            errors.append("terms must be an object")
        else:
            if set(spec["forbidden_keys"]) & set(payload):
                errors.append("terms contains forbidden key")
            for key in spec["required_on_submission"]:
                if key not in payload:
                    errors.append(f"terms missing {key}")
            if payload.get("payment_terms_days") not in contract["controlled_vocabularies"]["payment_terms_days"]:
                errors.append("terms payment day is not allowed")
            if not isinstance(payload.get("allow_partial_delivery"), bool):
                errors.append("allow_partial_delivery must be boolean")
            clauses = payload.get("contract_clause_codes")
            if not isinstance(clauses, list) or not clauses or any(
                code not in contract["controlled_vocabularies"]["contract_clause_codes"] for code in clauses
            ):
                errors.append("contract clauses are invalid")
            if "contract_months" in payload and (
                not isinstance(payload["contract_months"], int) or isinstance(payload["contract_months"], bool)
                or payload["contract_months"] <= 0
            ):
                errors.append("contract_months must be positive integer")
    elif kind == "product_attributes":
        spec = jc["products_attributes_json"]
        mode = mode or "physical"
        if not isinstance(payload, dict):
            errors.append("product attributes must be an object")
        else:
            for key in spec["common_required"]:
                if key not in payload:
                    errors.append(f"product attributes missing {key}")
            if not _is_nonempty_string(payload.get("archetype_code")):
                errors.append("archetype_code must be nonempty string")
            if payload.get("demand_class") not in spec["common_required"]["demand_class"]:
                errors.append("demand_class is invalid")
            for key in ("category", "subcategory"):
                if key in payload and not _is_nonempty_string(payload[key]):
                    errors.append(f"{key} must be nonempty string")
            if "build_platform" in payload and payload["build_platform"] not in contract["configured_builds"]["build_platforms"]:
                errors.append("build_platform is invalid")
            if "component_role" in payload and not _is_nonempty_string(payload["component_role"]):
                errors.append("component_role must be nonempty string")
            for key, vocabulary in (("offered_options", "offered_option_codes"),
                                    ("supported_platforms", "build_platforms")):
                if key in payload:
                    values = payload[key]
                    if (not isinstance(values, list) or not values or
                        any(not isinstance(value, str) or value not in contract["configured_builds"][vocabulary]
                            for value in values) or len(values) != len(set(values))):
                        errors.append(f"{key} must be a nonempty unique allowed list")
            mode_spec = spec["mode_rules"].get(mode)
            if mode_spec is None:
                errors.append("product mode is not defined")
            else:
                allowed = set(spec["common_required"]) | set(spec["common_optional"])
                allowed |= set(mode_spec.get("required", [])) | set(mode_spec.get("optional", []))
                unknown = set(payload) - allowed
                if unknown:
                    errors.append(f"product attributes contain unknown keys: {sorted(unknown)}")
                for key in mode_spec.get("required", []):
                    if key not in payload:
                        errors.append(f"product attributes missing mode key {key}")
            if "fulfillment_lead_days" in payload and (
                not isinstance(payload["fulfillment_lead_days"], int)
                or isinstance(payload["fulfillment_lead_days"], bool)
                or payload["fulfillment_lead_days"] < 0
            ):
                errors.append("fulfillment_lead_days must be nonnegative integer")
            if "supported_installation_regions" in payload:
                if not isinstance(payload["supported_installation_regions"], list) or any(
                    region not in sum(contract["controlled_vocabularies"]["destination_regions"].values(), [])
                    for region in payload["supported_installation_regions"]
                ):
                    errors.append("installation regions are invalid")
    elif kind == "line_configuration":
        spec = jc["deal_line_configuration_json"]
        mode = mode or "physical"
        if not isinstance(payload, dict):
            errors.append("line configuration must be an object")
        else:
            if mode == "digital":
                allowed = set(spec["digital_allowed_keys"])
                missing = set(spec["digital_required_keys"]) - set(payload)
                if missing:
                    errors.append(f"digital configuration missing keys: {sorted(missing)}")
                if set(payload) - allowed:
                    errors.append("digital configuration contains unknown keys")
                if not isinstance(payload.get("units_per_period"), int) or (
                    isinstance(payload.get("units_per_period"), bool) or payload.get("units_per_period", 0) <= 0
                ):
                    errors.append("units_per_period must be positive integer")
                if product_attributes and payload.get("edition") != product_attributes.get("edition"):
                    errors.append("digital edition differs from product attributes")
            elif mode == "make_to_order":
                if set(payload) - set(spec["make_to_order_allowed_keys"]):
                    errors.append("make-to-order configuration contains unknown keys")
                options = payload.get("selected_options")
                if (not isinstance(options, list) or len(options) != 1 or
                    not isinstance(options[0], str) or
                    options[0] not in contract["configured_builds"]["offered_option_codes"] or
                    (product_attributes is not None and options[0] not in
                     product_attributes.get("offered_options", product_attributes.get("option_codes", [])))):
                    errors.append("make-to-order selected option must be one offered code")
            elif set(payload) - set(spec["physical_allowed_keys"]):
                errors.append("physical configuration contains unknown keys")
    elif kind == "configuration_signature":
        spec = jc["configuration_signature_json"]
        if not isinstance(payload, dict):
            errors.append("configuration signature must be an object")
        else:
            if set(payload) - set(spec["allowed_top_level_keys"]):
                errors.append("configuration signature contains unknown keys")
            for key in ("selected_options", "option_codes", "feature_codes"):
                if key in payload and (not isinstance(payload[key], list) or
                                       any(not _is_nonempty_string(v) for v in payload[key]) or
                                       len(payload[key]) != len(set(payload[key]))):
                    errors.append(f"configuration signature {key} must be unique nonempty strings")
    elif kind == "requirements":
        spec = jc["requirements_json"]
        if not isinstance(payload, dict):
            errors.append("requirements must be an object")
        else:
            if set(payload) - set(spec["allowed_keys"]):
                errors.append("requirements contain unknown keys")
            if "requested_outcomes" in payload and (
                not isinstance(payload["requested_outcomes"], list)
                or any(not _is_nonempty_string(value) for value in payload["requested_outcomes"])
            ):
                errors.append("requested_outcomes must be nonempty strings")
            if "constraints" in payload:
                constraints = payload["constraints"]
                if not isinstance(constraints, list):
                    errors.append("constraints must be an array")
                else:
                    for item in constraints:
                        if (not isinstance(item, dict) or set(item) != {"code", "value"} or
                            not _is_nonempty_string(item.get("code")) or
                            not (type(item.get("value")) in (str, int, float, bool) or
                                 isinstance(item.get("value"), list) and
                                 all(isinstance(value, str) for value in item["value"]))):
                            errors.append("constraint must contain code and value")
            if "customer_notes" in payload and not isinstance(payload["customer_notes"], str):
                errors.append("customer_notes must be a string")
    elif kind == "compatibility_condition":
        spec = jc["compatibility_condition_json"]
        rule_type = mode
        required = set(spec["required_keys_by_rule_type"].get(rule_type, []))
        if rule_type not in spec["allowed_rule_types"]:
            errors.append("compatibility rule type is invalid")
        elif not isinstance(payload, dict):
            errors.append("compatibility condition must be an object")
        else:
            if required - set(payload):
                errors.append("compatibility condition is missing required keys")
            if set(payload) - required:
                errors.append("compatibility condition contains unknown keys")
            if "operator" in payload:
                allowed_operators = spec.get("allowed_operators_by_rule_type", {}).get(rule_type, [])
                if payload["operator"] not in allowed_operators:
                    errors.append("compatibility condition operator is invalid")
            if rule_type == "installation_eligibility":
                country = payload.get("country_code")
                if (country not in contract["controlled_vocabularies"]["countries"] or
                    payload.get("region") not in contract["controlled_vocabularies"]["destination_regions"].get(country, [])):
                    errors.append("installation condition country/region is invalid")
                if type(payload.get("eligible")) is not bool:
                    errors.append("installation condition eligible must be boolean")
    elif kind == "provider_evidence":
        spec = jc["provider_evidence_record"]
        if not isinstance(payload, dict):
            errors.append("provider evidence must be an object")
        else:
            for key in spec["required_keys"]:
                if key not in payload:
                    errors.append(f"provider evidence missing {key}")
            if payload.get("commitment_status") not in spec["commitment_status"]:
                errors.append("provider commitment status is invalid")
            if payload.get("commitment_status") == "binding" and (
                not payload.get("evidence_ref") or not payload.get("covers_from") or not payload.get("covers_until")
            ):
                errors.append("binding provider evidence needs full-term fields")
            if isinstance(payload.get("quantity_allocated"), (int, float)) and isinstance(payload.get("capacity_total"), (int, float)) and payload["quantity_allocated"] > payload["capacity_total"]:
                errors.append("provider allocated quantity exceeds capacity")
    elif kind == "evidence_refs":
        spec = jc["evidence_refs_json"]
        if not isinstance(payload, list):
            errors.append("evidence_refs must be an array")
        else:
            for item in payload:
                if not isinstance(item, dict):
                    errors.append("evidence reference item must be an object")
                    continue
                if set(item) - set(spec["item_keys"]):
                    errors.append("evidence reference contains unknown keys")
                for key in spec["item_keys"]:
                    if key not in item:
                        errors.append(f"evidence reference missing {key}")
                if not _is_nonempty_string(item.get("evidence_ref")):
                    errors.append("evidence reference ID is invalid")
                if item.get("evidence_type") not in spec["evidence_type"]:
                    errors.append("evidence type is invalid")
                if item.get("source_class") not in spec["source_class"]:
                    errors.append("evidence source class is invalid")
                if isinstance(item.get("issued_at"), str):
                    try:
                        issued = datetime.fromisoformat(item["issued_at"].replace("Z", "+00:00"))
                        if issued.tzinfo is None or issued.utcoffset() is None:
                            errors.append("evidence issued_at needs a time zone")
                    except ValueError:
                        errors.append("evidence issued_at is not ISO datetime")
                else:
                    errors.append("evidence issued_at must be ISO datetime")
    elif kind == "agent_output":
        spec = jc["agent_output_json"]
        if not isinstance(payload, dict):
            errors.append("agent output must be an object")
        else:
            for key in spec["required_keys"]:
                if key not in payload:
                    errors.append(f"agent output missing {key}")
            if payload.get("agent_name") not in contract["controlled_vocabularies"]["agent_names"]:
                errors.append("agent name is invalid")
            if payload.get("status") not in spec["status"]:
                errors.append("agent status is invalid")
            if not isinstance(payload.get("findings"), list):
                errors.append("agent findings must be an array")
            else:
                for finding in payload["findings"]:
                    if not isinstance(finding, dict) or any(key not in finding for key in spec["finding_keys"]):
                        errors.append("agent finding is incomplete")
                    elif finding.get("severity") not in spec["finding_severity"] or not isinstance(finding.get("evidence_refs"), list):
                        errors.append("agent finding severity or evidence_refs is invalid")
    else:
        raise ValueError(f"unknown payload contract: {kind}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--contract", type=Path, default=here / "phase1c_data_contract.yaml")
    args = parser.parse_args()
    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    print(json.dumps(validate_contract(contract), indent=2))
    raise SystemExit(1 if validate_contract(contract)["errors"] else 0)


if __name__ == "__main__":
    main()
