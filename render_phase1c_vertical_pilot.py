"""Render five connected, provisional deal paths at the configured as-of date.

This is the first operational generator slice. Source rows are constructed
before submitted deals and contain no expected decisions or answer keys.
"""

import argparse
from decimal import Decimal
import json
from pathlib import Path

import yaml

from phase1c_digital_units import digital_signature
from render_phase1c_sellable_catalogue import product_rows, quote


HERE = Path(__file__).resolve().parent
SQL_PATH = HERE / "phase1c_vertical_pilot.sql"
PROOF_PATH = HERE / "phase1c_vertical_provider_manifest.json"
AS_OF = "2026-09-01T12:00:00Z"
SNAPSHOT = "2026-09-01T09:00:00Z"
CATALOG = "CATALOGUE_2026_V1"
POLICY = "BASELINE_2026"
SELECTED = {
    "stocked_finished": "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-001",
    "supplier_finished": "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-006",
    "make_to_order": "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009",
    "digital_activation": "SELL-CLOUD_SERVICES_AND_SUBSCRIPTIONS-001",
    "scheduled_service": "SELL-PROFESSIONAL_AND_IMPLEMENTATION_SERVICES-001",
}


def insert(table, record):
    return (f"INSERT INTO {table} ({', '.join(record)}) VALUES ("
            + ", ".join(quote(value) for value in record.values()) + ");\n")


