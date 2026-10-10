"""Ensure the proposed projection is reproducible and exposes coverage gaps."""

from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import json
import unittest

import yaml

from build_phase1c_portfolio_draft import build
from phase1c_bom_selection import select_bom_components
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
        self.assertEqual(result["metrics"]["components_shared_across_two_or_more_boms"], 18)
        self.assertEqual(result["metrics"]["boms_with_substitute_groups"], 1)
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

    def test_component_roles_have_explicit_per_build_quantities(self):
        draft = build(self.config)
        roles = {row["product_id"]: row["attributes_json"]["component_role"]
                    for row in draft["products"] if row["fulfillment_mode"] == "component"}
        expected = {"compute_kit": (1, 0), "storage_drive": (2, 1),
                    "network_power_kit": (1, 0), "enclosure_kit": (1, 0)}
        for header in draft["bom_headers"]:
            by_role = {}
            for line in (row for row in draft["bom_lines"] if row["bom_id"] == header["bom_id"]):
                role = roles[line["component_product_id"]]
                self.assertEqual((line["required_quantity_per_output"], line["scrap_pct"]), expected[role])
                by_role.setdefault(role, []).append(line)
            self.assertEqual(set(by_role), set(expected))
            self.assertEqual(len(by_role["enclosure_kit"]), 1)

    def test_one_network_option_group_selects_one_of_two_same_family_parts(self):
        draft = build(self.config)
        candidates = [row for row in draft["bom_lines"]
                      if row["bom_id"] == "BOM-001" and
                      row["substitute_group_code"] == "NETWORK_OPTION"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual({row["priority"] for row in candidates}, {0, 1})
        components = {row["product_id"]: row for row in draft["products"]}
        self.assertEqual({components[row["component_product_id"]]["attributes_json"]["component_family"]
                          for row in candidates}, {"network_and_power"})

    def test_two_options_of_one_product_use_different_components(self):
        draft = build(self.config)
        product = draft["bom_headers"][0]["finished_product_id"]
        boms = [row["bom_id"] for row in draft["bom_headers"]
                if row["finished_product_id"] == product]
        self.assertEqual(len(boms), 2)
        component_sets = [{row["component_product_id"] for row in draft["bom_lines"]
                           if row["bom_id"] == bom_id} for bom_id in boms]
        self.assertNotEqual(*component_sets)

    def test_draft_substitute_is_selected_when_preferred_part_is_unavailable(self):
        draft = build(self.config)
        bom = dict(draft["bom_headers"][0], output_quantity=Decimal("1"))
        lines = [dict(row, required_quantity_per_output=Decimal(str(row["required_quantity_per_output"])),
                      scrap_pct=Decimal(str(row["scrap_pct"])))
                 for row in draft["bom_lines"] if row["bom_id"] == bom["bom_id"]]
        alternative = next(row for row in lines if row["substitute_group_code"] and row["priority"] == 1)
        as_of = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
        bundle = {
            "production_capacity": [{"location_id": "WH-EU-CENTRAL"}],
            "inventory": [{"inventory_id": "INV-ALT", "location_id": "WH-EU-CENTRAL",
                           "product_id": alternative["component_product_id"],
                           "quantity_on_hand": Decimal("1"), "quantity_allocated": Decimal("0"),
                           "snapshot_at": as_of}],
            "inbound_supply": [],
        }
        selected, groups = select_bom_components(bom, lines, Decimal("1"), bundle, as_of)
        self.assertEqual(len(selected), 4)
        self.assertEqual(groups[0]["selected_component_product_id"], alternative["component_product_id"])
        self.assertEqual(groups[0]["required_units_for_build"], Decimal("1"))


if __name__ == "__main__":
    unittest.main()
