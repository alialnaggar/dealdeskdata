"""Independent commercial decision examples across the three policy profiles."""

from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import unittest

import yaml

from compile_phase1c_policy import compile_rows
from phase1c_policy_decision import evaluate_compiled_policy


ROOT = Path(__file__).parent
COMPILED = compile_rows(yaml.safe_load((ROOT / "calibration_config.yaml").read_text(encoding="utf-8")))


def deal(code="BASELINE_2026", *, price=100, cost=60, quantity=100):
    price, cost = Decimal(str(price)), Decimal(str(cost))
    total = price * quantity
    return {
        "run": {"applied_policy_set_code": code, "as_of_at": datetime(2026, 9, 1, 10, tzinfo=timezone.utc)},
        "deal": {"terms_json": {"payment_terms_days": 30, "contract_clause_codes": ["standard"]},
                 "requested_delivery_date": None},
        "lines": [{"deal_line_id": "L1", "category": "end_user_computing_and_digital_workplace",
                   "list_price": Decimal(100), "quoted_unit_price": price, "standard_cost": cost,
                   "quantity": quantity, "fulfillment_mode": "stocked_finished"}],
        "customer": {"account_status": "Active"},
        "credit": {"credit_status": "Active"}, "receivables": [],
        "facts": {"deal_total": total, "credit_over_limit_pct": Decimal(0),
                  "credit_commitments_fresh": True,
                  "lines": [{"discount_pct": (Decimal(100) - price),
                             "margin_pct": (price - cost) * 100 / price}]},
        "rules": {table: [deepcopy(row) for row in rows if row["policy_set_code"] == code]
                  for table, rows in COMPILED.items()},
    }


def ids(result):
    return {hit["rule_id"] for hit in result["rule_hits"]}


def roles(result):
    return [item["role"] for item in result["required_approvals"]]


