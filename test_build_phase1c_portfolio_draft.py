"""Ensure the proposed projection is reproducible and exposes coverage gaps."""

from pathlib import Path
import json
import unittest

import yaml

from build_phase1c_portfolio_draft import build
from validate_phase1c_bom_portfolio import validate_portfolio


class DraftPortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load(Path("calibration_config.yaml").read_text(encoding="utf-8"))
        cls.contract = yaml.safe_load(Path("phase1c_data_contract.yaml").read_text(encoding="utf-8"))

    def test_full_proposed_structure_passes_but_does_not_release_generation(self):
        draft = build(self.config)
        self.assertEqual(draft, json.loads(Path("phase1c_portfolio_draft.json").read_text(encoding="utf-8")))
        result = validate_portfolio(draft, self.config, self.contract)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["metrics"]["sellable_products"], 120)
        self.assertEqual(result["metrics"]["components"], 36)
        self.assertEqual(result["metrics"]["effective_bom_variants"], 24)
        self.assertEqual(result["metrics"]["components_shared_across_two_or_more_boms"], 16)
        self.assertFalse(result["ready_for_full_generation"])

    def test_missing_component_usage_is_detected(self):
        draft = build(self.config)
        draft["bom_lines"] = [line for line in draft["bom_lines"]
                              if line["component_product_id"] != "COMP-COMPUTE-001"]
        result = validate_portfolio(draft, self.config, self.contract)
        self.assertIn("every proposed component must be used by an effective BOM", result["errors"])


if __name__ == "__main__":
    unittest.main()
