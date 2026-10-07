"""Read a real draft BOM through the deal reader using disposable SQL rows."""

import os
import re
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


if __name__ == "__main__":
    unittest.main()