class CommercialDecisionTests(unittest.TestCase):
    def test_ten_percent_discount_replay_has_one_sales_role(self):
        expected = {"BASELINE_2026": ["Regional_Manager"],
                    "LENIENT_EXPERIMENT": ["Regional_Manager"],
                    "STRICT_EXPERIMENT": ["Sales_Director"]}
        for code, route in expected.items():
            with self.subTest(code=code):
                result = evaluate_compiled_policy(deal(code, price=90, cost=60))
                self.assertEqual(result["status"], "approval_required")
                self.assertEqual(roles(result), route)
                self.assertEqual(result["deal_discount_pct"], 10)

    def test_credit_boundary_and_profile_conflict(self):
        for code, expected in (("BASELINE_2026", "Finance_Director"),
                               ("LENIENT_EXPERIMENT", "Finance_Director"),
                               ("STRICT_EXPERIMENT", "blocked")):
            with self.subTest(code=code):
                item = deal(code)
                item["facts"]["credit_over_limit_pct"] = Decimal(10)
                result = evaluate_compiled_policy(item)
                if expected == "blocked":
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual(roles(result), [])
                    self.assertIn("PO-STRICT-CREDIT-CAP", ids(result))
                else:
                    self.assertIn(expected, roles(result))
        baseline = deal()
        baseline["facts"]["credit_over_limit_pct"] = Decimal(15)
        self.assertIn("PO-BASE-CREDIT-EXCEPTION", ids(evaluate_compiled_policy(baseline)))
        baseline["facts"]["credit_over_limit_pct"] = Decimal("15.01")
        self.assertIn("PO-BASE-CREDIT-CAP", ids(evaluate_compiled_policy(baseline)))

    def test_margin_floor_exception_and_hard_block(self):
        self.assertNotIn("PO-BASE-MARGIN-EXCEPTION", ids(evaluate_compiled_policy(deal(cost=92))))
        result = evaluate_compiled_policy(deal(cost=93))
        self.assertEqual(roles(result), ["Sales_VP"])
        self.assertIn("PO-BASE-MARGIN-EXCEPTION", ids(result))
        result = evaluate_compiled_policy(deal(cost=95))
        self.assertEqual(result["status"], "blocked")
        self.assertIn("PO-BASE-MARGIN-SHORTFALL", ids(result))
        self.assertEqual(roles(result), [])
        self.assertIn("PO-BASE-MARGIN-NONPOSITIVE", ids(evaluate_compiled_policy(deal(cost=100))))

    def test_terms_contract_and_suppressed_routes(self):
        item = deal()
        item["deal"]["terms_json"]["payment_terms_days"] = 45
        self.assertEqual(roles(evaluate_compiled_policy(item)), ["Regional_Manager"])
        item["deal"]["terms_json"]["payment_terms_days"] = 60
        self.assertEqual(roles(evaluate_compiled_policy(item)), ["Regional_Manager", "Finance_Director"])
        item["deal"]["terms_json"]["contract_clause_codes"] = ["legal_review"]
        self.assertEqual(roles(evaluate_compiled_policy(item)),
                         ["Regional_Manager", "Finance_Director", "Legal_Compliance"])
        item["deal"]["terms_json"]["contract_clause_codes"] = ["prohibited"]
        result = evaluate_compiled_policy(item)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(roles(result), [])
        item["deal"]["terms_json"]["contract_clause_codes"] = ["standard"]
        item["deal"]["terms_json"]["payment_terms_days"] = 999
        self.assertIn("PO-BASE-PAYMENT-INVALID", ids(evaluate_compiled_policy(item)))

    def test_value_delivery_overdue_and_stale_credit(self):
        item = deal(quantity=1000)  # 100,000 EUR equals the baseline director boundary.
        self.assertEqual(roles(evaluate_compiled_policy(item)), ["Regional_Manager"])
        item = deal(quantity=1001)
        self.assertEqual(roles(evaluate_compiled_policy(item)), ["Sales_Director"])
        item["deal"]["requested_delivery_date"] = date(2026, 9, 5)
        item["facts"]["lines"][0]["earliest_full_date"] = date(2026, 9, 7)
        item["receivables"] = [{"due_date": date(2026, 8, 20), "outstanding_amount": Decimal(10)}]
        self.assertEqual(roles(evaluate_compiled_policy(item)), ["Sales_Director", "Finance_Director"])
        item["facts"]["credit_commitments_fresh"] = False
        result = evaluate_compiled_policy(item)
        self.assertEqual(result["status"], "needs_evidence")
        self.assertIn("credit_commitments_stale", result["evidence_gaps"])
        self.assertNotIn("PO-BASE-CREDIT-EXCEPTION", ids(result))
        self.assertEqual(roles(result), [])

    def test_line_discount_cannot_be_hidden_by_deal_average(self):
        item = deal(price=100)
        item["lines"].append({**item["lines"][0], "deal_line_id": "L2", "quoted_unit_price": Decimal(85)})
        item["facts"]["lines"].append({"discount_pct": Decimal(15),
                                          "margin_pct": (Decimal(85) - 60) * 100 / 85})
        item["facts"]["deal_total"] = Decimal(18500)
        result = evaluate_compiled_policy(item)
        self.assertLess(result["deal_discount_pct"], 10)
        self.assertEqual(roles(result), ["Sales_Director"])
        self.assertIn({"rule_id": "PR-BASE-DIRECTOR", "area": "pricing", "severity": "finding",
                       "scope": "L2"}, result["rule_hits"])

    def test_partial_rule_set_fails_closed(self):
        item = deal()
        item["rules"]["policy_rules"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            evaluate_compiled_policy(item)

    def test_inactive_account_is_hard_blocked(self):
        item = deal()
        item["customer"]["account_status"] = "Suspended"
        result = evaluate_compiled_policy(item)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("PO-BASE-ACCOUNT-INACTIVE", ids(result))
        self.assertEqual(roles(result), [])


@unittest.skipUnless(os.environ.get("DATABASE_URL"), "PostgreSQL integration requires DATABASE_URL")
class CompiledReaderIntegrationTests(unittest.TestCase):
    def test_database_reader_uses_loaded_rules(self):
        import psycopg
        from phase1c_reader import read_run

        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            baseline = read_run(conn, "00000000-0000-4000-8000-000000120001",
                                commercial_rule_mode="compiled")
            strict = read_run(conn, "00000000-0000-4000-8000-000000120003",
                              commercial_rule_mode="compiled")
            b = baseline["facts"]["commercial"]
            s = strict["facts"]["commercial"]
            self.assertEqual((b["deal_discount_pct"], s["deal_discount_pct"]), (10, 10))
            self.assertNotIn("PR-BASE-DIRECTOR", ids(b))
            self.assertIn("PR-STRICT-DIRECTOR", ids(s))
            credit = read_run(conn, "00000000-0000-4000-8000-000000110001",
                              commercial_rule_mode="compiled")
            self.assertIn("PO-BASE-CREDIT-EXCEPTION", ids(credit["facts"]["commercial"]))


if __name__ == "__main__":
    unittest.main()
