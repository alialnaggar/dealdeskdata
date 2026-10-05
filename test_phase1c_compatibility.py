"""Pure tests for typed compatibility/dependency findings."""

import unittest

from phase1c_compatibility import evaluate_compatibility


LINES = [
    {"deal_line_id": "L1", "product_id": "P-A", "fulfillment_group_code": "G1",
     "attributes_json": {"edition": "pro"}, "configuration_json": {"service_tier": "gold"}},
    {"deal_line_id": "L2", "product_id": "P-B", "fulfillment_group_code": "G1",
     "attributes_json": {}, "configuration_json": {}},
]
DEAL = {"requirements_json": {"requested_outcomes": ["install"]}}


def rule(rule_id, rule_type, condition, source=None, target=None, severity="blocker"):
    return {"compatibility_rule_id": rule_id, "rule_type": rule_type, "scope_type": "whole_deal",
            "source_product_id": source, "target_product_id": target, "condition_json": condition,
            "severity": severity, "message": rule_id}


class CompatibilityTests(unittest.TestCase):
    def test_requires_and_excludes_are_attributed(self):
        findings = evaluate_compatibility(LINES, DEAL, [
            rule("R-REQ", "requires_product", {"operator": "present"}, "P-A", "P-B"),
            rule("R-EX", "excludes_product", {"operator": "present"}, "P-A", "P-B"),
        ])
        self.assertEqual([f["status"] for f in findings], ["pass", "fail"])

    def test_attribute_and_required_field(self):
        findings = evaluate_compatibility(LINES, DEAL, [
            rule("R-ATTR", "attribute_constraint", {"attribute": "edition", "operator": "equals", "expected": "pro"}, "P-A"),
            rule("R-FIELD", "required_deal_field", {"field": "requirements_json.requested_outcomes"}),
        ])
        self.assertEqual([f["status"] for f in findings], ["pass", "pass"])

    def test_unsupported_operator_stays_visible(self):
        finding = evaluate_compatibility(LINES, DEAL, [
            rule("R-BAD", "attribute_constraint", {"attribute": "edition", "operator": "regex", "expected": "pro"}, "P-A")
        ])[0]
        self.assertEqual(finding["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
