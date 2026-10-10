"""Focused interface, substitution and power tests for one synthetic build."""

from copy import deepcopy
import json
import unittest

from validate_phase1c_technical_fit_pilot import HERE, validate


class TechnicalFitPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        cls.pilot = json.loads((HERE / "phase1c_technical_fit_pilot.json").read_text())

    def test_both_substitute_kits_pass_and_generation_remains_gated(self):
        result = validate(self.portfolio, self.pilot)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["candidate_results"]), 2)
        self.assertEqual({row["calculated_load_watts"] for row in result["candidate_results"].values()},
                         {214, 219})
        self.assertTrue(result["synthetic_fit_check_passed"])
        self.assertFalse(result["ready_for_full_generation"])

    def test_drive_interface_mismatch_is_rejected(self):
        pilot = deepcopy(self.pilot)
        pilot["component_specs"]["COMP-STORAGE-001"]["host_interface"] = "SATA"
        self.assertIn("storage drive interface does not match the compute kit",
                      validate(self.portfolio, pilot)["errors"])

    def test_alternative_must_fit_as_well_as_preferred_part(self):
        pilot = deepcopy(self.pilot)
        pilot["component_specs"]["COMP-NETWORK_AND_POWER-002"]["psu_output_watts"] = 200
        errors = validate(self.portfolio, pilot)["errors"]
        self.assertTrue(any("COMP-NETWORK_AND_POWER-002: kit power supply" in error
                            for error in errors))

    def test_undeclared_or_missing_part_specification_is_rejected(self):
        pilot = deepcopy(self.pilot)
        pilot["component_specs"].pop("COMP-NETWORK_AND_POWER-002")
        self.assertIn("pilot specifications must cover exactly the BOM candidates",
                      validate(self.portfolio, pilot)["errors"])

    def test_current_bom_quantities_are_checked(self):
        portfolio = deepcopy(self.portfolio)
        line = next(row for row in portfolio["bom_lines"]
                    if row["bom_id"] == "BOM-001" and row["component_product_id"] == "COMP-STORAGE-001")
        line["required_quantity_per_output"] = 3
        self.assertIn("BOM-001: storage_drive candidates or quantity differ from this pilot",
                      validate(portfolio, self.pilot)["errors"])


if __name__ == "__main__":
    unittest.main()
