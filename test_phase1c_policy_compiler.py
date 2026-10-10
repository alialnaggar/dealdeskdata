"""Boundary and coverage checks for the synthetic profile compiler."""

from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from compile_phase1c_policy import PROFILE_CODES, compile_rows, render_sql


CONFIG = yaml.safe_load(Path(__file__).with_name("calibration_config.yaml").read_text(encoding="utf-8"))


class PolicyCompilerTests(unittest.TestCase):
    def test_approved_numeric_profiles_and_coverage(self):
        profiles = CONFIG["governance"]["profiles"]
        expected = {"STRICT_EXPERIMENT": (5, 5, 30), "BASELINE_2026": (10, 15, 45),
                    "LENIENT_EXPERIMENT": (15, 25, 60)}
        for code, (discount, credit, terms) in expected.items():
            with self.subTest(code=code):
                self.assertEqual(profiles[code]["pricing"]["routine_discount_max_pct"], discount)
                self.assertEqual(profiles[code]["policy"]["credit_exception_max_over_limit_pct"], credit)
                self.assertEqual(profiles[code]["policy"]["standard_payment_terms_max_days"], terms)
        rows = compile_rows(CONFIG)
        self.assertEqual({table: len(items) for table, items in rows.items()},
                         {"pricing_rules": 33, "policy_rules": 51, "approval_rules": 21})
        for table, items in rows.items():
            self.assertEqual({r["policy_set_code"] for r in items}, set(PROFILE_CODES))
            self.assertEqual(len({next(v for k, v in r.items() if k.endswith("_rule_id")) for r in items}), len(items))
        self.assertEqual(render_sql(rows), render_sql(compile_rows(CONFIG)))

    def test_boundaries_are_strict_above_and_inclusive_exception_caps(self):
        rows = compile_rows(CONFIG)
        for code in PROFILE_CODES:
            with self.subTest(code=code):
                prices = [r for r in rows["pricing_rules"] if r["policy_set_code"] == code]
                policies = [r for r in rows["policy_rules"] if r["policy_set_code"] == code]
                director = next(r for r in prices if r["pricing_rule_id"].endswith("-DIRECTOR"))
                credit = next(r for r in policies if r["policy_rule_id"].endswith("-CREDIT-EXCEPTION"))
                cap = next(r for r in policies if r["policy_rule_id"].endswith("-CREDIT-CAP"))
                threshold = director["condition_json"]["discount_pct_gt"]
                self.assertEqual(threshold, CONFIG["governance"]["profiles"][code]["pricing"]["routine_discount_max_pct"])
                self.assertEqual(credit["condition_json"]["credit_over_limit_pct_lte"],
                                 cap["condition_json"]["credit_over_limit_pct_gt"])
                self.assertEqual(credit["condition_json"]["credit_over_limit_pct_gt"], 0)

    def test_invalid_ladder_fails_before_sql_generation(self):
        changed = deepcopy(CONFIG)
        changed["governance"]["profiles"]["STRICT_EXPERIMENT"]["policy"]["credit_exception_max_over_limit_pct"] = 30
        with self.assertRaisesRegex(ValueError, "Nonmonotonic"):
            compile_rows(changed)
        changed = deepcopy(CONFIG)
        changed["governance"]["profiles"]["BASELINE_2026"]["pricing"]["discount_requires_sales_vp_above_pct"] = 10
        with self.assertRaisesRegex(ValueError, "Invalid discount ladder"):
            compile_rows(changed)


if __name__ == "__main__":
    unittest.main()
