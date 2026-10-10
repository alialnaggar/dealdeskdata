"""Preflight a small connected Phase 1C row slice before full generation.

This validates selected generated-row contracts and relationships. It is not a
24-table generator, a database migration, or an agent decision oracle.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import json
import re

import yaml

from validate_phase1c_column_rules import schema_columns
from validate_phase1c_data_contract import validate_payload


HERE = Path(__file__).resolve().parent
TABLES = ("products", "customers", "suppliers", "inventory", "supplier_items",
          "shipping_lanes", "deals", "deal_lines")
ID_FIELD = {"products": "product_id", "customers": "customer_id", "suppliers": "supplier_id",
            "inventory": "inventory_id", "supplier_items": "supplier_item_id",
            "shipping_lanes": "lane_id", "deals": "deal_id", "deal_lines": "deal_line_id"}


def _day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def _instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include a time-zone offset")
    return result


def _number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a quantity")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("quantity must be finite")
    return result


def add_workdays(start, count, weekdays):
    """Count working days after start; a zero-day lead starts on the next workday."""
    if type(count) is not int or count < 0 or not isinstance(weekdays, list) or not weekdays:
        raise ValueError("invalid workday calculation")
    day = start
    if count == 0:
        while day.isoweekday() not in weekdays:
            day += timedelta(days=1)
        return day
    for _ in range(count):
        day += timedelta(days=1)
        while day.isoweekday() not in weekdays:
            day += timedelta(days=1)
    return day


def lane_arrival(ready_at, lane):
    """Date-level dispatch and transit in the lane's origin time zone."""
    local = ready_at.astimezone(ZoneInfo(lane["origin_time_zone"]))
    weekdays = lane["dispatch_weekdays_json"]
    cutoff = datetime.strptime(lane["cutoff_local_time"], "%H:%M:%S").time()
    dispatch = local.date()
    if local.time() >= cutoff:
        dispatch += timedelta(days=1)
    while dispatch.isoweekday() not in weekdays:
        dispatch += timedelta(days=1)
    return dispatch, add_workdays(dispatch, lane["transit_workdays"], weekdays)