def build(portfolio, costs, config, contract):
    if config["dataset"]["time_model"]["evaluation_as_of_date"] != "2026-09-01":
        raise ValueError("pilot dates must follow the configured as-of date")
    rows = product_rows(portfolio, costs, config, contract)
    price = {r[0]: Decimal(r[7]) for r in rows}
    price.update({p["product_id"]: Decimal(str(p["product_list_price_eur"]))
                  for p in costs["products"]})
    product = {p["product_id"]: p for p in portfolio["products"]}
    if {product[key]["fulfillment_mode"] for key in SELECTED.values()} != set(SELECTED):
        raise ValueError("selected products no longer cover exactly five modes")
    out = ["-- Provisional five-mode pilot; load after full 156-product master in a disposable transaction.\n",
           "-- Expected findings are deliberately absent from submitted rows.\n",
           "SET search_path TO deal_desk, public;\n"]
    supplier = "PILOT-SUP-001"
    out.append(insert("suppliers", dict(supplier_id=supplier, supplier_code=supplier,
        supplier_name="Synthetic pilot distributor", country_code="NL", status="active",
        order_calendar_json={"working_weekdays": [1, 2, 3, 4, 5], "holiday_dates": [],
                             "time_zone": "Europe/Amsterdam"})))
    supplied = SELECTED["supplier_finished"]
    out.append(insert("supplier_items", dict(supplier_item_id="PILOT-OFFER-001",
        supplier_id=supplier, product_id=supplied, supplier_sku="SYN-SUP-FINISHED-001",
        minimum_order_qty=1, order_multiple=1, lead_days_min=1, lead_days_mode=2,
        lead_days_max=3, unit_cost=(price[supplied] * Decimal("0.75")).quantize(Decimal("0.01")),
        currency_code="EUR", valid_from="2026-08-01", is_active=True)))
    out.append(insert("purchase_orders", dict(purchase_order_id="PILOT-PO-001",
        supplier_id=supplier, reference_number="PILOT-PO-001",
        ordered_at="2026-08-31T08:00:00Z", confirmed_at="2026-08-31T09:00:00Z",
        status="Confirmed", destination_location_id="WH-EU-CENTRAL")))
    out.append(insert("inbound_supply", dict(supply_id="PILOT-INBOUND-001",
        purchase_order_id="PILOT-PO-001", product_id=supplied, location_id="WH-EU-CENTRAL",
        quantity=2, quantity_allocated=0, expected_date="2026-09-03",
        confirmed_at="2026-08-31T09:00:00Z", status="Confirmed",
        reference_number="PILOT-INBOUND-001", evidence_ref="PILOT-SUPPLIER-MANIFEST-001",
        valid_until="2026-09-10T00:00:00Z")))
    stock = {SELECTED["stocked_finished"]: 3,
             "COMP-COMPUTE-001": 2, "COMP-STORAGE-001": 4,
             "COMP-NETWORK_AND_POWER-001": 2, "COMP-CHASSIS_AND_OTHER-001": 2}
    for i, (product_id, quantity) in enumerate(sorted(stock.items()), 1):
        out.append(insert("inventory", dict(inventory_id=f"PILOT-STOCK-{i:03d}",
            product_id=product_id, location_id="WH-EU-CENTRAL",
            quantity_on_hand=quantity, quantity_allocated=0, snapshot_at=SNAPSHOT)))
    for operation, capability, resource, day in ((1, "assembly", "workforce", "2026-09-02"),
                                                  (2, "test", "equipment", "2026-09-03")):
        out.append(insert("production_capacity", dict(capacity_id=f"PILOT-CAP-{operation}",
            location_id="WH-EU-CENTRAL", capability_code=capability,
            resource_type=resource, capacity_date=day, time_zone="Europe/Berlin",
            available_capacity_hours=8, allocated_capacity_hours=2, snapshot_at=SNAPSHOT,
            status="active", evidence_ref=f"PILOT-CAP-MANIFEST-{operation}")))
    out.append(insert("shipping_lanes", dict(lane_id="PILOT-LANE-DE-NW",
        origin_location_id="WH-EU-CENTRAL", origin_time_zone="Europe/Berlin",
        destination_country_code="DE", destination_region="DE-NW",
        shipping_service_code="standard", transit_workdays=2,
        dispatch_weekdays_json=[1, 2, 3, 4, 5], cutoff_local_time="15:00:00")))
    digital_id = SELECTED["digital_activation"]
    attrs = product[digital_id]["attributes_json"]
    signature = digital_signature(attrs, {"edition": attrs["edition"], "units_per_period": 1})
    if signature != {"edition": "business"}:
        raise ValueError("digital identity changed; source proof must be reviewed")
    out.append(insert("digital_capacity", dict(digital_capacity_id="PILOT-POOL-001",
        product_id=digital_id, configuration_signature_json=signature, provider_id=supplier,
        region_code="DE", term_code="12m", capacity_unit="instance", capacity_total=10,
        quantity_allocated=2, activation_lead_days=2, commitment_status="binding",
        confirmed_at="2026-08-31T09:00:00Z", valid_until="2027-09-05T00:00:00Z",
        snapshot_at=SNAPSHOT, evidence_ref="PILOT-PROVIDER-PROOF-001")))
    service_id = SELECTED["scheduled_service"]
    out.append(insert("compatibility_rules", dict(compatibility_rule_id="PILOT-SERVICE-COVERAGE",
        catalog_version=CATALOG, rule_name="Synthetic coverage for DE-NW",
        rule_type="installation_eligibility", scope_type="line", source_product_id=service_id,
        condition_json={"country_code": "DE", "region": "DE-NW", "eligible": True},
        severity="blocker", message="Service coverage region", priority=1)))
    for index, (mode, product_id) in enumerate(SELECTED.items(), 1):
        customer = f"PILOT-CUST-{index:02d}"
        deal = f"PILOT-DEAL-{index:02d}"
        out.append(insert("customers", dict(customer_id=customer, customer_code=customer,
            customer_name=f"Synthetic pilot buyer {index:02d}", size_segment="SMB",
            industry="manufacturing", country_code="DE", region="DE-NW",
            customer_since="2025-01-01", account_status="Active")))
        out.append(insert("customer_credit_profiles", dict(customer_id=customer,
            credit_limit=1000000, unbilled_committed_amount=0,
            commitments_as_of_at=SNAPSHOT, commitment_evidence_ref=f"PILOT-CREDIT-{index:02d}",
            risk_rating="Low", credit_status="Active", default_payment_terms_days=30,
            last_review_date="2026-08-15")))
        terms = {"payment_terms_days": 30, "contract_clause_codes": ["standard"],
                 "allow_partial_delivery": False}
        if mode == "digital_activation":
            terms["contract_months"] = 12
        out.append(insert("deals", dict(deal_id=deal, customer_id=customer,
            salesperson_id="SALES-001", deal_name=f"Synthetic pilot quote {index:02d}",
            submitted_at="2026-09-01T10:00:00Z", catalog_version=CATALOG,
            policy_set_code=POLICY, requested_delivery_date="2026-09-10" if mode != "digital_activation" else None,
            destination_country_code="DE", destination_region="DE-NW",
            shipping_service_code="standard" if mode in {"stocked_finished", "supplier_finished", "make_to_order"} else None,
            terms_json=terms, deal_status="Draft", dataset_type="generated_test")))
        configuration = ({"selected_options": ["standard"]} if mode == "make_to_order"
                         else {"edition": attrs["edition"], "units_per_period": 1}
                         if mode == "digital_activation" else {})
        out.append(insert("deal_lines", dict(deal_line_id=f"PILOT-LINE-{index:02d}",
            deal_id=deal, line_number=1, product_id=product_id,
            quantity=12 if mode == "digital_activation" else 1,
            quoted_unit_price=price[product_id], configuration_json=configuration,
            requested_activation_date="2026-09-03" if mode == "digital_activation" else None)))
        out.append(f"UPDATE deals SET deal_status='Submitted' WHERE deal_id={quote(deal)};\n")
        out.append(insert("deal_runs", dict(run_id=f"00000000-0000-4000-8000-{260000 + index:012d}",
            deal_id=deal, original_policy_set_code=POLICY, applied_policy_set_code=POLICY,
            catalog_version_used=CATALOG, as_of_at=AS_OF,
            data_snapshot_ref="PILOT-OPERATIONS-SNAPSHOT", input_snapshot_json={},
            config_hash="provisional-pilot", run_status="queued", started_at=AS_OF)))
    out.append("DO $pilot$ BEGIN IF (SELECT count(*) FROM deals WHERE deal_id LIKE 'PILOT-DEAL-%') <> 5 "
               "THEN RAISE EXCEPTION 'Five-mode pilot deals missing'; END IF; END $pilot$;\n")
    proof = {"schema_version": 1, "records": [{
        "evidence_ref": "PILOT-PROVIDER-PROOF-001", "evidence_type": "provider_proof",
        "source_class": "synthetic_provider_manifest", "issued_at": SNAPSHOT,
        "product_id": digital_id,
        "provider_id": supplier, "configuration_signature_json": signature,
        "region_code": "DE", "term_code": "12m", "capacity_unit": "instance",
        "capacity_total": 10, "quantity_allocated": 2, "commitment_status": "binding",
        "verified_at": SNAPSHOT, "confirmed_at": "2026-08-31T09:00:00Z",
        "valid_until": "2027-09-05T00:00:00Z", "covers_from": "2026-09-03",
        "covers_until": "2027-09-04"}]}
    return "".join(out), proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    sql, proof = build(portfolio, costs, config, contract)
    manifest = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    if args.check:
        if SQL_PATH.read_text() != sql or PROOF_PATH.read_text() != manifest:
            raise SystemExit("vertical pilot differs from source generator")
    else:
        SQL_PATH.write_text(sql)
        PROOF_PATH.write_text(manifest)
    print("five connected pilot deal inputs and independent provider proof rendered")


if __name__ == "__main__":
    main()
