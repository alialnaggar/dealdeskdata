"""Check the parameter contract catches inconsistencies before row generation."""

from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from validate_phase1c_calibration import validate


CONFIG = yaml.safe_load(Path(__file__).with_name("calibration_config.yaml").read_text(encoding="utf-8"))


class CalibrationContractTests(unittest.TestCase):
    def test_current_config_is_consistent_but_not_frozen(self):
        result = validate(CONFIG)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["ready_for_generation"])
        self.assertTrue(any("capacity horizon" in x for x in result["review_before_freeze"]))

    def test_broken_counts_and_price_order_are_rejected(self):
        changed = deepcopy(CONFIG)
        changed["dataset"]["customer_segment_counts"]["SMB"] += 1
        changed["product_catalogue"]["categories"]["servers_and_compute_infrastructure"]["price_eur"]["p50"] = 0
        changed["conflict_injection"]["requested_case_mix_pct"]["clean"] -= 1
        errors = validate(changed)["errors"]
        self.assertIn("customer segment counts", errors)
        self.assertIn("generated-test case counts", errors)
        self.assertIn("price anchors are not ordered: servers_and_compute_infrastructure", errors)

    def test_digital_proof_and_bom_coverage_are_enforced(self):
        changed = deepcopy(CONFIG)
        fields = changed["fulfillment_production_calibration"]["proposed_parameters"]["digital_capacity"]["trusted_provider_evidence_required_fields"]
        fields.remove("provider_id")
        changed["fulfillment_production_calibration"]["proposed_parameters"]["BOMs"]["effective_configured_BOM_variants_range"][0] = 10
        errors = validate(changed)["errors"]
        self.assertIn("digital proof fields differ from reader's trusted manifest", errors)
        self.assertIn("BOM variants cannot cover the proposed assembled products", errors)

    def test_component_rounding_contract_is_required(self):
        changed = deepcopy(CONFIG)
        changed["fulfillment_production_calibration"]["proposed_parameters"]["component_catalogue"]["component_unit_indivisible"] = False
        self.assertIn("component stock rounding contract differs from reader", validate(changed)["errors"])

    def test_historical_line_mix_mean_and_bins_are_checked(self):
        changed = deepcopy(CONFIG)
        changed["dataset"]["historical_lines_per_deal_sampling_percent"][8] += 1
        errors = validate(changed)["errors"]
        self.assertIn("historical line-count sampling weights", errors)
        self.assertIn("historical line-count expected mean differs from target", errors)


if __name__ == "__main__":
    unittest.main()
