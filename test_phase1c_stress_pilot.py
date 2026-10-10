"""Check the seeded 36-deal pilot load, as-of isolation and decision spread."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import unittest

import yaml

from render_phase1c_stress_pilot import build

try:
    import psycopg
except ImportError:
    psycopg = None

if psycopg is not None:
    from phase1c_reader import read_run, load_provider_evidence
    from phase1c_deal_decision import assemble_deal_decision

HERE = Path(__file__).resolve().parent


class StressRenderTests(unittest.TestCase):
    def test_seeded_output_and_diagnostic_counts(self):
        inputs = (json.loads((HERE / "phase1c_portfolio_draft.json").read_text()),
                  json.loads((HERE / "phase1c_build_cost_draft.json").read_text()),
                  yaml.safe_load((HERE / "calibration_config.yaml").read_text()),
                  yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text()))
        sql, report = build(*inputs)
        self.assertEqual(sql, (HERE / "phase1c_stress_pilot.sql").read_text())
        self.assertEqual(report, json.loads((HERE / "phase1c_stress_pilot_report.json").read_text()))
        self.assertEqual(report["sql_sha256"], hashlib.sha256(sql.encode()).hexdigest())
        self.assertEqual(sql.count("INSERT INTO deals "), 18)
        self.assertEqual(sql.count("INSERT INTO deal_lines "), report["stress_lines"])
        self.assertEqual(sum(report["line_mode_counts"].values()), report["stress_lines"])
        self.assertEqual(sum(int(k) * v for k, v in report["lines_per_deal"].items()),
                         report["stress_lines"])
        self.assertEqual(report["pilot_deals_total"], 36)
        self.assertNotIn("target_bucket", sql)


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class StressReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET search_path TO deal_desk, public")
        try:
            for name in ("phase1c_buildable_master.sql", "phase1c_sellable_catalogue.sql",
                         "phase1c_vertical_pilot.sql", "phase1c_conflict_pilot.sql",
                         "phase1c_stress_pilot.sql"):
                for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                            (HERE / name).read_text(), re.M | re.S):
                    cls.conn.execute(statement)
        except Exception:
            cls.conn.rollback()
            cls.conn.close()
            raise
        cls.proof = load_provider_evidence(HERE / "phase1c_conflict_provider_manifest.json")

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def read(self, run_number):
        return read_run(self.conn, f"00000000-0000-4000-8000-{run_number:012d}",
                        digital_evidence_resolver=self.proof,
                        cost_parameters={"workforce_cost_eur_per_hour": 30,
                                         "overhead_fraction": "0.1"},
                        commercial_rule_mode="compiled")

    def test_all_mixed_runs_and_as_of_replay(self):
        status = Counter()
        modes = Counter()
        stock_sources = Counter()
        for index in range(1, 19):
            bundle = self.read(270000 + index)
            row = self.conn.execute("SELECT dataset_type, deal_status FROM deal_desk.deals WHERE deal_id=%s",
                                    (bundle["deal"]["deal_id"],)).fetchone()
            self.assertEqual(row, ("generated_test", "Submitted"))
            decision = assemble_deal_decision(bundle)
            self.assertNotEqual(decision["status"], "approved")
            status[decision["status"]] += 1
            modes.update(line["fulfillment_mode"] for line in bundle["lines"])
            stock_sources.update(source for finding in decision["specialists"]["availability"]
                                 for source in finding["source_ids"] if source.startswith("STRESS-STOCK"))
        self.assertEqual(sum(status.values()), 18)
        self.assertEqual(len(modes), 5)
        self.assertGreaterEqual(status["needs_revision"], 1)
        self.assertTrue(any(count > 1 for count in stock_sources.values()))
        # Later snapshots must never rewrite findings at the earlier as-of time.
        baseline = self.read(260001)
        self.assertEqual(baseline["facts"]["lines"][0]["fulfillment_status"],
                         "confirmed_by_date")
        self.assertFalse(any(source.startswith("STRESS-") for source in
                             assemble_deal_decision(baseline)["specialists"]["availability"][0]["source_ids"]))


if __name__ == "__main__":
    unittest.main()
