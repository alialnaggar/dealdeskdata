"""Boundary checks for one assembled configuration and its SQL row graph."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import os
import unittest

import yaml

from validate_phase1c_assembly_pilot import connected_rows, validate_assembly


HERE = Path(__file__).resolve().parent
BASE = json.loads((HERE / "phase1c_pilot_slice.json").read_text())
ASSEMBLY = json.loads((HERE / "phase1c_assembly_pilot.json").read_text())
CONTRACT = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
CONFIG = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
SCHEMA = (HERE / "schema.sql").read_text()


def check(extension):
    return validate_assembly(BASE, extension, CONTRACT, SCHEMA, CONFIG)


class AssemblyPreflightTests(unittest.TestCase):
    def test_selected_build_and_cost_are_bounded(self):
        result = check(ASSEMBLY)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["ready_for_full_generation"])
        finding = result["findings"][0]
        self.assertEqual((finding["bom_id"], finding["operation_dates"], finding["status"]),
                         ("PILOT-BOM-001", ["2026-10-05", "2026-10-06"], "feasible_uncommitted"))
        self.assertEqual(finding["required_hours"], {"PILOT-R-ASM": "2.0", "PILOT-R-TEST": "2.75"})
        self.assertEqual(finding["cost_rollup_eur"], "428.47")

    def test_rejects_ambiguous_or_invalid_bom_and_cost(self):
        cases = [
            ("bom_headers", "status", "inactive", "exactly one effective active BOM"),
            ("bom_lines", "component_product_id", "PILOT-P-DEVICE", "invalid component catalogue"),
            ("product_rows", "standard_cost", 700, "cost differs"),
        ]
        for table, field, value, expected in cases:
            with self.subTest(table=table):
                changed = deepcopy(ASSEMBLY)
                changed[table][0][field] = value
                self.assertTrue(any(expected in e for e in check(changed)["errors"]))
        changed = deepcopy(ASSEMBLY)
        duplicate = deepcopy(changed["bom_headers"][0])
        duplicate["bom_id"] = "PILOT-BOM-DUP"
        duplicate["bom_version"] = "V2"
        changed["bom_headers"].append(duplicate)
        self.assertTrue(any("exactly one effective active BOM" in e for e in check(changed)["errors"]))

    def test_rejects_component_shortage_and_capacity_gap(self):
        changed = deepcopy(ASSEMBLY)
        changed["inventory_rows"][0]["quantity_allocated"] = 8
        self.assertTrue(any("component stock is insufficient" in e for e in check(changed)["errors"]))
        changed = deepcopy(ASSEMBLY)
        changed["production_capacity"][1]["allocated_capacity_hours"] = 6
        self.assertTrue(any("no fresh fitting capacity" in e for e in check(changed)["errors"]))
        changed = deepcopy(ASSEMBLY)
        changed["bom_headers"][0]["configuration_signature_json"] = {"unexpected": "value"}
        self.assertTrue(any("configuration signature contains unknown keys" in e for e in check(changed)["errors"]))


@unittest.skipUnless(os.environ.get("DATABASE_URL"), "PostgreSQL integration requires DATABASE_URL")
class AssemblyDatabaseTests(unittest.TestCase):
    def test_connected_assembly_rows_satisfy_sql_then_rollback(self):
        import psycopg
        from psycopg import sql
        from psycopg.types.json import Jsonb
        from phase1c_reader import read_run

        rows = connected_rows(BASE, ASSEMBLY)["rows"]
        order = ("products", "customers", "suppliers", "inventory", "supplier_items", "shipping_lanes",
                 "bom_headers", "bom_lines", "production_requirements", "production_capacity", "deals", "deal_lines")
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            try:
                conn.execute("SET LOCAL search_path TO deal_desk, public")
                for table in order:
                    for row in rows[table]:
                        insert_row = {**row, "deal_status": "Draft"} if table == "deals" else row
                        names = list(insert_row)
                        query = sql.SQL("INSERT INTO deal_desk.{} ({}) VALUES ({})").format(
                            sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, names)),
                            sql.SQL(", ").join(sql.Placeholder() for _ in names))
                        values = [Jsonb(insert_row[name]) if name.endswith("_json") and insert_row[name] is not None
                                  else insert_row[name] for name in names]
                        conn.execute(query, values)
                conn.execute("UPDATE deal_desk.deals SET deal_status='Submitted' WHERE deal_id='PILOT-D-001'")
                conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
                self.assertEqual(conn.execute("SELECT count(*) FROM deal_desk.bom_lines WHERE bom_id='PILOT-BOM-001'").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT count(*) FROM deal_desk.production_capacity WHERE capacity_id LIKE 'PILOT-CAP-%'").fetchone()[0], 2)
                conn.execute("""INSERT INTO deal_desk.customer_credit_profiles
                    (customer_id, credit_limit, unbilled_committed_amount, commitments_as_of_at,
                     commitment_evidence_ref, risk_rating, credit_status, default_payment_terms_days,
                     last_review_date) VALUES
                    ('PILOT-C-001', 100000, 0, '2026-10-04T10:00:00+02:00',
                     'SYN-CREDIT-001', 'Low', 'Active', 30, '2026-09-01')""")
                conn.execute("""INSERT INTO deal_desk.deal_runs
                    (run_id, deal_id, original_policy_set_code, applied_policy_set_code, catalog_version_used,
                     as_of_at, data_snapshot_ref, input_snapshot_json, config_hash, run_status, started_at)
                    VALUES ('00000000-0000-4000-8000-000000990001', 'PILOT-D-001', 'BASELINE_2026',
                     'BASELINE_2026', 'CATALOGUE_2026_V1', '2026-10-04T12:00:00+02:00',
                     'SYN-PILOT-SNAPSHOT', '{}', 'SYN-PILOT-CONFIG', 'queued', '2026-10-04T12:00:00+02:00')""")
                bundle = read_run(conn, "00000000-0000-4000-8000-000000990001",
                                  cost_parameters=ASSEMBLY["cost_parameters"], commercial_rule_mode="reference")
                assembly = bundle["facts"]["supply"]["assembly"]["PILOT-P-BUILD"]
                self.assertEqual(assembly["bom_id"], "PILOT-BOM-001")
                self.assertEqual(assembly["component_demand"]["PILOT-P-COMP-A"], Decimal("6") / Decimal("0.99"))
                self.assertEqual(assembly["operation_days"], [date(2026, 10, 5), date(2026, 10, 6)])
                self.assertTrue(assembly["cost_rollup"]["within_5_pct"])
                self.assertEqual(bundle["facts"]["lines"][0]["production_status"], "feasible_uncommitted")
            finally:
                conn.rollback()


if __name__ == "__main__":
    unittest.main()
