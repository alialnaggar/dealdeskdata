"""Boundary tests for one priced SKU with two configured BOM costs."""

from copy import deepcopy
from pathlib import Path
import json
import unittest

import yaml

from validate_phase1c_variant_cost_pilot import evaluate_build_cost_draft, evaluate_cost_pilot


HERE = Path(__file__).resolve().parent


class VariantCostPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        cls.pilot = json.loads((HERE / "phase1c_variant_cost_pilot.json").read_text())
        cls.build_draft = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        cls.config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())

    def test_one_cost_and_one_list_price_cover_both_options(self):
        result = evaluate_cost_pilot(self.portfolio, self.pilot, self.config)
        self.assertEqual(result["errors"], [])
        self.assertEqual(set(result["rollups_eur"]), {"BOM-001", "BOM-002"})
        self.assertEqual(result["rollups_eur"], {"BOM-001": "683.33", "BOM-002": "705.33"})
        self.assertFalse(result["ready_for_full_generation"])

    def test_catalogue_cost_must_cover_more_expensive_option(self):
        pilot = deepcopy(self.pilot)
        pilot["product_standard_cost_eur"] = 700
        self.assertIn("one priced SKU needs a conservative standard cost covering its highest-cost variant",
                      evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"])

    def test_materially_more_expensive_option_cannot_hide_under_one_cost(self):
        pilot = deepcopy(self.pilot)
        pilot["component_standard_costs_eur"]["COMP-COMPUTE-002"] = 400
        errors = evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"]
        self.assertIn("variant costs cannot share one standard cost within tolerance", errors)

    def test_missing_substitute_choice_and_cost_are_visible(self):
        pilot = deepcopy(self.pilot)
        pilot["selected_substitutes"]["BOM-001"] = {}
        pilot["component_standard_costs_eur"].pop("COMP-STORAGE-002")
        errors = evaluate_cost_pilot(self.portfolio, pilot, self.config)["errors"]
        self.assertTrue(any("substitute selections" in error for error in errors))
        self.assertTrue(any("part cost" in error for error in errors))

    def test_every_buildable_sku_and_bom_has_a_cost_rollup(self):
        result = evaluate_build_cost_draft(self.portfolio, self.build_draft, self.config)
        self.assertEqual(result["errors"], [])
        self.assertEqual((result["checked_products"], result["checked_boms"]), (18, 24))
        self.assertFalse(result["ready_for_full_generation"])

    def test_batch_rejects_omitted_product_and_component_cost(self):
        draft = deepcopy(self.build_draft)
        draft["products"].pop()
        draft["component_standard_costs_eur"].pop("COMP-COMPUTE-001")
        errors = evaluate_build_cost_draft(self.portfolio, draft, self.config)["errors"]
        self.assertIn("cost draft must cover each buildable product exactly once", errors)
        self.assertIn("component costs must cover the exact draft component catalogue", errors)
        self.assertTrue(any("selected part cost" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
