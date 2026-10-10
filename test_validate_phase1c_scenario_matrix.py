"""Guard scenario coverage and separation before investing in generated rows."""

from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from validate_phase1c_scenario_matrix import manifest, validate


HERE = Path(__file__).resolve().parent


class ScenarioMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = yaml.safe_load((HERE / "phase1c_scenario_matrix.yaml").read_text())
        cls.config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())

    def test_complete_matrix_and_reproducible_manifest(self):
        self.assertEqual(validate(self.matrix, self.config), [])
        result = manifest(HERE, self.matrix)
        self.assertEqual(result["pilot_target_deals"], 18)
        self.assertEqual(result["evaluation_target_cases"], 36)
        self.assertEqual(result, manifest(HERE, self.matrix))
        self.assertEqual(len(result["source_sha256"]), 7)

    def test_missing_evidence_family_cannot_pass(self):
        draft = deepcopy(self.matrix)
        draft["archetypes"] = [c for c in draft["archetypes"] if c["mode"] != "digital_activation"]
        draft["pilot"]["target_deals"] = len(draft["archetypes"])
        draft["evaluation"]["target_cases"] = len(draft["archetypes"]) * 2
        self.assertTrue(any("mode coverage differs" in error for error in validate(draft, self.config)))

    def test_evaluation_isolation_is_required(self):
        draft = deepcopy(self.matrix)
        draft["evaluation"]["answer_keys_agent_visible"] = True
        self.assertTrue(any("agent-visible" in error for error in validate(draft, self.config)))

    def test_setup_cannot_contain_answer_key(self):
        draft = deepcopy(self.matrix)
        draft["archetypes"][0]["setup"] = "fresh_stock_expected_decision_approved"
        self.assertTrue(any("outcome leakage" in error for error in validate(draft, self.config)))


if __name__ == "__main__":
    unittest.main()
