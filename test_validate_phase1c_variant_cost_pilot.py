"""Boundary tests for one priced SKU with two configured BOM costs."""

from copy import deepcopy
from pathlib import Path
import json
import unittest

import yaml

from validate_phase1c_variant_cost_pilot import evaluate_cost_pilot


HERE = Path(__file__).resolve().parent


class VariantCostPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        cls.pilot = json.loads((HERE / "phase1c_variant_cost_pilot.json").read_text())
        cls.config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())

    def test_one_cost_and_one_list_price_cover_both_options(self):
        result = evaluate_cost_pilot(self.portfolio, self.pilot, self.config)
        self.assertEqual(result["errors"], [])
        self.assertEqual(set(result["rollups_eur"]), {"BOM-001", "BOM-002"})
        self.assertEqual(result["rollups_eur"], {"BOM-001": "688.56", "BOM-002": "710.78"})
        self.assertFalse(result["ready_for_full_generation"])

    def test_catalogue_cost_must_cover_more_expensive_option(self):
        pilot = deepcopy(self.pilot)
        pilot["product_standard_cost_eur"] = 700
        self.assertIn("one priced SKU needs a conservative standard cost covering its highest-cost variant",
                      evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"])

    def test_materially_more_expensive_option_cannot_hide_under_one_cost(self):
        pilot = deepcopy(self.pilot)
        pilot["component_standard_costs_eur"]["COMP-COMPUTE-002"] = 200
        errors = evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"]
        self.assertIn("variant costs cannot share one standard cost within tolerance", errors)

    def test_missing_substitute_choice_and_cost_are_visible(self):
        pilot = deepcopy(self.pilot)
        pilot["selected_substitutes"]["BOM-001"] = {}
        pilot["component_standard_costs_eur"].pop("COMP-STORAGE-002")
        errors = evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"]
        self.assertTrue(any("substitute selections" in error for error in errors))
        self.assertTrue(any("part cost" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
