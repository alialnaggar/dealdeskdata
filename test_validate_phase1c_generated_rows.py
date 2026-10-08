"""Check typed validation rejects source drift beyond PostgreSQL constraints."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import unittest

import yaml

from validate_phase1c_generated_rows import validate_rows

HERE = Path(__file__).resolve().parent
CONTRACT = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())


def example():
    return {
        "products": [{"product_id": "BUILD-1", "fulfillment_mode": "make_to_order",
                      "attributes_json": {"archetype_code": "workstation", "demand_class": "regular",
                                          "offered_options": ["standard"]},
                      "unit_of_measure": "device", "is_active": True, "is_sellable": True}],
        "suppliers": [{"supplier_id": "SUP-1", "order_calendar_json": {
            "working_weekdays": [1, 2, 3, 4, 5], "holiday_dates": [], "time_zone": "Europe/Amsterdam"}}],
        "inventory": [{"inventory_id": "INV-1", "location_id": "WH-EU-CENTRAL"}],
        "purchase_orders": [], "inbound_supply": [],
        "production_capacity": [{"capacity_id": "CAP-1", "location_id": "WH-EU-CENTRAL",
                                 "time_zone": "Europe/Berlin"}],
        "shipping_lanes": [{"lane_id": "LANE-1", "origin_location_id": "WH-EU-CENTRAL",
                            "origin_time_zone": "Europe/Berlin",
                            "dispatch_weekdays_json": [1, 2, 3, 4, 5]}],
        "compatibility_rules": [{"compatibility_rule_id": "COV-1", "rule_type": "installation_eligibility",
                                 "condition_json": {"country_code": "DE", "region": "DE-NW", "eligible": True}}],
        "bom_headers": [{"finished_product_id": "BUILD-1", "configuration_signature_json":
                         {"selected_options": ["standard"]}, "status": "active"}],
        "deals": [{"deal_id": "DEAL-1", "submitted_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
                   "destination_country_code": "DE", "destination_region": "DE-NW",
                   "terms_json": {"payment_terms_days": 30, "contract_clause_codes": ["standard"],
                                  "allow_partial_delivery": False},
                   "requirements_json": {}, "evidence_refs_json": []}],
        "deal_lines": [{"deal_line_id": "LINE-1", "deal_id": "DEAL-1", "product_id": "BUILD-1",
                        "configuration_json": {"selected_options": ["standard"]}, "quantity": 1,
                        "requested_activation_date": None}],
    }


class GeneratedRowTests(unittest.TestCase):
    def test_connected_typed_rows(self):
        self.assertEqual(validate_rows(example(), CONTRACT)["errors"], [])

    def test_unknown_location_zone_option_and_unresolved_evidence_fail(self):
        rows = example()
        rows["inventory"][0]["location_id"] = "WH-EU-NORTH"
        rows["shipping_lanes"][0]["origin_time_zone"] = "UTC"
        rows["deal_lines"][0]["configuration_json"] = {"selected_options": ["alternate"]}
        rows["deals"][0]["evidence_refs_json"] = [{
            "evidence_ref": "UNTRUSTED-1", "evidence_type": "customer_document",
            "source_class": "synthetic_sales_input", "issued_at": "2026-09-01T01:00:00Z"}]
        errors = validate_rows(rows, CONTRACT)["errors"]
        self.assertTrue(any("unknown location" in error for error in errors))
        self.assertTrue(any("origin_time_zone differs" in error for error in errors))
        self.assertTrue(any("selected option must be one offered code" in error for error in errors))
        self.assertTrue(any("lacks matching independent record" in error for error in errors))

    def test_trusted_reference_must_precede_submission(self):
        rows = example()
        ref = {"evidence_ref": "DOC-1", "evidence_type": "customer_document",
               "source_class": "synthetic_sales_input", "issued_at": "2026-09-02T00:00:00Z"}
        rows["deals"][0]["evidence_refs_json"] = [ref]
        errors = validate_rows(rows, CONTRACT, trusted_deal_evidence={"DOC-1": ref})["errors"]
        self.assertTrue(any("issued after submission" in error for error in errors))

    def test_bad_installation_condition_is_rejected(self):
        rows = example()
        rows["compatibility_rules"][0]["condition_json"] = {
            "country_code": "DE", "region_codes": ["DE-NW"], "eligible": "yes"}
        errors = validate_rows(rows, CONTRACT)["errors"]
        self.assertTrue(any("compatibility condition" in error or "installation condition" in error
                            for error in errors))

    def test_requirements_cannot_carry_an_expected_decision(self):
        rows = example()
        rows["deals"][0]["requirements_json"] = {"expected_decision": "Approved"}
        self.assertTrue(any("requirements contain unknown keys" in error
                            for error in validate_rows(rows, CONTRACT)["errors"]))

    def test_digital_full_term_quantity_is_checked(self):
        rows = example()
        rows["products"][0].update(fulfillment_mode="digital_activation",
                                    unit_of_measure="instance_month",
                                    attributes_json={"archetype_code": "cloud", "demand_class": "regular",
                                                     "edition": "business"})
        rows["bom_headers"] = []
        rows["deals"][0]["terms_json"]["contract_months"] = 12
        rows["deal_lines"][0].update(configuration_json={"edition": "business", "units_per_period": 2},
                                      requested_activation_date="2026-09-03", quantity=12)
        errors = validate_rows(rows, CONTRACT)["errors"]
        self.assertTrue(any("digital full-term quantity/date invalid" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
