"""Checks a connected pilot slice without treating it as a full dataset."""

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
import json
import os
import unittest

import yaml

from validate_phase1c_pilot import ID_FIELD, TABLES, add_workdays, lane_arrival, validate_pilot


HERE = Path(__file__).resolve().parent
PILOT = json.loads((HERE / "phase1c_pilot_slice.json").read_text(encoding="utf-8"))
CONTRACT = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text(encoding="utf-8"))
CONFIG = yaml.safe_load((HERE / "calibration_config.yaml").read_text(encoding="utf-8"))
SCHEMA = (HERE / "schema.sql").read_text(encoding="utf-8")


def check(pilot):
    return validate_pilot(pilot, CONTRACT, SCHEMA, CONFIG)


class PilotPreflightTests(unittest.TestCase):
    def test_connected_slice_and_bounded_findings(self):
        result = check(PILOT)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["row_counts"], {table: 1 for table in TABLES})
        self.assertFalse(result["ready_for_full_generation"])
        self.assertEqual(result["findings"], [
            {"code": "supplier_lead_out_of_horizon", "source_id": "PILOT-O-001",
             "latest_offer_date": "2026-11-13", "planning_horizon_end": "2026-11-03",
             "status": "unknown_or_conditional"},
            {"code": "lane_date_candidate", "source_id": "PILOT-DL-001",
             "lane_id": "PILOT-LANE-001", "dispatch": "2026-10-05",
             "arrival": "2026-10-07", "status": "candidate_not_stock_commitment"},
        ])

    def test_calendar_boundaries_and_configured_horizon(self):
        self.assertEqual(add_workdays(date(2026, 10, 4), 0, [1, 2, 3, 4, 5]), date(2026, 10, 5))
        self.assertEqual(add_workdays(date(2026, 10, 4), 30, [1, 2, 3, 4, 5]), date(2026, 11, 13))
        lane = PILOT["rows"]["shipping_lanes"][0]
        self.assertEqual(lane_arrival(datetime.fromisoformat("2026-10-02T16:00:00+02:00"), lane),
                         (date(2026, 10, 5), date(2026, 10, 7)))
        changed = deepcopy(CONFIG)
        changed["fulfillment_production_calibration"]["proposed_parameters"]["production_capacity"]["horizon_calendar_days"] = 45
        self.assertNotIn("supplier_lead_out_of_horizon",
                         {f["code"] for f in validate_pilot(PILOT, CONTRACT, SCHEMA, changed)["findings"]})

    def test_cross_table_and_payload_failures(self):
        cases = [
            ("customers", "region", "FR-IDF", "country and region differ"),
            ("inventory", "quantity_allocated", 11, "allocation exceeds stock"),
            ("shipping_lanes", "origin_time_zone", "Europe/Paris", "origin and time zone differ"),
            ("deal_lines", "product_id", "MISSING", "deal/product is missing or not sellable"),
        ]
        for table, field, value, expected in cases:
            with self.subTest(table=table, field=field):
                changed = deepcopy(PILOT)
                changed["rows"][table][0][field] = value
                self.assertTrue(any(expected in e for e in check(changed)["errors"]))
        changed = deepcopy(PILOT)
        changed["rows"]["suppliers"][0]["order_calendar_json"]["holiday_dates"] = ["2026-12-25"]
        self.assertTrue(any("holidays are omitted" in e for e in check(changed)["errors"]))

    def test_schema_shape_and_answer_isolation(self):
        changed = deepcopy(PILOT)
        del changed["rows"]["products"][0]["stock_uom"]
        self.assertIn("products[0]: fields differ from schema.sql", check(changed)["errors"])
        changed = deepcopy(PILOT)
        changed["rows"]["deals"][0]["historical_decision"] = "Approved"
        self.assertTrue(any("pilot cannot contain historical outcomes" in e for e in check(changed)["errors"]))


@unittest.skipUnless(os.environ.get("DATABASE_URL"), "PostgreSQL integration requires DATABASE_URL")
class PilotDatabaseTests(unittest.TestCase):
    def test_pilot_rows_pass_database_constraints_then_rollback(self):
        import psycopg
        from psycopg import sql
        from psycopg.types.json import Jsonb

        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            try:
                for table in TABLES:
                    for row in PILOT["rows"][table]:
                        names = list(row)
                        query = sql.SQL("INSERT INTO deal_desk.{} ({}) VALUES ({})").format(
                            sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, names)),
                            sql.SQL(", ").join(sql.Placeholder() for _ in names))
                        values = [Jsonb(row[name]) if name.endswith("_json") else row[name] for name in names]
                        conn.execute(query, values)
                for table in TABLES:
                    key = PILOT["rows"][table][0][ID_FIELD[table]]
                    query = sql.SQL("SELECT count(*) FROM deal_desk.{} WHERE {} = %s").format(
                        sql.Identifier(table), sql.Identifier(ID_FIELD[table]))
                    self.assertEqual(conn.execute(query, (key,)).fetchone()[0], 1)
            finally:
                conn.rollback()


if __name__ == "__main__":
    unittest.main()
