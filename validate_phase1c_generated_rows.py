"""Validate typed Phase 1C row contracts on an imported dataset or pilot.

The database owns FKs and arithmetic constraints. This pass checks JSON,
controlled location/zone mappings and submitted-line semantics that SQL does
not enforce. It does not infer source commitments from reference strings.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re

import yaml

from phase1c_digital_units import digital_demand
from validate_phase1c_data_contract import validate_payload

HERE = Path(__file__).resolve().parent
PILOT_SQL = ("phase1c_buildable_master.sql", "phase1c_sellable_catalogue.sql",
             "phase1c_vertical_pilot.sql", "phase1c_conflict_pilot.sql",
             "phase1c_stress_pilot.sql")


def validate_rows(rows, contract, *, trusted_deal_evidence=None):
    errors = []
    locations = contract["controlled_vocabularies"]["location_codes"]
    regions = contract["controlled_vocabularies"]["destination_regions"]
    products = {row["product_id"]: row for row in rows["products"]}
    deals = {row["deal_id"]: row for row in rows["deals"]}
    if len(products) != len(rows["products"]) or len(deals) != len(rows["deals"]):
        errors.append("duplicate product or deal ID in validation input")

    def check_location(table, row, column, zone_column=None):
        location = row[column]
        label = f"{table}.{row[next(iter(row))]}"
        if location not in locations:
            errors.append(f"{label}: unknown location {location}")
        elif zone_column and row[zone_column] != locations[location]["time_zone"]:
            errors.append(f"{label}: {zone_column} differs from configured origin")

    for table, column, zone in (("inventory", "location_id", None),
                                ("purchase_orders", "destination_location_id", None),
                                ("inbound_supply", "location_id", None),
                                ("production_capacity", "location_id", "time_zone"),
                                ("shipping_lanes", "origin_location_id", "origin_time_zone")):
        for row in rows[table]:
            check_location(table, row, column, zone)
    for row in rows["suppliers"]:
        for error in validate_payload("supplier_calendar", row["order_calendar_json"], contract):
            errors.append(f"suppliers.{row['supplier_id']}: {error}")
    for row in rows["shipping_lanes"]:
        for error in validate_payload("shipping_weekdays", row["dispatch_weekdays_json"], contract):
            errors.append(f"shipping_lanes.{row['lane_id']}: {error}")
    for row in rows["products"]:
        mode = row["fulfillment_mode"]
        mode = "physical" if mode in {"stocked_finished", "supplier_finished", "make_to_order"} else mode
        for error in validate_payload("product_attributes", row["attributes_json"], contract, mode=mode):
            errors.append(f"products.{row['product_id']}: {error}")
    for row in rows["compatibility_rules"]:
        for error in validate_payload("compatibility_condition", row["condition_json"], contract,
                                      mode=row["rule_type"]):
            errors.append(f"compatibility_rules.{row['compatibility_rule_id']}: {error}")
    for row in rows["deals"]:
        deal_id = row["deal_id"]
        for kind, column in (("deal_terms", "terms_json"), ("requirements", "requirements_json"),
                             ("evidence_refs", "evidence_refs_json")):
            for error in validate_payload(kind, row[column], contract):
                errors.append(f"deals.{deal_id}.{column}: {error}")
        country = row["destination_country_code"]
        if country not in regions or row["destination_region"] not in regions[country]:
            errors.append(f"deals.{deal_id}: destination country/region mismatch")
        for reference in row["evidence_refs_json"]:
            if not isinstance(reference, dict) or not isinstance(reference.get("issued_at"), str):
                continue
            try:
                issued = datetime.fromisoformat(reference["issued_at"].replace("Z", "+00:00"))
                if issued.tzinfo and issued > row["submitted_at"]:
                    errors.append(f"deals.{deal_id}: evidence issued after submission")
            except ValueError:
                pass  # The payload validator reports the malformed date.
            trusted = (trusted_deal_evidence or {}).get(reference.get("evidence_ref"))
            if not trusted or any(trusted.get(key) != reference.get(key)
                                  for key in ("evidence_ref", "evidence_type", "source_class", "issued_at")):
                errors.append(f"deals.{deal_id}: evidence reference lacks matching independent record")
    for row in rows["deal_lines"]:
        line_id = row["deal_line_id"]
        deal = deals.get(row["deal_id"])
        product = products.get(row["product_id"])
        if not deal or not product:
            errors.append(f"deal_lines.{line_id}: unknown deal or product")
            continue
        if not product["is_sellable"] or not product["is_active"]:
            errors.append(f"deal_lines.{line_id}: product not active sellable")
        mode = product["fulfillment_mode"]
        payload_mode = "digital" if mode == "digital_activation" else mode
        for error in validate_payload("line_configuration", row["configuration_json"], contract,
                                      mode=payload_mode, product_attributes=product["attributes_json"]):
            errors.append(f"deal_lines.{line_id}: {error}")
        if mode == "digital_activation":
            valid, billed, _ = digital_demand(product["unit_of_measure"],
                                              deal["terms_json"].get("contract_months"),
                                              row["configuration_json"].get("units_per_period"))
            if not valid or row["quantity"] != billed or row["requested_activation_date"] is None:
                errors.append(f"deal_lines.{line_id}: digital full-term quantity/date invalid")
        elif row["requested_activation_date"] is not None:
            errors.append(f"deal_lines.{line_id}: physical or service line has activation date")
        if mode == "make_to_order":
            matches = [bom for bom in rows["bom_headers"] if bom["finished_product_id"] == row["product_id"]
                       and bom["configuration_signature_json"] == row["configuration_json"]
                       and bom["status"] == "active"]
            if len(matches) != 1:
                errors.append(f"deal_lines.{line_id}: selected BOM missing or ambiguous")
    return {"errors": errors, "counts": {key: len(value) for key, value in rows.items()},
            "ready_for_row_checks": not errors}


def load_rows(conn):
    from psycopg.rows import dict_row
    tables = ("products", "suppliers", "inventory", "purchase_orders", "inbound_supply",
              "production_capacity", "shipping_lanes", "compatibility_rules", "bom_headers",
              "deals", "deal_lines")
    with conn.cursor(row_factory=dict_row) as cur:
        return {table: cur.execute(f"SELECT * FROM deal_desk.{table}").fetchall() for table in tables}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load-pilot", action="store_true", help="load five provisional SQL files in a rollback-only transaction")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL required")
    import psycopg
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("SET search_path TO deal_desk, public")
        try:
            if args.load_pilot:
                for name in PILOT_SQL:
                    for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                                (HERE / name).read_text(), re.M | re.S):
                        conn.execute(statement)
            result = validate_rows(load_rows(conn), contract)
        finally:
            conn.rollback()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
