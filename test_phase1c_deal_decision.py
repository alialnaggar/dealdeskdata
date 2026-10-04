"""Decision gates over independently prepared commercial and fulfillment facts."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import os
import unittest

from phase1c_deal_decision import assemble_deal_decision
from test_phase1c_policy_decision import deal


def complete_bundle():
    item = deepcopy(deal())
    item["run"].update(run_id="test-run", catalog_version_used="CATALOGUE_2026_V1")
    item["deal"].update(deal_id="test-deal")
    item["lines"][0].update(line_id="L1", product_id="P1", is_active=True,
                             is_sellable=True, installation_requested=False,
                             requested_activation_date=None)
    item["facts"].update(credit_exposure=Decimal(100), supply={"assembly": {}})
    item["facts"]["lines"][0].update(line_id="L1", fulfillment_status="confirmed_by_date",
                                      earliest_full_date=date(2026, 9, 3),
                                      quantity_by_requested_date=Decimal(100),
                                      shipping_options=[{"stock_id": "I1", "supply_ids": [],
                                                         "arrival": date(2026, 9, 3)}])
    item["bom"] = []
    return item


class DecisionGateTests(unittest.TestCase):
    def test_clean_deal_routes_to_a_real_review_role(self):
        result = assemble_deal_decision(complete_bundle())
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual([r["role"] for r in result["required_approvals"]], ["Regional_Manager"])
        self.assertEqual(result["specialists"]["availability"][0]["source_ids"], ["I1"])

    def test_shortage_and_late_date_withhold_route(self):
        for state in ("infeasible", "late_alternative"):
            with self.subTest(state=state):
                item = complete_bundle()
                item["facts"]["lines"][0]["fulfillment_status"] = state
                result = assemble_deal_decision(item)
                self.assertEqual(result["status"], "needs_revision")
                self.assertFalse(result["required_approvals"])

    def test_unknown_installation_and_tentative_production(self):
        item = complete_bundle()
        item["lines"][0]["installation_requested"] = True
        item["facts"]["lines"][0]["installation"] = "unknown"
        self.assertEqual(assemble_deal_decision(item)["status"], "needs_evidence")
        item["facts"]["lines"][0]["installation"] = "ineligible"
        self.assertEqual(assemble_deal_decision(item)["status"], "blocked")
        item = complete_bundle()
        item["lines"][0]["fulfillment_mode"] = "make_to_order"
        item["lines"][0]["configuration_json"] = {"edition": "E"}
        item["bom"] = [{"bom_id": "B1", "finished_product_id": "P1",
                        "configuration_signature_json": {"edition": "E"}}]
        item["facts"]["lines"][0].update(fulfillment_status="feasible_uncommitted",
                                          shipping_by_request=True)
        result = assemble_deal_decision(item)
        self.assertEqual(result["status"], "needs_commitment")
        self.assertTrue(result["specialists"]["availability"][0]["tentative"])

    def test_hard_policy_block_and_stale_credit_withhold_route(self):
        item = complete_bundle()
        item["customer"]["account_status"] = "Suspended"
        result = assemble_deal_decision(item)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["required_approvals"])
        item = complete_bundle()
        item["facts"]["credit_commitments_fresh"] = False
        result = assemble_deal_decision(item)
        self.assertEqual(result["status"], "needs_evidence")
        self.assertIn("credit_commitments_stale", result["evidence_gaps"])

    def test_digital_reference_alone_does_not_confirm(self):
        item = complete_bundle()
        item["lines"][0].update(fulfillment_mode="digital_activation", requested_activation_date=date(2026, 9, 3))
        item["facts"]["lines"][0]["digital"] = {"status": "binding_candidate", "pools": [{"id": "D1"}]}
        self.assertEqual(assemble_deal_decision(item)["status"], "needs_evidence")
        item["facts"]["lines"][0]["digital"]["status"] = "confirmed_by_date"
        self.assertEqual(assemble_deal_decision(item)["status"], "approval_required")

    def test_config_and_cost_mismatch(self):
        item = complete_bundle()
        item["lines"][0]["is_active"] = False
        self.assertEqual(assemble_deal_decision(item)["status"], "blocked")
        item = complete_bundle()
        item["facts"]["supply"]["assembly"] = {"P1": {"cost_rollup": {"within_5_pct": False}}}
        self.assertEqual(assemble_deal_decision(item)["status"], "needs_evidence")

    def test_lines_must_match_reader_facts(self):
        item = complete_bundle()
        item["facts"]["lines"][0]["line_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Misaligned"):
            assemble_deal_decision(item)


@unittest.skipUnless(os.environ.get("DATABASE_URL"), "PostgreSQL integration requires DATABASE_URL")
class ReferenceDealIntegrationTests(unittest.TestCase):
    """Run the 14 reference deals using compiled rules loaded by the CI workflow."""

    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def read(self, number, **kwargs):
        from phase1c_reader import read_run
        return read_run(self.conn, f"00000000-0000-4000-8000-000000{number:02d}0001",
                        commercial_rule_mode="compiled", **kwargs)

    def test_all_14_reference_runs_have_attributed_gated_outputs(self):
        expected_lines = {14: 2}
        for number in range(1, 15):
            with self.subTest(reference_case=number):
                result = assemble_deal_decision(self.read(number))
                self.assertEqual(len(result["specialists"]), 6)
                self.assertEqual(len(result["specialists"]["availability"]), expected_lines.get(number, 1))
                self.assertEqual(result["required_approvals"],
                                 result["specialists"]["approval_routing"]["required_roles"])
                if result["status"] != "approval_required":
                    self.assertEqual(result["required_approvals"], [])
                self.assertEqual(result["policy_set_code"], "BASELINE_2026")

    def test_reference_contradictions_do_not_become_final_approval(self):
        expectations = {2: "needs_commitment", 3: "needs_commitment", 5: "needs_commitment",
                        6: "needs_evidence", 7: "needs_revision", 8: "needs_evidence",
                        9: "blocked", 10: "needs_evidence", 14: "needs_revision"}
        for number, status in expectations.items():
            with self.subTest(reference_case=number):
                result = assemble_deal_decision(self.read(number))
                self.assertEqual(result["status"], status)
                self.assertEqual(result["required_approvals"], [])

    def test_digital_binding_needs_independent_proof(self):
        from phase1c_reader import load_provider_evidence
        self.assertEqual(assemble_deal_decision(self.read(4))["status"], "needs_evidence")
        resolver = load_provider_evidence("phase1c_provider_evidence_fixture.json")
        verified = assemble_deal_decision(self.read(4, digital_evidence_resolver=resolver))
        self.assertEqual(verified["specialists"]["availability"][0]["status"], "confirmed_by_date")
        self.assertNotIn("digital_confirmation_missing:", " ".join(verified["evidence_gaps"]))

    def test_credit_and_discount_attribution(self):
        from phase1c_reader import read_run
        credit = assemble_deal_decision(self.read(11))
        self.assertIn("PO-BASE-CREDIT-EXCEPTION", {h["rule_id"] for h in credit["specialists"]["credit"]["rule_hits"]})
        for suffix, expected_role in ((1, "Regional_Manager"), (2, "Regional_Manager"), (3, "Sales_Director")):
            with self.subTest(replay=suffix):
                run_id = f"00000000-0000-4000-8000-00000012000{suffix}"
                bundle = read_run(self.conn, run_id, commercial_rule_mode="compiled")
                result = assemble_deal_decision(bundle)
                self.assertEqual(result["specialists"]["pricing"]["deal_discount_pct"], Decimal(10))
                self.assertIn(expected_role, [r["role"] for r in
                                              bundle["facts"]["commercial"]["required_approvals"]])


if __name__ == "__main__":
    unittest.main()
