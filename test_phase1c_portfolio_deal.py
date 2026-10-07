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
                                         "overhead_fraction": "0.1"})

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


if __name__ == "__main__":
    unittest.main()
