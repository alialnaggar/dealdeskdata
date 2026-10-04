from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from validate_phase1c_column_rules import validate


HERE = Path(__file__).resolve().parent
SQL = (HERE / "schema.sql").read_text(encoding="utf-8")
CONTRACT = yaml.safe_load((HERE / "phase1c_column_rules.yaml").read_text(encoding="utf-8"))


class ColumnContractTests(unittest.TestCase):
    def test_all_columns_covered_but_open_reviews_block_generation(self):
        result = validate(SQL, CONTRACT)
        self.assertEqual((result["tables"], result["columns"]), (24, 266))
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["ready_for_generation"])
        self.assertGreater(len(result["review_before_generation"]), 0)

    def test_removed_column_and_type_drift_fail(self):
        changed = deepcopy(CONTRACT)
        del changed["tables"]["inbound_supply"]["expected_date"]
        changed["tables"]["products"]["standard_cost"]["sql_type"] = "TEXT"
        errors = validate(SQL, changed)["errors"]
        self.assertTrue(any("inbound_supply: missing=" in e for e in errors))
        self.assertTrue(any("products.standard_cost: SQL sql_type drift" == e for e in errors))

    def test_unexplained_field_fails(self):
        changed = deepcopy(CONTRACT)
        changed["tables"]["deals"]["terms_json"]["validation"] = ""
        self.assertIn("deals.terms_json: missing validation", validate(SQL, changed)["errors"])


if __name__ == "__main__":
    unittest.main()
