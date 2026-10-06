"""Pure tests for portfolio coverage; fixtures are deliberately small and test-only."""
from copy import deepcopy
import unittest

import yaml

from validate_phase1c_bom_portfolio import validate_portfolio

CONFIG = yaml.safe_load(open("calibration_config.yaml", encoding="utf-8"))
CONTRACT = yaml.safe_load(open("phase1c_data_contract.yaml", encoding="utf-8"))
CATALOG = CONFIG["product_catalogue"]["metadata"]["catalogue_version"]


def small_config():
    config = deepcopy(CONFIG)
    config["dataset"]["sellable_products"] = 2
    params = config["fulfillment_production_calibration"]["proposed_parameters"]
    params["component_catalogue"].update({
        "non_sellable_component_count": 3,
        "family_counts": {"compute": 1, "storage": 1, "network_and_power": 1, "chassis_and_other": 0},
        "total_product_rows_with_120_sellable": 5,
        "shared_across_at_least_two_BOMs_min_share": 0.3,
    })
    params["BOMs"].update({
        "make_to_order_sellable_count": 1,
        "effective_configured_BOM_variants_range": [2, 2],
    })
    return config


def portfolio():
    products = [
        {"product_id": "SELL-STOCK", "catalog_version": CATALOG, "is_sellable": True,
         "product_type": "physical", "fulfillment_mode": "stocked_finished", "attributes_json": {}},
        {"product_id": "SELL-BUILD", "catalog_version": CATALOG, "is_sellable": True,
         "product_type": "physical", "fulfillment_mode": "make_to_order", "attributes_json": {}},
        {"product_id": "COMP-COMPUTE", "catalog_version": CATALOG, "is_sellable": False,
         "product_type": "component", "fulfillment_mode": "component", "attributes_json": {"component_family": "compute"}},
        {"product_id": "COMP-STORAGE", "catalog_version": CATALOG, "is_sellable": False,
         "product_type": "component", "fulfillment_mode": "component", "attributes_json": {"component_family": "storage"}},
        {"product_id": "COMP-NETWORK", "catalog_version": CATALOG, "is_sellable": False,
         "product_type": "component", "fulfillment_mode": "component", "attributes_json": {"component_family": "network_and_power"}},
    ]
    sigs = [{"selected_options": ["standard"]}, {"selected_options": ["enhanced"]}]
    headers = []
    for bom, sig in zip(("BOM-STANDARD", "BOM-ENHANCED"), sigs):
        headers.append({
            "bom_id": bom, "finished_product_id": "SELL-BUILD", "catalog_version": CATALOG,
            "configuration_signature_json": sig, "output_quantity": 1,
            "effective_from": "2026-01-01T00:00:00Z", "effective_to": None, "status": "active",
        })
    def line(bom, component, group=None, priority=0):
        return {"bom_line_id": f"{bom}-{component}", "bom_id": bom, "component_product_id": component,
                "required_quantity_per_output": 1, "scrap_pct": 1, "substitute_group_code": group,
                "priority": priority, "is_mandatory": True}
    requirements = [{
        "requirement_id": f"{bom}-ASM", "bom_id": bom, "operation_seq": 1,
        "capability_code": "assembly", "resource_type": "workforce", "setup_hours": 0.5,
        "hours_per_unit": 0.5, "batch_size": 4, "status": "active",
    } for bom in ("BOM-STANDARD", "BOM-ENHANCED")]
    return {
        "catalog_version": CATALOG, "as_of_at": "2026-10-06T12:00:00Z", "products": products,
        "offered_configurations": [
            {"product_id": "SELL-BUILD", "configuration_signature_json": sigs[0]},
            {"product_id": "SELL-BUILD", "configuration_signature_json": sigs[1]},
        ],
        "bom_headers": headers,
        "bom_lines": [line("BOM-STANDARD", "COMP-COMPUTE"), line("BOM-STANDARD", "COMP-STORAGE"),
                      line("BOM-ENHANCED", "COMP-COMPUTE"), line("BOM-ENHANCED", "COMP-NETWORK")],
        "production_requirements": requirements,
    }


class BomPortfolioTests(unittest.TestCase):
    def check(self, data=None):
        return validate_portfolio(data or portfolio(), small_config(), CONTRACT)

    def test_explicit_configurations_map_to_one_bom_but_generation_stays_gated(self):
        result = self.check()
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["portfolio_coverage_valid"])
        self.assertFalse(result["ready_for_full_generation"])
        self.assertEqual(result["metrics"]["effective_bom_variants"], 2)
        self.assertAlmostEqual(result["metrics"]["shared_component_share"], 1 / 3, places=3)

    def test_missing_effective_bom_fails_coverage(self):
        data = portfolio()
        data["bom_headers"].pop()
        self.assertTrue(any("exactly one effective active BOM" in e for e in self.check(data)["errors"]))

    def test_overlapping_active_versions_fail(self):
        data = portfolio()
        duplicate = deepcopy(data["bom_headers"][0])
        duplicate.update({"bom_id": "BOM-OVERLAP", "effective_from": "2026-10-01T00:00:00Z"})
        data["bom_headers"].append(duplicate)
        self.assertTrue(any("active BOM periods overlap" in e for e in self.check(data)["errors"]))

    def test_nonoverlapping_historical_version_is_allowed(self):
        data = portfolio()
        historical = deepcopy(data["bom_headers"][0])
        historical.update({"bom_id": "BOM-OLD", "effective_from": "2025-01-01T00:00:00Z",
                           "effective_to": "2026-01-01T00:00:00Z"})
        data["bom_headers"].append(historical)
        self.assertEqual(self.check(data)["errors"], [])

    def test_noncomponent_reference_and_scrap_at_100_are_rejected(self):
        data = portfolio()
        data["bom_lines"][0]["component_product_id"] = "SELL-STOCK"
        data["bom_lines"][1]["scrap_pct"] = 100
        errors = self.check(data)["errors"]
        self.assertTrue(any("not a component product" in e for e in errors))
        self.assertTrue(any("scrap percent must be in [0, 100)" in e for e in errors))

    def test_component_reuse_minimum_is_checked(self):
        data = portfolio()
        data["bom_lines"][2]["component_product_id"] = "COMP-NETWORK"
        self.assertIn("component reuse across BOMs is below the current proposal minimum",
                      self.check(data)["errors"])

    def test_projection_field_drift_is_rejected(self):
        data = portfolio()
        del data["bom_headers"][0]["effective_to"]
        self.assertTrue(any("header projection fields differ" in e for e in self.check(data)["errors"]))

    def test_substitute_group_limit_is_checked(self):
        data = portfolio()
        data["bom_lines"][0]["substitute_group_code"] = "POWER"
        data["bom_lines"].append({
            "bom_line_id": "BOM-STANDARD-ALT", "bom_id": "BOM-STANDARD",
            "component_product_id": "COMP-NETWORK", "required_quantity_per_output": 1,
            "scrap_pct": 0, "substitute_group_code": "POWER", "priority": 1, "is_mandatory": True,
        })
        self.assertIn("BOMs with substitute groups exceed the current proposal maximum",
                      self.check(data)["errors"])
        self.assertIn("BOM-STANDARD: substitute group POWER mixes component families",
                      self.check(data)["errors"])


if __name__ == "__main__":
    unittest.main()
