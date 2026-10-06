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

    def test_business_mix_keeps_network_devices_supplier_sourced(self):
        draft = build(self.config)
        sellable = [row for row in draft["products"] if row["is_sellable"]]
        assembled = [row for row in sellable if row["fulfillment_mode"] == "make_to_order"]
        by_category = {}
        for row in assembled:
            category = row["attributes_json"]["category"]
            by_category[category] = by_category.get(category, 0) + 1
        self.assertEqual(by_category, {
            "end_user_computing_and_digital_workplace": 2,
            "servers_and_compute_infrastructure": 10,
            "storage_and_data_protection": 6,
        })
        network_devices = [row for row in sellable
                           if row["attributes_json"]["category"] == "networking_and_connectivity"
                           and row["product_type"] == "physical"]
        self.assertTrue(all(row["fulfillment_mode"] == "supplier_finished"
                            for row in network_devices))

    def test_every_build_has_one_part_from_each_proposed_family(self):
        draft = build(self.config)
        families = {row["product_id"]: row["attributes_json"]["component_family"]
                    for row in draft["products"] if row["fulfillment_mode"] == "component"}
        expected = set(self.config["fulfillment_production_calibration"]["proposed_parameters"]
                       ["component_catalogue"]["family_counts"])
        for header in draft["bom_headers"]:
            actual = {families[line["component_product_id"]] for line in draft["bom_lines"]
                      if line["bom_id"] == header["bom_id"]}
            self.assertEqual(actual, expected, header["bom_id"])


if __name__ == "__main__":
    unittest.main()
