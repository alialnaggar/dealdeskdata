"""Read a real draft BOM through the deal reader using disposable SQL rows."""

import os
import re
import json
import unittest
from datetime import date
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None

if psycopg is not None:
    from phase1c_reader import read_run
    from phase1c_deal_decision import assemble_deal_decision
    from psycopg.types.json import Jsonb


HERE = Path(__file__).resolve().parent
RUN_ID = "00000000-0000-4000-8000-000000240001"


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class PortfolioDealReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        try:
            cls.conn.execute("SET search_path TO deal_desk, public")
            for name in ("phase1c_buildable_master.sql", "phase1c_supply_rows.sql",
                         "phase1c_portfolio_deal_rows.sql"):
                content = (HERE / name).read_text()
                # Use the exact fixture inserts in the test's uncommitted transaction.
                for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                            content, re.M | re.S):
                    cls.conn.execute(statement)
        except Exception:
            cls.conn.rollback()
            cls.conn.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def setUp(self):
        self.conn.execute("SAVEPOINT portfolio_case")

    def tearDown(self):
        self.conn.execute("ROLLBACK TO SAVEPOINT portfolio_case")
        self.conn.execute("RELEASE SAVEPOINT portfolio_case")

    def read(self):
        return read_run(self.conn, RUN_ID,
                        cost_parameters={"workforce_cost_eur_per_hour": 30,
                                         "overhead_fraction": "0.1"},
                        commercial_rule_mode="compiled")

    def test_selected_kit_stock_and_ordered_capacity(self):
        bundle = self.read()
        plan = bundle["facts"]["supply"]["assembly_by_bom"]["BOM-001"]
        line = bundle["facts"]["lines"][0]
        self.assertEqual(plan["component_stock_required"]["COMP-STORAGE-001"], 3)
        self.assertEqual(plan["substitution_groups"][0]["selected_component_product_id"],
                         "COMP-NETWORK_AND_POWER-001")
        self.assertEqual(plan["operation_days"], [date(2026, 10, 8), date(2026, 10, 9)])
        self.assertEqual(line["selected_bom_id"], "BOM-001")
        self.assertEqual(line["fulfillment_status"], "feasible_uncommitted")
        self.assertTrue(line["shipping_by_request"])
        self.assertTrue(plan["cost_rollup"]["within_5_pct"])
        decision = assemble_deal_decision(bundle)
        self.assertEqual(decision["status"], "needs_commitment")
        self.assertEqual(decision["required_approvals"], [])
        self.assertEqual(decision["uncommitted_paths"],
                         [{"line_id": "SYN-DL-WORKSTATION",
                           "code": "supply_or_production_not_committed"}])
        self.assertEqual(decision["specialists"]["configuration"][0]["bom_ids"], ["BOM-001"])
        self.assertTrue(decision["specialists"]["approval_routing"]["route_withheld"])
        self.assertEqual(set(decision["specialists"]["availability"][0]["source_ids"]), {
            "BOM-001", "SYN-STOCK-COMPUTE", "SYN-STOCK-STORAGE", "SYN-STOCK-NET",
            "SYN-STOCK-ENCLOSURE", "SYN-CAP-ASM", "SYN-CAP-TEST"})

    def test_confirmed_inbound_alternate_when_selected_kit_is_unavailable(self):
        self.conn.execute("UPDATE inventory SET quantity_allocated = 1 "
                          "WHERE inventory_id = 'SYN-STOCK-NET'")
        bundle = self.read()
        plan = bundle["facts"]["supply"]["assembly_by_bom"]["BOM-001"]
        self.assertEqual(plan["substitution_groups"][0]["selected_component_product_id"],
                         "COMP-NETWORK_AND_POWER-002")
        self.assertEqual(plan["component_stock_required"]["COMP-NETWORK_AND_POWER-002"], 1)
        self.assertEqual(bundle["facts"]["lines"][0]["fulfillment_status"],
                         "feasible_uncommitted")
        decision = assemble_deal_decision(bundle)
        self.assertEqual(decision["status"], "needs_commitment")
        self.assertEqual(decision["required_approvals"], [])
        sources = set(decision["specialists"]["availability"][0]["source_ids"])
        self.assertIn("SYN-INBOUND-NET-ALT", sources)
        self.assertIn("SYN-PO-NET-ALT", sources)
        self.assertNotIn("SYN-STOCK-NET", sources)

    def test_cancelled_po_cannot_rescue_a_component_shortage(self):
        self.conn.execute("UPDATE inventory SET quantity_allocated = 1 "
                          "WHERE inventory_id = 'SYN-STOCK-NET'")
        self.conn.execute("UPDATE inbound_supply SET status = 'Cancelled' "
                          "WHERE supply_id = 'SYN-INBOUND-NET-ALT'")
        self.conn.execute("UPDATE purchase_orders SET status = 'Cancelled' "
                          "WHERE purchase_order_id = 'SYN-PO-NET-ALT'")
        bundle = self.read()
        group = bundle["facts"]["supply"]["assembly_by_bom"]["BOM-001"]["substitution_groups"][0]
        self.assertEqual(group["selection_reason"],
                         "lowest_priority_candidate; no_candidate_has_sufficient_selectable_units")
        self.assertEqual(bundle["facts"]["lines"][0]["production_status"],
                         "infeasible_without_replenishment")
        decision = assemble_deal_decision(bundle)
        self.assertEqual(decision["status"], "needs_revision")
        self.assertEqual(decision["required_approvals"], [])
        self.assertNotIn("SYN-INBOUND-NET-ALT",
                         decision["specialists"]["availability"][0]["source_ids"])

    def test_stale_capacity_is_unknown_instead_of_a_promise(self):
        self.conn.execute("UPDATE production_capacity "
                          "SET snapshot_at = '2026-10-05T09:00:00Z' "
                          "WHERE capacity_id IN ('SYN-CAP-ASM', 'SYN-CAP-TEST')")
        bundle = self.read()
        line = bundle["facts"]["lines"][0]
        self.assertEqual(line["production_status"], "unknown")
        self.assertEqual(line["production_unknown_reason"],
                         "production_capacity_evidence_missing_or_stale")
        decision = assemble_deal_decision(bundle)
        self.assertEqual(decision["status"], "needs_evidence")
        self.assertEqual(decision["required_approvals"], [])

    def test_every_offered_buildable_configuration_reaches_an_uncommitted_gate(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        prices = {p["product_id"]: p["product_list_price_eur"] for p in costs["products"]}
        boms = portfolio["bom_headers"]
        self.assertEqual(len(boms), 24)
        self.assertEqual(len({b["finished_product_id"] for b in boms}), 18)

        self.conn.execute("""INSERT INTO customers (customer_id, customer_code, customer_name,
            size_segment, strategic_account, industry, country_code, region, customer_since,
            account_status) VALUES ('SYN-CUST-PORTFOLIO', 'SYN-CUST-PORTFOLIO',
            'Fictional Portfolio Buyer', 'Enterprise', FALSE, 'manufacturing', 'DE', 'DE-NW',
            '2025-01-01', 'Active')""")
        self.conn.execute("""INSERT INTO customer_credit_profiles (customer_id, credit_limit,
            unbilled_committed_amount, commitments_as_of_at, commitment_evidence_ref,
            risk_rating, credit_status, default_payment_terms_days, last_review_date,
            next_review_date) VALUES ('SYN-CUST-PORTFOLIO', 1000000, 0,
            '2026-10-07T09:00:00Z', 'SYN-PORTFOLIO-CREDIT', 'Low', 'Active', 30,
            '2026-10-01', '2027-01-01')""")
        existing = {'COMP-COMPUTE-001', 'COMP-STORAGE-001',
                    'COMP-NETWORK_AND_POWER-001', 'COMP-CHASSIS_AND_OTHER-001'}
        component_ids = {line["component_product_id"] for line in portfolio["bom_lines"]}
        self.assertEqual(len(component_ids), 36)
        for component_id in sorted(component_ids - existing):
            self.conn.execute("""INSERT INTO inventory (inventory_id, product_id, location_id,
                quantity_on_hand, quantity_allocated, snapshot_at)
                VALUES (%s, %s, 'WH-EU-CENTRAL', 10, 0, '2026-10-07T09:00:00Z')""",
                (f"SYN-PORTFOLIO-STOCK-{component_id}", component_id))

        for index, bom in enumerate(boms, 1):
            deal_id = f"SYN-PORTFOLIO-{bom['bom_id']}"
            run_id = f"00000000-0000-4000-8000-{250000 + index:012d}"
            product_id = bom["finished_product_id"]
            self.conn.execute("""INSERT INTO deals (deal_id, customer_id, salesperson_id,
                deal_name, submitted_at, currency_code, catalog_version, policy_set_code,
                requested_delivery_date, destination_country_code, destination_region,
                shipping_service_code, terms_json, requirements_json, evidence_refs_json,
                deal_status, dataset_type) VALUES (%s, 'SYN-CUST-PORTFOLIO', 'SYN-SALES-001',
                %s, '2026-10-07T10:00:00Z', 'EUR', 'CATALOGUE_2026_V1', 'BASELINE_2026',
                '2026-10-15', 'DE', 'DE-NW', 'standard', %s, '{}', '[]', 'Draft',
                'generated_test')""", (deal_id, f"Synthetic {bom['bom_id']} quote",
                                     Jsonb({"payment_terms_days": 30,
                                            "contract_clause_codes": ["standard"],
                                            "allow_partial_delivery": False})))
            self.conn.execute("""INSERT INTO deal_lines (deal_line_id, deal_id, line_number,
                product_id, quantity, quoted_unit_price, configuration_json)
                VALUES (%s, %s, 1, %s, 1, %s, %s)""",
                (f"SYN-DL-{bom['bom_id']}", deal_id, product_id, prices[product_id],
                 Jsonb(bom["configuration_signature_json"])))
            self.conn.execute("UPDATE deals SET deal_status = 'Submitted' WHERE deal_id = %s",
                              (deal_id,))
            self.conn.execute("""INSERT INTO deal_runs (run_id, deal_id,
                original_policy_set_code, applied_policy_set_code, catalog_version_used,
                as_of_at, data_snapshot_ref, input_snapshot_json, config_hash,
                run_status, started_at, completed_at)
                VALUES (%s, %s, 'BASELINE_2026', 'BASELINE_2026', 'CATALOGUE_2026_V1',
                '2026-10-07T12:00:00Z', 'SYN-PORTFOLIO-SNAPSHOT', %s,
                'synthetic-fixture', 'completed', '2026-10-07T12:00:00Z',
                '2026-10-07T12:01:00Z')""",
                (run_id, deal_id, Jsonb({"fixture": "portfolio_coverage", "bom_id": bom["bom_id"]})))

            bundle = read_run(self.conn, run_id,
                              cost_parameters={"workforce_cost_eur_per_hour": 30,
                                               "overhead_fraction": "0.1"},
                              commercial_rule_mode="compiled")
            line = bundle["facts"]["lines"][0]
            plan = bundle["facts"]["supply"]["assembly_by_bom"][bom["bom_id"]]
            decision = assemble_deal_decision(bundle)
            with self.subTest(bom_id=bom["bom_id"]):
                self.assertEqual(line["selected_bom_id"], bom["bom_id"])
                self.assertEqual(line["fulfillment_status"], "feasible_uncommitted")
                self.assertTrue(line["shipping_by_request"])
                self.assertEqual(len(plan["component_stock_required"]), 4)
                self.assertEqual(sum(plan["component_stock_required"].values()), 6)
                self.assertTrue(plan["cost_rollup"]["within_5_pct"])
                self.assertEqual(decision["status"], "needs_commitment")
                self.assertEqual(decision["required_approvals"], [])

    def test_combined_portfolio_deal_competes_for_shared_capacity(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        prices = {p["product_id"]: p["product_list_price_eur"] for p in costs["products"]}
        boms = portfolio["bom_headers"]
        self.assertEqual(len(boms), 24)

        # Remove material scarcity to isolate the six free hours in each of
        # the two workshop operation rows. No stock or capacity is committed.
        self.conn.execute("UPDATE inventory SET quantity_on_hand = 100, quantity_allocated = 0 "
                          "WHERE inventory_id LIKE 'SYN-STOCK-%'")
        existing = {'COMP-COMPUTE-001', 'COMP-STORAGE-001',
                    'COMP-NETWORK_AND_POWER-001', 'COMP-CHASSIS_AND_OTHER-001'}
        for component_id in sorted({line["component_product_id"]
                                    for line in portfolio["bom_lines"]} - existing):
            self.conn.execute("""INSERT INTO inventory (inventory_id, product_id, location_id,
                quantity_on_hand, quantity_allocated, snapshot_at)
                VALUES (%s, %s, 'WH-EU-CENTRAL', 100, 0, '2026-10-07T09:00:00Z')""",
                (f"SYN-BATCH-STOCK-{component_id}", component_id))
        self.conn.execute("""INSERT INTO customers (customer_id, customer_code, customer_name,
            size_segment, strategic_account, industry, country_code, region, customer_since,
            account_status) VALUES ('SYN-CUST-BATCH', 'SYN-CUST-BATCH',
            'Fictional Batch Buyer', 'Enterprise', FALSE, 'manufacturing', 'DE', 'DE-NW',
            '2025-01-01', 'Active')""")
        self.conn.execute("""INSERT INTO customer_credit_profiles (customer_id, credit_limit,
            unbilled_committed_amount, commitments_as_of_at, commitment_evidence_ref,
            risk_rating, credit_status, default_payment_terms_days, last_review_date)
            VALUES ('SYN-CUST-BATCH', 1000000, 0, '2026-10-07T09:00:00Z',
            'SYN-BATCH-CREDIT', 'Low', 'Active', 30, '2026-10-01')""")
        self.conn.execute("""INSERT INTO deals (deal_id, customer_id, salesperson_id,
            deal_name, submitted_at, currency_code, catalog_version, policy_set_code,
            requested_delivery_date, destination_country_code, destination_region,
            shipping_service_code, terms_json, requirements_json, evidence_refs_json,
            deal_status, dataset_type) VALUES ('SYN-DEAL-BATCH', 'SYN-CUST-BATCH',
            'SYN-SALES-001', 'Synthetic portfolio capacity contention',
            '2026-10-07T10:00:00Z', 'EUR', 'CATALOGUE_2026_V1', 'BASELINE_2026',
            '2026-10-15', 'DE', 'DE-NW', 'standard', %s, '{}', '[]', 'Draft',
            'generated_test')""", (Jsonb({"payment_terms_days": 30,
                                            "contract_clause_codes": ["standard"],
                                            "allow_partial_delivery": False}),))
        for number, bom in enumerate(boms, 1):
            product_id = bom["finished_product_id"]
            self.conn.execute("""INSERT INTO deal_lines (deal_line_id, deal_id, line_number,
                product_id, quantity, quoted_unit_price, configuration_json)
                VALUES (%s, 'SYN-DEAL-BATCH', %s, %s, 1, %s, %s)""",
                (f"SYN-BATCH-LINE-{number:02d}", number, product_id, prices[product_id],
                 Jsonb(bom["configuration_signature_json"])))
        self.conn.execute("UPDATE deals SET deal_status = 'Submitted' "
                          "WHERE deal_id = 'SYN-DEAL-BATCH'")
        run_id = "00000000-0000-4000-8000-000000260001"
        self.conn.execute("""INSERT INTO deal_runs (run_id, deal_id,
            original_policy_set_code, applied_policy_set_code, catalog_version_used,
            as_of_at, data_snapshot_ref, input_snapshot_json, config_hash,
            run_status, started_at, completed_at)
            VALUES (%s, 'SYN-DEAL-BATCH', 'BASELINE_2026', 'BASELINE_2026',
            'CATALOGUE_2026_V1', '2026-10-07T12:00:00Z', 'SYN-BATCH-SNAPSHOT', %s,
            'synthetic-fixture', 'completed', '2026-10-07T12:00:00Z',
            '2026-10-07T12:01:00Z')""",
            (run_id, Jsonb({"fixture": "portfolio_capacity_contention"})))

        bundle = read_run(self.conn, run_id,
                          cost_parameters={"workforce_cost_eur_per_hour": 30,
                                           "overhead_fraction": "0.1"},
                          commercial_rule_mode="compiled")
        plans = bundle["facts"]["supply"]["assembly_by_bom"]
        statuses = [fact.get("production_status") for fact in bundle["facts"]["lines"]]
        decision = assemble_deal_decision(bundle)
        self.assertEqual(len(plans), 24)
        self.assertEqual(statuses.count("feasible_uncommitted"), 6)
        self.assertEqual(statuses.count("infeasible_without_replenishment"), 18)
        self.assertEqual(len(decision["revision_reasons"]), 18)
        self.assertEqual(decision["status"], "needs_revision")
        self.assertEqual(decision["required_approvals"], [])


if __name__ == "__main__":
    unittest.main()