def validate_pilot(pilot, contract, schema_sql, config):
    errors, findings = [], []
    vocab = contract["controlled_vocabularies"]
    try:
        as_of = _instant(pilot["as_of_at"])
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        return {"errors": [f"as_of_at: {exc}"], "findings": [], "ready_for_full_generation": False}
    if set(pilot) != {"as_of_at", "rows"} or not isinstance(pilot["rows"], dict):
        errors.append("pilot must contain only as_of_at and rows mapping")
        return {"errors": errors, "findings": findings, "ready_for_full_generation": False}
    rows = pilot["rows"]
    if set(rows) != set(TABLES):
        errors.append("pilot table set differs from the declared eight-table slice")
    shape = schema_columns(schema_sql)
    indexed = {}
    for table in TABLES:
        collection = rows.get(table)
        if not isinstance(collection, list) or not collection:
            errors.append(f"{table}: expected a nonempty list")
            indexed[table] = {}
            continue
        indexed[table] = {}
        for position, row in enumerate(collection):
            label = f"{table}[{position}]"
            if not isinstance(row, dict):
                errors.append(f"{label}: expected an object")
                continue
            if set(row) != set(shape[table]):
                errors.append(f"{label}: fields differ from schema.sql")
                continue
            if any(row[name] is None for name, rule in shape[table].items() if not rule["nullable"]):
                errors.append(f"{label}: required SQL field is null")
                continue
            key = row[ID_FIELD[table]]
            if key in indexed[table]:
                errors.append(f"{table}: duplicate {ID_FIELD[table]}")
            indexed[table][key] = row
    if errors:
        return {"errors": errors, "findings": findings, "ready_for_full_generation": False}

    products, customers, suppliers = (indexed[name] for name in ("products", "customers", "suppliers"))
    for product in products.values():
        key = product["product_id"]
        mode = product["fulfillment_mode"]
        attribute_mode = "digital_activation" if mode == "digital_activation" else (
            "scheduled_service" if mode == "scheduled_service" else "component" if mode == "component" else "physical")
        errors.extend(f"products.{key}: {e}" for e in validate_payload(
            "product_attributes", product["attributes_json"], contract, mode=attribute_mode))
        if product["catalog_version"] != vocab["catalog_version"]:
            errors.append(f"products.{key}: catalogue version differs")
        if (mode in ("digital_activation", "scheduled_service")) != (product["stock_uom"] == "not_applicable"):
            errors.append(f"products.{key}: stock unit differs from fulfillment mode")
        if mode == "component" and product["is_sellable"]:
            errors.append(f"products.{key}: component cannot be sold")
        if mode != "component" and product["category"] not in config["product_catalogue"]["categories"]:
            errors.append(f"products.{key}: category is not configured")
    for customer in customers.values():
        key = customer["customer_id"]
        country = customer["country_code"]
        if country not in vocab["countries"] or customer["region"] not in vocab["destination_regions"].get(country, []):
            errors.append(f"customers.{key}: country and region differ")
        if customer["industry"] not in vocab["customer_industry_codes"]:
            errors.append(f"customers.{key}: industry is not configured")
        if _day(customer["customer_since"]) > as_of.date():
            errors.append(f"customers.{key}: customer_since is in the future")
    for supplier in suppliers.values():
        key = supplier["supplier_id"]
        if supplier["country_code"] not in vocab["countries"]:
            errors.append(f"suppliers.{key}: country is not configured")
        errors.extend(f"suppliers.{key}: {e}" for e in validate_payload(
            "supplier_calendar", supplier["order_calendar_json"], contract))
    for stock in indexed["inventory"].values():
        key = stock["inventory_id"]
        product = products.get(stock["product_id"])
        if product is None or product["stock_uom"] == "not_applicable":
            errors.append(f"inventory.{key}: product is missing or nonstockable")
        if stock["location_id"] not in vocab["location_codes"]:
            errors.append(f"inventory.{key}: location is not configured")
        try:
            if not 0 <= _number(stock["quantity_allocated"]) <= _number(stock["quantity_on_hand"]):
                errors.append(f"inventory.{key}: allocation exceeds stock")
            if product is not None and product["stock_uom"] == "component_unit" and any(
                _number(stock[field]) != _number(stock[field]).to_integral_value()
                for field in ("quantity_on_hand", "quantity_allocated")
            ):
                errors.append(f"inventory.{key}: component_unit stock and allocation must be whole units")
            snapshot = _instant(stock["snapshot_at"])
            if snapshot > as_of:
                errors.append(f"inventory.{key}: snapshot is after as_of_at")
            elif as_of - snapshot > timedelta(hours=config["fulfillment_production_calibration"]
                                               ["proposed_parameters"]["aggregate_inventory"]
                                               ["confirmed_stock_snapshot_max_age_hours"]):
                findings.append({"code": "stock_snapshot_stale", "source_id": key,
                                 "status": "unknown_pending_refresh"})
        except (InvalidOperation, TypeError, ValueError) as exc:
            errors.append(f"inventory.{key}: {exc}")
    for offer in indexed["supplier_items"].values():
        key = offer["supplier_item_id"]
        supplier = suppliers.get(offer["supplier_id"])
        if supplier is None or supplier["status"] != "active" or offer["product_id"] not in products:
            errors.append(f"supplier_items.{key}: supplier/product is unavailable")
            continue
        if offer["currency_code"] != "EUR" or not (0 <= offer["lead_days_min"] <= offer["lead_days_mode"] <= offer["lead_days_max"]):
            errors.append(f"supplier_items.{key}: currency or lead range is invalid")
            continue
        if _day(offer["valid_from"]) > as_of.date() or (offer["valid_to"] and _day(offer["valid_to"]) < as_of.date()):
            errors.append(f"supplier_items.{key}: offer is outside validity dates")
        calendar = supplier["order_calendar_json"]
        if not validate_payload("supplier_calendar", calendar, contract):
            latest = add_workdays(as_of.astimezone(ZoneInfo(calendar["time_zone"])).date(),
                                   offer["lead_days_max"], calendar["working_weekdays"])
            horizon = as_of.date() + timedelta(days=config["fulfillment_production_calibration"]
                                                      ["proposed_parameters"]["production_capacity"]
                                                      ["horizon_calendar_days"])
            if latest > horizon:
                findings.append({"code": "supplier_lead_out_of_horizon", "source_id": key,
                                 "latest_offer_date": latest.isoformat(), "planning_horizon_end": horizon.isoformat(),
                                 "status": "unknown_or_conditional"})
    lanes = indexed["shipping_lanes"]
    for lane in lanes.values():
        key = lane["lane_id"]
        origin = vocab["location_codes"].get(lane["origin_location_id"])
        if origin is None or lane["origin_time_zone"] != origin["time_zone"]:
            errors.append(f"shipping_lanes.{key}: origin and time zone differ")
        if lane["destination_region"] not in vocab["destination_regions"].get(lane["destination_country_code"], []):
            errors.append(f"shipping_lanes.{key}: destination region is invalid")
        errors.extend(f"shipping_lanes.{key}: {e}" for e in validate_payload(
            "shipping_weekdays", lane["dispatch_weekdays_json"], contract))
        if lane["shipping_service_code"] not in vocab["service_codes"] or type(lane["transit_workdays"]) is not int or lane["transit_workdays"] < 0:
            errors.append(f"shipping_lanes.{key}: service or transit is invalid")
    for deal in indexed["deals"].values():
        key = deal["deal_id"]
        customer = customers.get(deal["customer_id"])
        if customer is None or _day(customer["customer_since"]) > _instant(deal["submitted_at"]).date():
            errors.append(f"deals.{key}: customer is missing or not yet active")
        if _instant(deal["submitted_at"]) > as_of:
            errors.append(f"deals.{key}: submission is after as_of_at")
        if deal["catalog_version"] != vocab["catalog_version"] or deal["currency_code"] != "EUR":
            errors.append(f"deals.{key}: catalogue or currency differs")
        if not re.fullmatch(vocab["salesperson_code_pattern"], deal["salesperson_id"]):
            errors.append(f"deals.{key}: salesperson code is invalid")
        if deal["destination_region"] not in vocab["destination_regions"].get(deal["destination_country_code"], []):
            errors.append(f"deals.{key}: destination is invalid")
        for kind, field in (("deal_terms", "terms_json"), ("requirements", "requirements_json"),
                            ("evidence_refs", "evidence_refs_json")):
            errors.extend(f"deals.{key}: {e}" for e in validate_payload(kind, deal[field], contract))
        if deal["dataset_type"] != "generated_test" or any(deal[field] is not None for field in
                                                      ("historical_decision", "decision_reason", "approved_by_roles_json")):
            errors.append(f"deals.{key}: pilot cannot contain historical outcomes or approval labels")
    for line in indexed["deal_lines"].values():
        key = line["deal_line_id"]
        deal, product = indexed["deals"].get(line["deal_id"]), products.get(line["product_id"])
        if deal is None or product is None or not product["is_active"] or not product["is_sellable"]:
            errors.append(f"deal_lines.{key}: deal/product is missing or not sellable")
            continue
        if product["catalog_version"] != deal["catalog_version"]:
            errors.append(f"deal_lines.{key}: product version differs from deal")
        mode = "digital" if product["fulfillment_mode"] == "digital_activation" else (
            "make_to_order" if product["fulfillment_mode"] == "make_to_order" else "physical")
        errors.extend(f"deal_lines.{key}: {e}" for e in validate_payload(
            "line_configuration", line["configuration_json"], contract, mode=mode,
            product_attributes=product["attributes_json"]))
        if type(line["quantity"]) is not int or line["quantity"] <= 0 or _number(line["quoted_unit_price"]) <= 0:
            errors.append(f"deal_lines.{key}: quoted quantity or price is invalid")
        matching = [lane for lane in lanes.values() if lane["is_active"] and
                    lane["destination_country_code"] == deal["destination_country_code"] and
                    lane["destination_region"] == deal["destination_region"] and
                    lane["shipping_service_code"] == deal["shipping_service_code"]]
        if product["stock_uom"] != "not_applicable" and not matching:
            errors.append(f"deal_lines.{key}: no configured shipping lane")
        for lane in matching:
            if not validate_payload("shipping_weekdays", lane["dispatch_weekdays_json"], contract) and \
                    lane["origin_location_id"] in vocab["location_codes"] and \
                    lane["origin_time_zone"] == vocab["location_codes"][lane["origin_location_id"]]["time_zone"]:
                dispatch, arrival = lane_arrival(as_of, lane)
                findings.append({"code": "lane_date_candidate", "source_id": key,
                                 "lane_id": lane["lane_id"], "dispatch": dispatch.isoformat(),
                                 "arrival": arrival.isoformat(), "status": "candidate_not_stock_commitment"})
    return {"errors": errors, "findings": findings, "ready_for_full_generation": False,
            "row_counts": {table: len(rows.get(table, [])) for table in TABLES}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=HERE / "phase1c_pilot_slice.json")
    args = parser.parse_args()
    pilot = json.loads(args.pilot.read_text(encoding="utf-8"))
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text(encoding="utf-8"))
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text(encoding="utf-8"))
    result = validate_pilot(pilot, contract, (HERE / "schema.sql").read_text(encoding="utf-8"), config)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
