"""Independent expectations for the 14 reference deals (not fixture SQL assertions)."""
import os
import subprocess
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg

from phase1c_reader import load_provider_evidence, read_run


ROOT = Path(__file__).parent


def load_fixture_rows():
    # The existing fixture script rolls back by design. Reuse only its row
    # inserts/updates in this disposable database, leaving expected answers out.
    statements = [line for line in (ROOT / "phase1c_row_fixtures.sql").read_text().splitlines()
                  if line.startswith(("INSERT INTO ", "UPDATE deals SET "))]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql") as temp:
        temp.write("\\set ON_ERROR_STOP on\nBEGIN;\nSET search_path TO deal_desk, public;\n")
        temp.write("\n".join(statements))
        temp.write("\n" + (ROOT / "phase1c_rule_rows.sql").read_text())
        temp.write("\nCOMMIT;\n")
        temp.flush()
        subprocess.run(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-q", "-f", temp.name], check=True)


class ReaderReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_fixture_rows()
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def read(self, number):
        return read_run(self.conn, f"00000000-0000-4000-8000-000000{number:02d}0001")

    def test_stock_then_confirmed_receipt(self):
        b = self.read(1)
        p = "stock_then_confirmed_receipt-P"
        self.assertEqual(b["facts"]["supply"]["stock"][p][0]["free"], 8)
        self.assertEqual(b["facts"]["supply"]["binding_receipts"][p][0]["free"], 3)
        self.assertTrue(b["facts"]["lines"][0]["shipping_by_request"])
        self.assertTrue(b["facts"]["lines"][0]["partial_available_now"])
        self.assertEqual(b["facts"]["lines"][0]["quantity_by_requested_date"], 10)
        self.assertEqual(b["facts"]["lines"][0]["fulfillment_status"], "confirmed_by_date")

    def test_assembly_later_workday(self):
        facts = self.read(2)["facts"]
        a = facts["supply"]["assembly"]["assembly_later_workday-P"]
        self.assertEqual(a["build_units"], 8)
        self.assertEqual(a["component_demand"]["assembly_later_workday-C"], 16)
        self.assertEqual(a["required_hours"][("assembly", "workforce")], 5)
        self.assertEqual(a["first_fitting_day"], date(2026, 9, 2))
        self.assertEqual(facts["supply"]["production_receipt_convention"],
                         "confirmed_receipt_usable_on_expected_date")
        self.assertEqual(facts["lines"][0]["production_status"], "feasible_uncommitted")
        self.assertEqual(facts["lines"][0]["fulfillment_status"], "feasible_uncommitted")
        self.assertTrue(facts["lines"][0]["shipping_by_request"])

    def test_offer_without_supplier_commitment(self):
        b = self.read(3)
        self.assertEqual(b["facts"]["lines"][0]["supplier_offer_days"], [10])
        self.assertEqual(b["facts"]["supply"]["binding_receipts"]["offer_without_supplier_commitment-P"], [])
        self.assertFalse(b["facts"]["lines"][0]["shipping_by_request"])
        self.assertEqual(b["facts"]["lines"][0]["fulfillment_status"], "conditional")

    def test_digital_binding(self):
        d = self.read(4)["facts"]["lines"][0]["digital"]
        self.assertEqual(d["concurrent_demand"], 5)
        self.assertEqual(d["pools"][0]["free"], 6)
        self.assertEqual(d["status"], "binding_candidate")
        verified_provider_record = load_provider_evidence(ROOT / "phase1c_provider_evidence_fixture.json")
        checked = read_run(self.conn, "00000000-0000-4000-8000-000000040001",
                           digital_evidence_resolver=verified_provider_record)["facts"]["lines"][0]["digital"]
        self.assertEqual(checked["status"], "confirmed_by_date")
        self.assertTrue(checked["pools"][0]["full_term_verified"])
        invalid = read_run(self.conn, "00000000-0000-4000-8000-000000040001",
                           digital_evidence_resolver=lambda ref: dict(verified_provider_record(ref), covers_until=date(2027, 8, 4)))
        self.assertEqual(invalid["facts"]["lines"][0]["digital"]["status"], "binding_candidate")
        wrong_provider = read_run(self.conn, "00000000-0000-4000-8000-000000040001",
                                  digital_evidence_resolver=lambda ref: dict(verified_provider_record(ref), provider_id="other"))
        self.assertEqual(wrong_provider["facts"]["lines"][0]["digital"]["status"], "binding_candidate")

    def test_digital_provisional(self):
        d = self.read(5)["facts"]["lines"][0]["digital"]
        self.assertEqual(d["pools"][0]["free"], 6)
        self.assertFalse(d["pools"][0]["binding"])
        self.assertEqual(d["status"], "conditional")

    def test_digital_stale(self):
        d = self.read(6)["facts"]["lines"][0]["digital"]
        self.assertTrue(d["pools"][0]["binding"])
        self.assertFalse(d["pools"][0]["fresh"])
        self.assertEqual(d["status"], "unknown")

    def test_friday_cutoff(self):
        fact = self.read(7)["facts"]["lines"][0]
        option = fact["shipping_options"][0]
        self.assertEqual((option["dispatch"], option["arrival"]), (date(2026, 9, 7), date(2026, 9, 9)))
        self.assertEqual(fact["fulfillment_status"], "late_alternative")

    def test_installation_rule_missing(self):
        b = self.read(8)["facts"]["lines"][0]
        self.assertEqual(b["installation"], "unknown")
        self.assertTrue(b["shipping_by_request"])

    def test_installation_ineligible(self):
        b = self.read(9)["facts"]["lines"][0]
        self.assertEqual(b["installation"], "ineligible")
        self.assertEqual(len(b["installation_evidence"]), 1)
        self.assertTrue(b["shipping_by_request"])

    def test_inventory_stale(self):
        b = self.read(10)["facts"]
        self.assertEqual(b["supply"]["stock"]["inventory_snapshot_expired-P"][0]["free"], 7)
        self.assertFalse(b["supply"]["stock"]["inventory_snapshot_expired-P"][0]["fresh"])
        self.assertFalse(b["lines"][0]["shipping_by_request"])
        self.assertEqual(b["lines"][0]["fulfillment_status"], "unknown")

    def test_credit_exception(self):
        f = self.read(11)["facts"]
        self.assertEqual(f["credit_exposure"], 110000)
        self.assertEqual(f["credit_over_limit_pct"], 10)
        self.assertEqual(f["commercial"]["credit_status"], "exception")
        self.assertIn("Finance_Director", [x["role"] for x in f["commercial"]["required_approvals"]])

    def test_discount_replay(self):
        run_ids = [f"00000000-0000-4000-8000-00000012000{i}" for i in (1, 2, 3)]
        bundles = [read_run(self.conn, run_id) for run_id in run_ids]
        self.assertEqual([x["facts"]["lines"][0]["discount_pct"] for x in bundles], [10] * 3)
        self.assertEqual({x["run"]["applied_policy_set_code"] for x in bundles},
                         {"BASELINE_2026", "LENIENT_EXPERIMENT", "STRICT_EXPERIMENT"})
        self.assertEqual({x["run"]["deal_id"] for x in bundles}, {"D-discount_profile_replay"})
        self.assertEqual([x["facts"]["commercial"]["pricing_status"] for x in bundles],
                         ["routine", "routine", "exception"])
        self.assertEqual([[r["role"] for r in x["facts"]["commercial"]["required_approvals"]] for x in bundles],
                         [[], [], ["Sales_Director"]])

    def test_assembled_cost_evidence(self):
        b = read_run(self.conn, "00000000-0000-4000-8000-000000130001",
                     cost_parameters={"workforce_cost_eur_per_hour": 30, "overhead_fraction": "0.1"})
        self.assertEqual(b["lines"][0]["standard_cost"], 1375)
        self.assertEqual(b["bom_lines"][0]["standard_cost"], 1100)
        self.assertEqual(b["facts"]["supply"]["assembly"]["assembled_cost_rollup-P"]["required_hours"][("assembly", "workforce")], 5)
        self.assertEqual(b["facts"]["supply"]["assembly"]["assembled_cost_rollup-P"]["cost_rollup"],
                         {"material": 1100, "labor": 150, "overhead": 125, "total": 1375, "within_5_pct": True})

    def test_two_lines_shared_component(self):
        s = self.read(14)["facts"]["supply"]
        self.assertEqual(s["assembly"]["two_lines_share_component-P"]["component_demand"]["two_lines_share_component-C"], 14)
        self.assertEqual(sum(x["free"] for x in s["stock"]["two_lines_share_component-C"])
                         + sum(x["free"] for x in s["binding_receipts"]["two_lines_share_component-C"]), 13)
        self.assertIsNone(s["assembly"]["two_lines_share_component-P"]["first_fitting_day"])
        self.assertEqual(self.read(14)["facts"]["lines"][0]["production_status"], "infeasible_without_replenishment")


if __name__ == "__main__":
    unittest.main()
