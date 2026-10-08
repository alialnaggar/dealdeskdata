"""Read five generated source-to-deal paths through the PostgreSQL reader."""

import json
import os
from pathlib import Path
import re
import unittest

import yaml

from render_phase1c_vertical_pilot import build, SELECTED

try:
    import psycopg
except ImportError:
    psycopg = None

if psycopg is not None:
    from phase1c_reader import load_provider_evidence, read_run
    from phase1c_deal_decision import assemble_deal_decision


HERE = Path(__file__).resolve().parent


class VerticalPilotRenderTests(unittest.TestCase):
    def test_rebuild_is_deterministic_and_deals_contain_no_target_labels(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
        sql, proof = build(portfolio, costs, config, contract)
        self.assertEqual(sql, (HERE / "phase1c_vertical_pilot.sql").read_text())
        self.assertEqual(proof, json.loads((HERE / "phase1c_vertical_provider_manifest.json").read_text()))
        self.assertEqual(sql.count("INSERT INTO deals "), 5)
        self.assertEqual(sql.count("INSERT INTO deal_runs "), 5)
        self.assertNotIn("target_bucket", sql)
        self.assertEqual(len(SELECTED), 5)


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class VerticalPilotReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET search_path TO deal_desk, public")
        try:
            for file in ("phase1c_buildable_master.sql", "phase1c_sellable_catalogue.sql",
                         "phase1c_vertical_pilot.sql"):
                content = (HERE / file).read_text()
                for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;", content,
                                            re.M | re.S):
                    cls.conn.execute(statement)
        except Exception:
            cls.conn.rollback()
            cls.conn.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def read(self, index):
        return read_run(self.conn, f"00000000-0000-4000-8000-{260000 + index:012d}",
                        digital_evidence_resolver=load_provider_evidence(
                            HERE / "phase1c_vertical_provider_manifest.json"),
                        cost_parameters={"workforce_cost_eur_per_hour": 30,
                                         "overhead_fraction": "0.1"},
                        commercial_rule_mode="compiled")

    def test_five_modes_reach_expected_evidence_boundaries(self):
        expected = ("confirmed_by_date", "confirmed_by_date", "feasible_uncommitted",
                    "confirmed_by_date", "conditional")
        for index, (mode, status) in enumerate(zip(SELECTED, expected), 1):
            with self.subTest(mode=mode):
                bundle = self.read(index)
                line = bundle["facts"]["lines"][0]
                actual = (line["digital"]["status"] if mode == "digital_activation" else
                          line["service"]["status"] if mode == "scheduled_service" else
                          line["fulfillment_status"])
                self.assertEqual(actual, status)
                self.assertEqual(bundle["lines"][0]["fulfillment_mode"], mode)
                decision = assemble_deal_decision(bundle)
                self.assertNotEqual(decision["status"], "blocked")
        digital = self.read(4)["facts"]["lines"][0]["digital"]
        self.assertTrue(digital["pools"][0]["full_term_verified"])
        service = self.read(5)
        self.assertFalse(service["facts"]["lines"][0]["service"]["slot_committed"])
        self.assertEqual(assemble_deal_decision(service)["status"], "needs_commitment")


if __name__ == "__main__":
    unittest.main()
