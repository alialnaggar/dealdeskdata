from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from validate_phase1c_column_rules import validate, schema_columns


HERE = Path(__file__).resolve().parent
SQL = (HERE / "schema.sql").read_text(encoding="utf-8")
CONTRACT = yaml.safe_load((HERE / "phase1c_column_rules.yaml").read_text(encoding="utf-8"))


class ColumnContractTests(unittest.TestCase):
    def test_all_columns_covered_but_open_reviews_block_generation(self):
        result = validate(SQL, CONTRACT)
        self.assertEqual((result["tables"], result["columns"]), (24, 266))
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["ready_for_generation"])
        self.assertEqual(len(result["review_before_generation"]), 6)
        self.assertEqual({item.split(":", 1)[0] for item in result["review_before_generation"]}, {
            "products.attributes_json", "products.list_price", "products.standard_cost",
            "suppliers.order_calendar_json", "compatibility_rules.condition_json",
            "agent_execution_log.output_json"})
        self.assertEqual(sum(bool(row.get("resolved_by")) for table in CONTRACT["tables"].values()
                             for row in table.values()), 8)

    def test_removed_column_and_type_drift_fail(self):
        changed = deepcopy(CONTRACT)
        del changed["tables"]["inbound_supply"]["expected_date"]
        changed["tables"]["products"]["standard_cost"]["sql_type"] = "TEXT"
        errors = validate(SQL, changed)["errors"]
        self.assertTrue(any("inbound_supply: missing=" in e for e in errors))
        self.assertTrue(any("products.standard_cost: SQL sql_type drift" == e for e in errors))

    def test_timestamp_type_is_not_parsed_as_time(self):
        columns = schema_columns(SQL)
        self.assertEqual(columns["inventory"]["snapshot_at"]["sql_type"], "TIMESTAMPTZ")
        self.assertEqual(columns["shipping_lanes"]["cutoff_local_time"]["sql_type"], "TIME")
        changed = deepcopy(CONTRACT)
        changed["tables"]["inventory"]["snapshot_at"]["sql_type"] = "TIME"
        self.assertIn("inventory.snapshot_at: SQL sql_type drift", validate(SQL, changed)["errors"])

    def test_unexplained_field_fails(self):
        changed = deepcopy(CONTRACT)
        changed["tables"]["deals"]["terms_json"]["validation"] = ""
        self.assertIn("deals.terms_json: missing validation", validate(SQL, changed)["errors"])


if __name__ == "__main__":
    unittest.main()
