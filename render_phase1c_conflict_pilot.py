"""Render independent source conflicts for the Phase 1C pilot.

Load after the five-mode pilot. The case map remains outside submitted rows.
"""

import argparse
from decimal import Decimal
import json
from pathlib import Path

import yaml

from render_phase1c_sellable_catalogue import product_rows
from render_phase1c_vertical_pilot import insert, CATALOG, POLICY, AS_OF, SNAPSHOT

HERE = Path(__file__).resolve().parent
SQL_PATH = HERE / "phase1c_conflict_pilot.sql"
CASE_MAP = {
    "STOCK-ALLOCATED": 6, "STOCK-STALE": 7,
    "SUPPLY-OFFER-ONLY": 8, "SUPPLY-CANCELLED": 9,
    "DIGITAL-NO-PROOF": 10, "DIGITAL-EXPIRED": 11,
    "SERVICE-OUTSIDE": 12, "CREDIT-LIMIT": 13,
    "PRICE-FLOOR": 14, "POLICY-CLAUSE": 15,
    "BUILD-SUBSTITUTE": 16, "BUILD-CAPACITY-STALE": 17,
    "BUILD-HORIZON": 18,
}
END = "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-"
CLOUD = "SELL-CLOUD_SERVICES_AND_SUBSCRIPTIONS-"
SERVICE = "SELL-PROFESSIONAL_AND_IMPLEMENTATION_SERVICES-"
PRODUCTS = {
    "STOCK-ALLOCATED": END + "002", "STOCK-STALE": END + "003",
    "SUPPLY-OFFER-ONLY": END + "007", "SUPPLY-CANCELLED": END + "008",
    "DIGITAL-NO-PROOF": CLOUD + "002", "DIGITAL-EXPIRED": CLOUD + "003",
    "SERVICE-OUTSIDE": SERVICE + "002", "CREDIT-LIMIT": END + "004",
    "PRICE-FLOOR": END + "005", "POLICY-CLAUSE": END + "011",
    "BUILD-SUBSTITUTE": END + "009",
    "BUILD-CAPACITY-STALE": "SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001",
    "BUILD-HORIZON": "SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001",
}


