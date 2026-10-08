"""Check exact customer quotas and PostgreSQL constraints for the master slice."""

from collections import Counter
import json
import os
from pathlib import Path
import re
import unittest

import yaml

from render_phase1c_customer_master import build

try:
    import psycopg
except ImportError:
    psycopg = None


HERE = Path(__file__).resolve().parent


class CustomerMasterTests(unittest.TestCase):
    def test_render_and_ledger_are_reproducible(self):
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
        sql, ledger = build(config, contract)
        self.assertEqual(sql, (HERE / "phase1c_customer_master.sql").read_text())
        self.assertEqual(ledger, json.loads((HERE / "phase1c_customer_commitment_ledger.json").read_text()))
        self.assertEqual(sql.count("INSERT INTO customers "), 80)
        self.assertEqual(sql.count("INSERT INTO customer_credit_profiles "), 80)
        self.assertEqual(len(ledger["commitments"]), 80)
        self.assertEqual(len({r["evidence_ref"] for r in ledger["commitments"]}), 80)
        self.assertEqual(Counter(r["adverse_signal"] for r in ledger["commitments"])["synthetic_account_hold"], 3)

    def test_bad_config_is_rejected(self):
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
        config["dataset"]["customers"] += 1
        with self.assertRaisesRegex(ValueError, "customer count drift"):
            build(config, contract)


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class CustomerMasterDatabaseTests(unittest.TestCase):
    def test_constraints_and_exact_distributions(self):
        conn = psycopg.connect(os.environ["DATABASE_URL"])
        try:
            for statement in re.findall(r"^INSERT INTO .*?;", (HERE / "phase1c_customer_master.sql").read_text(), re.M):
                conn.execute(statement)
            config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
            contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
            expected = [
                ("size_segment", config["dataset"]["customer_segment_counts"]),
                ("industry", {k: int(v * .8) for k, v in contract["controlled_vocabularies"]["customer_industry_target_share_pct"].items()}),
                ("country_code", {k: int(v * .8) for k, v in contract["controlled_vocabularies"]["customer_country_target_share_pct"].items()}),
            ]
            for column, counts in expected:
                actual = dict(conn.execute(f"SELECT {column}, count(*) FROM deal_desk.customers GROUP BY {column}").fetchall())
                self.assertEqual(actual, counts)
            for column, counts in (("risk_rating", config["commercial_supply"]["credit_profiles"]["risk_rating_exact_counts"]),
                                   ("credit_status", config["commercial_supply"]["credit_profiles"]["credit_status_exact_counts"])):
                actual = dict(conn.execute(f"SELECT {column}, count(*) FROM deal_desk.customer_credit_profiles GROUP BY {column}").fetchall())
                self.assertEqual(actual, counts)
            rows = conn.execute("""SELECT c.size_segment, p.default_payment_terms_days, count(*)
                FROM deal_desk.customers c JOIN deal_desk.customer_credit_profiles p USING (customer_id)
                GROUP BY 1,2""").fetchall()
            actual = {(segment, days): count for segment, days, count in rows}
            expected_terms = {(segment, int(days)): count for segment, counts in
                config["commercial_supply"]["credit_profiles"]["default_payment_terms_exact_counts_by_segment"].items()
                for days, count in counts.items() if count}
            self.assertEqual(actual, expected_terms)
        finally:
            conn.rollback()
            conn.close()


if __name__ == "__main__":
    unittest.main()
