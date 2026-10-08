"""Check provisional historical input quotas and transaction-safe SQL loading."""

from collections import Counter
import json
import os
from pathlib import Path
import re
import unittest

import yaml

from render_phase1c_historical_inputs import build, PREFIX

try:
    import psycopg
except ImportError:
    psycopg = None


HERE = Path(__file__).resolve().parent
FILES = [HERE / f"{PREFIX}{n:02d}.sql" for n in range(1, 9)]


def inputs():
    return (json.loads((HERE / "phase1c_portfolio_draft.json").read_text()),
            json.loads((HERE / "phase1c_build_cost_draft.json").read_text()),
            yaml.safe_load((HERE / "calibration_config.yaml").read_text()),
            yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text()),
            json.loads((HERE / "phase1c_customer_commitment_ledger.json").read_text()))


class HistoricalInputTests(unittest.TestCase):
    def test_exact_quotas_no_oracles_and_deterministic_shards(self):
        shards, report = build(*inputs())
        self.assertEqual(shards, [f.read_text() for f in FILES])
        self.assertEqual(report, json.loads((HERE / "phase1c_historical_inputs_report.json").read_text()))
        self.assertEqual(report["historical_deals"], 400)
        self.assertEqual(report["deal_lines"], 1200)
        self.assertEqual(report["lines_per_deal"],
                         {"1": 50, "2": 87, "3": 135, "4": 80, "5": 40, "6": 6, "7": 1, "8": 1})
        self.assertEqual(report["top_product_line_share"], .64)
        self.assertEqual(report["customers_used"], 80)
        sql = "".join(shards)
        for token in ("historical_decision", "decision_reason", "approved_by_roles_json",
                      "INSERT INTO deal_runs", "INSERT INTO agent_execution_log"):
            self.assertNotIn(token, sql)
        self.assertEqual(sql.count("INSERT INTO deals "), 400)
        self.assertEqual(sql.count("INSERT INTO deal_lines "), 1200)
        self.assertEqual(sql.count("UPDATE deals SET deal_status='Submitted'"), 400)


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class HistoricalInputDatabaseTests(unittest.TestCase):
    def test_load_and_database_distribution(self):
        conn = psycopg.connect(os.environ["DATABASE_URL"])
        try:
            conn.execute("SET search_path TO deal_desk, public")
            for file in (HERE / "phase1c_buildable_master.sql",
                         HERE / "phase1c_sellable_catalogue.sql",
                         HERE / "phase1c_customer_master.sql", *FILES):
                for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                            file.read_text(), re.M | re.S):
                    conn.execute(statement)
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
            counts = conn.execute("""SELECT count(*), count(DISTINCT customer_id),
                count(*) FILTER (WHERE historical_decision IS NOT NULL OR decision_reason IS NOT NULL)
                FROM deal_desk.deals WHERE deal_id LIKE 'HIST-DEAL-%'""").fetchone()
            self.assertEqual(counts, (400, 80, 0))
            bins = dict(conn.execute("""SELECT line_count, count(*) FROM (
                SELECT deal_id, count(*) AS line_count FROM deal_desk.deal_lines
                WHERE deal_id LIKE 'HIST-DEAL-%' GROUP BY deal_id) x GROUP BY line_count""").fetchall())
            self.assertEqual(bins, {1: 50, 2: 87, 3: 135, 4: 80, 5: 40, 6: 6, 7: 1, 8: 1})
            occurrences = [row[0] for row in conn.execute("""SELECT count(*) FROM deal_desk.deal_lines
                WHERE deal_id LIKE 'HIST-DEAL-%' GROUP BY product_id ORDER BY count(*) DESC""")]
            self.assertEqual(len(occurrences), 120)
            self.assertEqual(sum(occurrences), 1200)
            self.assertEqual(sum(occurrences[:24]), 768)
            self.assertGreaterEqual(min(occurrences), 3)
            self.assertEqual(conn.execute("""SELECT count(*) FROM deal_desk.deals
                WHERE deal_id LIKE 'HIST-DEAL-%' AND submitted_at >= '2026-09-01'""").fetchone()[0], 0)
            from validate_phase1c_generated_rows import load_rows, validate_rows
            rows = load_rows(conn)
            rows["deals"] = [row for row in rows["deals"] if row["deal_id"].startswith("HIST-DEAL-")]
            rows["deal_lines"] = [row for row in rows["deal_lines"] if row["deal_id"].startswith("HIST-DEAL-")]
            for table in ("suppliers", "inventory", "purchase_orders", "inbound_supply",
                          "production_capacity", "shipping_lanes", "compatibility_rules"):
                rows[table] = []
            contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
            self.assertEqual(validate_rows(rows, contract)["errors"], [])
        finally:
            conn.rollback()
            conn.close()


if __name__ == "__main__":
    unittest.main()
