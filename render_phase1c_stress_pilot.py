"""Render a seeded mixed-deal stress extension after the 18 scenario cases.

These 18 deals make 36 pilot deals in total. They reuse source pools on purpose;
only contention inside a run can be scheduled by the current read-only reader.
"""

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random

import yaml

from render_phase1c_sellable_catalogue import product_rows
from render_phase1c_vertical_pilot import insert, CATALOG, POLICY

HERE = Path(__file__).resolve().parent
SQL_PATH = HERE / "phase1c_stress_pilot.sql"
REPORT_PATH = HERE / "phase1c_stress_pilot_report.json"
AS_OF = "2026-09-01T14:00:00Z"
SNAPSHOT = "2026-09-01T13:00:00Z"
STOCK = "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-001"
SUPPLY = "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-006"
BUILD = "SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009"
DIGITAL = "SELL-CLOUD_SERVICES_AND_SUBSCRIPTIONS-001"
SERVICE = "SELL-PROFESSIONAL_AND_IMPLEMENTATION_SERVICES-001"
CASES = (["stock"] * 4 + ["supply"] * 3 + ["build"] * 4 +
         ["digital"] * 3 + ["service"] * 2 + ["mixed"] * 2)


def build(portfolio, costs, config, contract):
    if config["random_seed"] != 22495 or config["dataset"]["time_model"]["evaluation_as_of_date"] != "2026-09-01":
        raise ValueError("stress seed or as-of date changed; review pilot assumptions")
    rng = random.Random(config["random_seed"] + 36)
    prices = {r[0]: Decimal(r[7]) for r in product_rows(portfolio, costs, config, contract)}
    prices.update({p["product_id"]: Decimal(str(p["product_list_price_eur"]))
                   for p in costs["products"]})
    out = ["-- Seeded provisional stress inputs; load after vertical and conflict pilots.\n",
           "-- Submitted rows contain no decision or oracle fields.\n",
           "SET search_path TO deal_desk, public;\n"]

    def add(table, **values):
        out.append(insert(table, values))

    # Later snapshots do not change the five baseline or thirteen conflict runs.
    for n, (product, quantity) in enumerate(((STOCK, 3),
        ("COMP-COMPUTE-001", 20), ("COMP-STORAGE-001", 30),
        ("COMP-NETWORK_AND_POWER-001", 20), ("COMP-CHASSIS_AND_OTHER-001", 20)), 1):
        add("inventory", inventory_id=f"STRESS-STOCK-{n:02d}", product_id=product,
            location_id="WH-EU-CENTRAL", quantity_on_hand=quantity,
            quantity_allocated=0, snapshot_at=SNAPSHOT)
    for n, (capability, resource, day) in enumerate((("assembly", "workforce", "2026-09-02"),
                                                     ("test", "equipment", "2026-09-03")), 1):
        add("production_capacity", capacity_id=f"STRESS-CAP-{n:02d}",
            location_id="WH-EU-CENTRAL", capability_code=capability,
            resource_type=resource, capacity_date=day, time_zone="Europe/Berlin",
            available_capacity_hours=8, allocated_capacity_hours=2,
            snapshot_at=SNAPSHOT, status="active", evidence_ref=f"STRESS-CAP-PROOF-{n:02d}")

    ordered = list(CASES)
    rng.shuffle(ordered)
    lines_per_deal = []
    mode_counts = Counter()
    for index, kind in enumerate(ordered, 1):
        customer, deal = f"STRESS-CUST-{index:02d}", f"STRESS-DEAL-{index:02d}"
        add("customers", customer_id=customer, customer_code=customer,
            customer_name=f"Synthetic stress buyer {index:02d}", size_segment="SMB",
            industry="manufacturing", country_code="DE", region="DE-NW",
            customer_since="2025-01-01", account_status="Active")
        add("customer_credit_profiles", customer_id=customer, credit_limit=1000000,
            unbilled_committed_amount=0, commitments_as_of_at=SNAPSHOT,
            commitment_evidence_ref=f"STRESS-CREDIT-{index:02d}",
            risk_rating="Low", credit_status="Active", default_payment_terms_days=30,
            last_review_date="2026-08-15")
        if kind == "stock":
            specs = [(STOCK, (1, 2, 4, 1)[index % 4])]
        elif kind == "supply":
            specs = [(SUPPLY, rng.choice([1, 2, 3]))]
        elif kind == "build":
            specs = [(BUILD, rng.choice([1, 2, 7]))]
        elif kind == "digital":
            specs = [(DIGITAL, rng.choice([1, 2]))]
        elif kind == "service":
            specs = [(SERVICE, 1)]
        else:
            specs = [(STOCK, 1), (DIGITAL, 1)] if index % 2 else [(SUPPLY, 1), (SERVICE, 1)]
        extras = (STOCK, SUPPLY, DIGITAL, SERVICE, BUILD)
        specs.append((extras[(index - 1) % len(extras)], 1))
        if index % 2 == 0:
            specs.append((extras[(index + 1) % len(extras)], 1))
        modes = set()
        for product, _ in specs:
            mode = next(p["fulfillment_mode"] for p in portfolio["products"] if p["product_id"] == product)
            modes.add(mode)
            mode_counts[mode] += 1
        physical = bool(modes & {"stocked_finished", "supplier_finished", "make_to_order"})
        terms = {"payment_terms_days": 30, "contract_clause_codes": ["standard"],
                 "allow_partial_delivery": False}
        if "digital_activation" in modes:
            terms["contract_months"] = 12
        add("deals", deal_id=deal, customer_id=customer, salesperson_id="SALES-001",
            deal_name=f"Synthetic stress quote {index:02d}",
            submitted_at="2026-09-01T12:15:00Z", catalog_version=CATALOG,
            policy_set_code=POLICY, requested_delivery_date="2026-09-10" if not
            (modes == {"digital_activation"}) else None,
            destination_country_code="DE", destination_region="DE-NW",
            shipping_service_code="standard" if physical else None,
            terms_json=terms, deal_status="Draft", dataset_type="generated_test")
        for line_no, (product, units) in enumerate(specs, 1):
            mode = next(p["fulfillment_mode"] for p in portfolio["products"] if p["product_id"] == product)
            digital = mode == "digital_activation"
            discount = Decimal(rng.choice(["0", "0.02", "0.04"]))
            add("deal_lines", deal_line_id=f"STRESS-LINE-{index:02d}-{line_no}",
                deal_id=deal, line_number=line_no, product_id=product,
                quantity=units * 12 if digital else units,
                quoted_unit_price=(prices[product] * (1 - discount)).quantize(Decimal("0.01")),
                configuration_json=({"edition": "business", "units_per_period": units} if digital else
                                    {"selected_options": ["standard"]} if mode == "make_to_order" else {}),
                requested_activation_date="2026-09-03" if digital else None)
        out.append(f"UPDATE deals SET deal_status='Submitted' WHERE deal_id='{deal}';\n")
        add("deal_runs", run_id=f"00000000-0000-4000-8000-{270000 + index:012d}",
            deal_id=deal, original_policy_set_code=POLICY, applied_policy_set_code=POLICY,
            catalog_version_used=CATALOG, as_of_at=AS_OF, data_snapshot_ref="STRESS-SNAPSHOT",
            input_snapshot_json={}, config_hash="provisional-stress-pilot",
            run_status="queued", started_at=AS_OF)
        lines_per_deal.append(len(specs))
    out.append("DO $pilot$ BEGIN IF (SELECT count(*) FROM deals WHERE deal_id LIKE 'STRESS-DEAL-%') <> 18 "
               "THEN RAISE EXCEPTION 'Stress pilot deals missing'; END IF; END $pilot$;\n")
    sql = "".join(out)
    report = {"schema_version": 1, "seed": config["random_seed"] + 36,
              "as_of_at": AS_OF, "stress_deals": len(ordered),
              "pilot_deals_total": 18 + len(ordered), "stress_lines": sum(lines_per_deal),
              "lines_per_deal": {str(k): v for k, v in sorted(Counter(lines_per_deal).items())},
              "line_mode_counts": dict(sorted(mode_counts.items())),
              "sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
              "limitations": ["development_pilot_not_distribution_calibration",
                              "read_only_runs_do_not_reserve_supply_across_deals"]}
    return sql, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    sql, report = build(portfolio, costs, config, contract)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        if SQL_PATH.read_text() != sql or REPORT_PATH.read_text() != rendered:
            raise SystemExit("stress pilot differs from source generator")
    else:
        SQL_PATH.write_text(sql)
        REPORT_PATH.write_text(rendered)
    print(f"{report['stress_deals']} stress deals, {report['stress_lines']} lines, hash {report['sql_sha256']}")


if __name__ == "__main__":
    main()