def build(portfolio, costs, config, contract):
    prices = {row[0]: Decimal(row[7]) for row in product_rows(portfolio, costs, config, contract)}
    prices.update({p["product_id"]: Decimal(str(p["product_list_price_eur"]))
                   for p in costs["products"]})
    rows = ["-- Synthetic conflicts; generated_test only. No oracle labels in deal inputs.\n",
            "SET search_path TO deal_desk, public;\n"]

    def add(table, **values):
        rows.append(insert(table, values))

    def stock(index, product, location, quantity, snapshot, allocated=0):
        add("inventory", inventory_id=f"CONFLICT-STOCK-{index:02d}-{product}",
            product_id=product, location_id=location, quantity_on_hand=quantity,
            quantity_allocated=allocated, snapshot_at=snapshot)

    def capacity(index, location, snapshot):
        days = ("2026-09-04", "2026-09-07") if index == 18 else ("2026-09-02", "2026-09-03")
        for operation, capability, resource, day in ((1, "assembly", "workforce", days[0]),
                                                     (2, "test", "equipment", days[1])):
            add("production_capacity", capacity_id=f"CONFLICT-CAP-{index:02d}-{operation}",
                location_id=location, capability_code=capability, resource_type=resource,
                capacity_date=day, time_zone="Europe/Amsterdam" if location == "WH-EU-WEST" else "Europe/Berlin", available_capacity_hours=8,
                allocated_capacity_hours=2, snapshot_at=snapshot, status="active",
                evidence_ref=f"CONFLICT-CAP-PROOF-{index:02d}-{operation}")

    for case, index in CASE_MAP.items():
        product = PRODUCTS[case]
        customer, deal = f"CONFLICT-CUST-{index:02d}", f"CONFLICT-DEAL-{index:02d}"
        add("customers", customer_id=customer, customer_code=customer,
            customer_name=f"Synthetic buyer {index:02d}", size_segment="SMB",
            industry="manufacturing", country_code="DE", region="DE-NW",
            customer_since="2025-01-01", account_status="Active")
        add("customer_credit_profiles", customer_id=customer,
            credit_limit=Decimal("1000") if case == "CREDIT-LIMIT" else Decimal("1000000"),
            unbilled_committed_amount=Decimal("200") if case == "CREDIT-LIMIT" else 0,
            commitments_as_of_at=SNAPSHOT, commitment_evidence_ref=f"CONFLICT-CREDIT-{index:02d}",
            risk_rating="Low", credit_status="Active", default_payment_terms_days=30,
            last_review_date="2026-08-15")
        if case == "CREDIT-LIMIT":
            add("accounts_receivable", receivable_id="CONFLICT-AR-13", customer_id=customer,
                invoice_number="CONFLICT-INVOICE-13", invoice_date="2026-08-01",
                due_date="2026-09-15", original_amount=800, outstanding_amount=700,
                status="Partially Paid", as_of_date="2026-09-01")
        mode = next(p["fulfillment_mode"] for p in portfolio["products"] if p["product_id"] == product)
        digital = mode == "digital_activation"
        run_as_of = ("2026-09-01T05:00:00Z" if case == "BUILD-CAPACITY-STALE" else
                     "2026-09-01T07:00:00Z" if case in {"BUILD-SUBSTITUTE", "BUILD-HORIZON"} else AS_OF)
        terms = {"payment_terms_days": 30,
                 "contract_clause_codes": ["legal_review"] if case == "POLICY-CLAUSE" else ["standard"],
                 "allow_partial_delivery": False}
        if digital:
            terms["contract_months"] = 12
        add("deals", deal_id=deal, customer_id=customer, salesperson_id="SALES-001",
            deal_name=f"Synthetic quote {index:02d}",
            submitted_at="2026-09-01T03:00:00Z" if mode == "make_to_order" else "2026-09-01T10:00:00Z",
            catalog_version=CATALOG, policy_set_code=POLICY,
            requested_delivery_date=None if digital else "2026-09-10",
            destination_country_code="DE", destination_region="DE-NW",
            shipping_service_code="standard" if mode in {"stocked_finished", "supplier_finished", "make_to_order"} else None,
            terms_json=terms, deal_status="Draft", dataset_type="generated_test")
        quoted = (prices[product] * Decimal("0.5")).quantize(Decimal("0.01")) if case == "PRICE-FLOOR" else prices[product]
        add("deal_lines", deal_line_id=f"CONFLICT-LINE-{index:02d}", deal_id=deal,
            line_number=1, product_id=product, quantity=12 if digital else 1,
            quoted_unit_price=quoted,
            configuration_json={"edition": "business", "units_per_period": 1} if digital else
                {"selected_options": ["alternate" if case == "BUILD-CAPACITY-STALE" else "standard"]}
                if mode == "make_to_order" else {},
            requested_activation_date="2026-09-03" if digital else None)
        rows.append(f"UPDATE deals SET deal_status='Submitted' WHERE deal_id='{deal}';\n")
        add("deal_runs", run_id=f"00000000-0000-4000-8000-{260000 + index:012d}", deal_id=deal,
            original_policy_set_code=POLICY, applied_policy_set_code=POLICY,
            catalog_version_used=CATALOG, as_of_at=run_as_of,
            data_snapshot_ref="CONFLICT-SNAPSHOT", input_snapshot_json={},
            config_hash="provisional-conflict-pilot", run_status="queued", started_at=run_as_of)

        if case.startswith("STOCK-") or case in {"CREDIT-LIMIT", "PRICE-FLOOR", "POLICY-CLAUSE"}:
            allocated = 2 if case == "STOCK-ALLOCATED" else 0
            snapshot = "2026-08-30T09:00:00Z" if case == "STOCK-STALE" else SNAPSHOT
            stock(index, product, "WH-EU-CENTRAL", 2, snapshot, allocated)
        if case.startswith("SUPPLY-"):
            add("supplier_items", supplier_item_id=f"CONFLICT-OFFER-{index:02d}",
                supplier_id="PILOT-SUP-001", product_id=product,
                supplier_sku=f"SYN-OFFER-{index:02d}", minimum_order_qty=1,
                order_multiple=1, lead_days_min=1, lead_days_mode=2, lead_days_max=3,
                unit_cost=(prices[product] * Decimal("0.75")).quantize(Decimal("0.01")),
                currency_code="EUR", valid_from="2026-08-01",
                is_active=case == "SUPPLY-OFFER-ONLY")
        if case == "SUPPLY-CANCELLED":
            add("purchase_orders", purchase_order_id="CONFLICT-PO-09",
                supplier_id="PILOT-SUP-001", reference_number="CONFLICT-PO-09",
                ordered_at="2026-08-30T08:00:00Z", confirmed_at="2026-08-30T09:00:00Z",
                status="Cancelled", destination_location_id="WH-EU-CENTRAL")
            add("inbound_supply", supply_id="CONFLICT-INBOUND-09", purchase_order_id="CONFLICT-PO-09",
                product_id=product, location_id="WH-EU-CENTRAL", quantity=2,
                quantity_allocated=0, expected_date="2026-09-03",
                confirmed_at="2026-08-30T09:00:00Z", status="Cancelled",
                reference_number="CONFLICT-INBOUND-09", evidence_ref="CANCELLED-MANIFEST-09")
        if digital:
            add("digital_capacity", digital_capacity_id=f"CONFLICT-POOL-{index:02d}",
                product_id=product, configuration_signature_json={"edition": "business"},
                provider_id="PILOT-SUP-001", region_code="DE", term_code="12m",
                capacity_unit="instance", capacity_total=10, quantity_allocated=2,
                activation_lead_days=2, commitment_status="binding",
                confirmed_at="2026-08-31T09:00:00Z", valid_until="2027-09-05T00:00:00Z",
                snapshot_at=SNAPSHOT, evidence_ref=f"CONFLICT-PROOF-{index:02d}")
        if case == "SERVICE-OUTSIDE":
            add("compatibility_rules", compatibility_rule_id="CONFLICT-SERVICE-OUTSIDE",
                catalog_version=CATALOG, rule_name="Synthetic outside service coverage",
                rule_type="installation_eligibility", scope_type="line", source_product_id=product,
                condition_json={"country_code": "DE", "region": "DE-NW", "eligible": False},
                severity="blocker", message="Service unavailable in region", priority=1)
        if mode == "make_to_order":
            location = "WH-EU-CENTRAL" if case == "BUILD-CAPACITY-STALE" else "WH-EU-WEST"
            source_at = "2026-09-01T04:00:00Z" if case == "BUILD-CAPACITY-STALE" else "2026-09-01T06:00:00Z"
            bom = {"BUILD-SUBSTITUTE": "BOM-001", "BUILD-CAPACITY-STALE": "BOM-006",
                   "BUILD-HORIZON": "BOM-005"}[case]
            parts = [line for line in portfolio["bom_lines"] if line["bom_id"] == bom]
            for line in parts:
                component = line["component_product_id"]
                if case == "BUILD-HORIZON" and component == "COMP-COMPUTE-004":
                    continue
                if case == "BUILD-SUBSTITUTE" and component == "COMP-NETWORK_AND_POWER-002":
                    continue
                stock(index, component, location, 4,
                      source_at, 4 if case == "BUILD-SUBSTITUTE" and
                      component == "COMP-NETWORK_AND_POWER-001" else 0)
            capacity(index, location, "2026-08-30T04:00:00Z" if case == "BUILD-CAPACITY-STALE" else source_at)
            if case == "BUILD-SUBSTITUTE":
                add("shipping_lanes", lane_id=f"CONFLICT-LANE-{index:02d}",
                    origin_location_id=location, origin_time_zone="Europe/Amsterdam",
                    destination_country_code="DE", destination_region="DE-NW",
                    shipping_service_code="standard", transit_workdays=2,
                    dispatch_weekdays_json=[1, 2, 3, 4, 5], cutoff_local_time="15:00:00")
            if case in {"BUILD-SUBSTITUTE", "BUILD-HORIZON"}:
                component = ("COMP-NETWORK_AND_POWER-002" if case == "BUILD-SUBSTITUTE"
                             else "COMP-COMPUTE-004")
                po = f"CONFLICT-PO-{index:02d}"
                add("purchase_orders", purchase_order_id=po, supplier_id="PILOT-SUP-001",
                    reference_number=po, ordered_at="2026-08-31T08:00:00Z",
                    confirmed_at="2026-08-31T09:00:00Z", status="Confirmed",
                    destination_location_id=location)
                add("inbound_supply", supply_id=f"CONFLICT-INBOUND-{index:02d}",
                    purchase_order_id=po, product_id=component, location_id=location,
                    quantity=2, quantity_allocated=0,
                    expected_date="2026-09-02" if case == "BUILD-SUBSTITUTE" else "2026-09-10",
                    confirmed_at="2026-08-31T09:00:00Z", status="Confirmed",
                    reference_number=f"CONFLICT-INBOUND-{index:02d}",
                    evidence_ref=f"CONFLICT-COMPONENT-PROOF-{index:02d}",
                    valid_until="2026-09-15T00:00:00Z")
    rows.append("DO $pilot$ BEGIN IF (SELECT count(*) FROM deals WHERE deal_id LIKE 'CONFLICT-DEAL-%') <> 13 "
                "THEN RAISE EXCEPTION 'Conflict pilot deals missing'; END IF; END $pilot$;\n")
    return "".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    sql = build(portfolio, costs, config, contract)
    if args.check:
        if SQL_PATH.read_text() != sql:
            raise SystemExit("conflict pilot differs from source generator")
    else:
        SQL_PATH.write_text(sql)
    print(f"{len(CASE_MAP)} provisional conflict deals rendered")


if __name__ == "__main__":
    main()
