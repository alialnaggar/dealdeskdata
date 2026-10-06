"""Check that readiness findings respond to real changes in draft inputs."""

from copy import deepcopy
import json
import unittest

import yaml

from audit_phase1c_build_readiness import HERE, audit


class ReadinessAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        cls.costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        cls.config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())

    def test_current_draft_keeps_evidence_gate_open(self):
        result = audit(self.portfolio, self.costs, self.config)
        self.assertEqual(len(result["component_specifications_missing"]), 36)
        self.assertEqual(len(result["boms_awaiting_detailed_compatibility"]), 24)
        self.assertEqual(len(result["margin_outliers_above_proposed_p90"]), 1)
        self.assertFalse(result["ready_for_full_generation"])

    def test_margin_change_removes_only_the_outlier(self):
        costs = deepcopy(self.costs)
        costs["products"][0]["product_standard_cost_eur"] = 770
        result = audit(self.portfolio, costs, self.config)
        self.assertEqual(result["margin_outliers_above_proposed_p90"], [])
        self.assertEqual(len(result["boms_awaiting_detailed_compatibility"]), 24)
        self.assertFalse(result["price_comparability_verified"])

    def test_part_specification_updates_affected_bom_set(self):
        portfolio = deepcopy(self.portfolio)
        for component in portfolio["products"]:
            if component["fulfillment_mode"] != "component":
                continue
            attrs = component["attributes_json"]
            for family, fields in {
                "compute": ("socket_or_controller_interface", "rated_watts"),
                "storage": ("host_interface", "form_factor"),
                "network_and_power": ("host_interface", "rated_watts"),
                "chassis_and_other": ("supported_form_factor", "power_budget_watts"),
            }.items():
                if attrs["component_family"] == family:
                    attrs.update({field: "example" for field in fields})
        result = audit(portfolio, self.costs, self.config)
        self.assertEqual(result["component_specifications_missing"], {})
        self.assertEqual(len(result["boms_awaiting_detailed_compatibility"]), 24)
        self.assertFalse(result["ready_for_full_generation"])


if __name__ == "__main__":
    unittest.main()
