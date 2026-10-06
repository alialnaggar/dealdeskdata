from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from validate_phase1c_data_contract import validate_contract, validate_payload


CONTRACT = yaml.safe_load(
    (Path(__file__).resolve().parent / "phase1c_data_contract.yaml").read_text(encoding="utf-8")
)


class DataContractTests(unittest.TestCase):
    def test_current_contract_is_structurally_ready_but_dataset_is_not_frozen(self):
        result = validate_contract(CONTRACT)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["ready_for_generation"])

    def test_regions_and_timezones_cannot_drift(self):
        changed = deepcopy(CONTRACT)
        changed["controlled_vocabularies"]["destination_regions"]["DE"].append("FR-INVALID")
        changed["controlled_vocabularies"]["location_codes"]["WH-EU-CENTRAL"]["time_zone"] = "Not/AZone"
        errors = validate_contract(changed)["errors"]
        self.assertIn("regions for DE must use the DE- prefix", errors)
        self.assertIn("WH-EU-CENTRAL has invalid IANA time zone", errors)

    def test_supplier_and_shipping_calendar_rows(self):
        supplier = {
            "working_weekdays": [1, 2, 3, 4, 5],
            "holiday_dates": [],
            "time_zone": "Europe/Berlin",
        }
        self.assertEqual(validate_payload("supplier_calendar", supplier, CONTRACT), [])
        self.assertEqual(validate_payload("shipping_weekdays", [1, 2, 3, 4, 5], CONTRACT), [])
        bad = dict(supplier, working_weekdays=[1, True, 8], holiday_dates=["2026-12-25"],
                   time_zone="Not/AZone", unexpected=True)
        self.assertEqual(len(validate_payload("supplier_calendar", bad, CONTRACT)), 4)
        for weekdays in ([], [1, 1], [0, 1], [True, 2], "Mon-Fri"):
            with self.subTest(weekdays=weekdays):
                self.assertTrue(validate_payload("shipping_weekdays", weekdays, CONTRACT))

    def test_component_stock_rounding_contract(self):
        changed = deepcopy(CONTRACT)
        changed["component_stock"]["indivisible"] = False
        self.assertIn("component stock contract must preserve whole units and aggregate rounding",
                      validate_contract(changed)["errors"])

    def test_configured_builds_separate_same_product_variants(self):
        changed = deepcopy(CONTRACT)
        changed["configured_builds"]["same_product_variant_demand"] = "group_by_product"
        self.assertIn("configured build contract must separate BOM variants and unbound finished stock",
                      validate_contract(changed)["errors"])

    def test_build_platform_and_option_vocabularies_are_typed(self):
        changed = deepcopy(CONTRACT)
        changed["configured_builds"]["build_platforms"] = ["server", "server"]
        self.assertIn("configured build_platforms must be nonempty unique strings",
                      validate_contract(changed)["errors"])
        attrs = {"archetype_code": "RACK_SERVER", "demand_class": "regular",
                 "build_platform": "server", "offered_options": ["standard", "alternate"]}
        self.assertEqual(validate_payload("product_attributes", attrs, CONTRACT, mode="physical"), [])
        attrs["offered_options"] = ["standard", "premium"]
        self.assertIn("offered_options must be a nonempty unique allowed list",
                      validate_payload("product_attributes", attrs, CONTRACT, mode="physical"))

    def test_substitution_selection_contract_is_required(self):
        changed = deepcopy(CONTRACT)
        changed["configured_builds"]["substitution_selection"]["preference_order"] = "priority_only"
        self.assertIn("configured build contract must define deterministic substitute selection",
                      validate_contract(changed)["errors"])

    def test_production_horizon_preserves_unknown_supply(self):
        changed = deepcopy(CONTRACT)
        changed["production_horizon"]["infer_capacity_after_boundary"] = True
        self.assertIn("production horizon contract must preserve uncertainty beyond represented capacity",
                      validate_contract(changed)["errors"])

    def test_terms_and_evidence_payloads_are_typed(self):
        terms = {
            "payment_terms_days": 30,
            "contract_clause_codes": ["standard"],
            "allow_partial_delivery": False,
        }
        self.assertEqual(validate_payload("deal_terms", terms, CONTRACT), [])
        bad_terms = dict(terms, payment_method="card", payment_terms_days=17)
        self.assertGreaterEqual(len(validate_payload("deal_terms", bad_terms, CONTRACT)), 2)
        good_evidence = [{
            "evidence_ref": "E-1",
            "evidence_type": "provider_proof",
            "source_class": "synthetic_provider_manifest",
            "issued_at": "2026-09-01T10:00:00Z",
        }]
        self.assertEqual(validate_payload("evidence_refs", good_evidence, CONTRACT), [])
        good_output = {
            "agent_name": "Credit",
            "status": "conditional",
            "findings": [{
                "code": "credit_review",
                "severity": "approval_required",
                "message": "Review required",
                "evidence_refs": [],
            }],
        }
        self.assertEqual(validate_payload("agent_output", good_output, CONTRACT), [])

    def test_product_line_requirement_and_provider_payloads_reject_drift(self):
        attrs = {
            "archetype_code": "CAT-CLOUD-001",
            "demand_class": "regular",
            "edition": "business",
        }
        self.assertEqual(validate_payload("product_attributes", attrs, CONTRACT, mode="digital_activation"), [])
        self.assertTrue(validate_payload("product_attributes", dict(attrs, unexpected=True), CONTRACT, mode="digital_activation"))
        line = {"edition": "business", "units_per_period": 5}
        self.assertEqual(validate_payload("line_configuration", line, CONTRACT, mode="digital", product_attributes=attrs), [])
        self.assertTrue(validate_payload("line_configuration", {"edition": "wrong", "units_per_period": 5}, CONTRACT, mode="digital", product_attributes=attrs))
        requirements = {"constraints": [{"code": "installation_region", "value": ["DE-BE"]}]}
        self.assertEqual(validate_payload("requirements", requirements, CONTRACT), [])
        provider = {
            "evidence_ref": "E-1", "product_id": "P-1", "provider_id": None,
            "configuration_signature_json": {}, "region_code": "DE-BE", "term_code": "12m",
            "capacity_unit": "instance", "capacity_total": 10, "quantity_allocated": 2,
            "commitment_status": "binding", "verified_at": "2026-09-01T10:00:00Z",
            "covers_from": "2026-09-04", "covers_until": "2027-09-04",
        }
        self.assertEqual(validate_payload("provider_evidence", provider, CONTRACT), [])

    def test_provider_and_agent_safety_contracts_are_required(self):
        changed = deepcopy(CONTRACT)
        changed["json_contracts"]["provider_evidence_record"]["required_keys"].remove("provider_id")
        changed["json_contracts"]["agent_output_json"]["no_private_chain_of_thought"] = False
        errors = validate_contract(changed)["errors"]
        self.assertIn("provider proof must require provider_id", errors)
        self.assertIn("agent output contract must exclude private chain of thought and actual approval", errors)

    def test_geography_and_industry_mix_is_complete(self):
        changed = deepcopy(CONTRACT)
        changed["controlled_vocabularies"]["customer_country_target_share_pct"].pop("DE")
        changed["controlled_vocabularies"]["customer_industry_target_share_pct"].pop("retail")
        errors = validate_contract(changed)["errors"]
        self.assertIn("customer country shares must cover supported countries", errors)
        self.assertIn("industry shares must cover the industry vocabulary", errors)


if __name__ == "__main__":
    unittest.main()
