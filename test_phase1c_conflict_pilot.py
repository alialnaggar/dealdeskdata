"""Check conflict source rows against the PostgreSQL reader and compiled policy."""

import json
import os
from pathlib import Path
import re
import unittest

import yaml

from render_phase1c_conflict_pilot import build, CASE_MAP

try:
    import psycopg
except ImportError:
    psycopg = None

if psycopg is not None:
    from phase1c_reader import read_run, load_provider_evidence
    from phase1c_deal_decision import assemble_deal_decision

HERE = Path(__file__).resolve().parent


class ConflictRenderTests(unittest.TestCase):
    def test_deterministic_and_no_oracle_in_submissions(self):
        args = (json.loads((HERE / "phase1c_portfolio_draft.json").read_text()),
                json.loads((HERE / "phase1c_build_cost_draft.json").read_text()),
                yaml.safe_load((HERE / "calibration_config.yaml").read_text()),
                yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text()))
        sql = build(*args)
        self.assertEqual(sql, (HERE / "phase1c_conflict_pilot.sql").read_text())
        self.assertEqual(sql.count("INSERT INTO deals "), len(CASE_MAP))
        self.assertEqual(sql.count("INSERT INTO deal_runs "), len(CASE_MAP))
        self.assertNotIn("target_bucket", sql)
        locations = set(re.findall(r"'(WH-EU-[A-Z]+)'", sql))
        self.assertTrue(locations)
        self.assertLessEqual(locations, set(args[3]["controlled_vocabularies"]["location_codes"]))
        self.assertIn("'WH-EU-WEST', 'Europe/Amsterdam'", sql)


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class ConflictReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET search_path TO deal_desk, public")
        try:
            for name in ("phase1c_buildable_master.sql", "phase1c_sellable_catalogue.sql",
                         "phase1c_vertical_pilot.sql", "phase1c_conflict_pilot.sql"):
                content = (HERE / name).read_text()
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

    def read(self, case):
        index = CASE_MAP[case]
        return read_run(self.conn, f"00000000-0000-4000-8000-{260000 + index:012d}",
                        digital_evidence_resolver=load_provider_evidence(
                            HERE / "phase1c_conflict_provider_manifest.json"),
                        cost_parameters={"workforce_cost_eur_per_hour": 30,
                                         "overhead_fraction": "0.1"},
                        commercial_rule_mode="compiled")

    def test_operational_conflicts_remain_bounded(self):
        expected = {
            "STOCK-ALLOCATED": "infeasible", "STOCK-STALE": "unknown",
            "SUPPLY-OFFER-ONLY": "conditional", "SUPPLY-CANCELLED": "infeasible",
            "DIGITAL-NO-PROOF": "binding_candidate", "DIGITAL-EXPIRED": "binding_candidate",
            "SERVICE-OUTSIDE": "infeasible",
        }
        for case, status in expected.items():
            with self.subTest(case=case):
                bundle = self.read(case)
                fact = bundle["facts"]["lines"][0]
                actual = (fact["digital"]["status"] if case.startswith("DIGITAL") else
                          fact["service"]["status"] if case.startswith("SERVICE") else
                          fact["fulfillment_status"])
                self.assertEqual(actual, status)
        self.assertEqual(assemble_deal_decision(self.read("SUPPLY-OFFER-ONLY"))["status"],
                         "needs_evidence")
        for case in ("DIGITAL-NO-PROOF", "DIGITAL-EXPIRED"):
            fact = self.read(case)["facts"]["lines"][0]["digital"]
            self.assertFalse(fact["pools"][0]["full_term_verified"])
            self.assertEqual(assemble_deal_decision(self.read(case))["status"], "needs_evidence")

    def test_commercial_conflicts_keep_source_attribution(self):
        for case, expected_area in (("CREDIT-LIMIT", "credit"),
                                    ("PRICE-FLOOR", "pricing"),
                                    ("POLICY-CLAUSE", "policy")):
            with self.subTest(case=case):
                bundle = self.read(case)
                self.assertEqual(bundle["facts"]["lines"][0]["fulfillment_status"],
                                 "confirmed_by_date")
                decision = assemble_deal_decision(bundle)
                self.assertTrue(any(hit["area"] == expected_area
                                    for hit in decision["commercial_rule_hits"]))
                self.assertNotEqual(decision["status"], "approved")

    def test_build_conflicts_do_not_infer_unrepresented_capacity(self):
        substitute = self.read("BUILD-SUBSTITUTE")
        line = substitute["facts"]["lines"][0]
        self.assertEqual(line["fulfillment_status"], "feasible_uncommitted")
        plan = substitute["facts"]["supply"]["assembly_by_bom"]["BOM-001"]
        self.assertEqual(plan["substitution_groups"][0]["selected_component_product_id"],
                         "COMP-NETWORK_AND_POWER-002")
        self.assertIn("CONFLICT-INBOUND-16", plan["candidate_evidence_ids"])
        for case, reason in (("BUILD-CAPACITY-STALE", "production_capacity_evidence_missing_or_stale"),
                             ("BUILD-HORIZON", "confirmed_component_supply_after_capacity_horizon")):
            with self.subTest(case=case):
                bundle = self.read(case)
                fact = bundle["facts"]["lines"][0]
                self.assertEqual(fact["fulfillment_status"], "unknown")
                self.assertEqual(fact["production_unknown_reason"], reason)
                self.assertEqual(assemble_deal_decision(bundle)["status"], "needs_evidence")


if __name__ == "__main__":
    unittest.main()
