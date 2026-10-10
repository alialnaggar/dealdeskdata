"""Protect monthly versus annual billing and canonical provider identity."""

import unittest

from phase1c_digital_units import digital_demand, digital_signature


class DigitalUnitTests(unittest.TestCase):
    def test_monthly_instance_and_storage_demand(self):
        self.assertEqual(digital_demand("instance_month", 12, 5), (True, 60, "instance"))
        self.assertEqual(digital_demand("protected_tb_month", 12, 5), (True, 60, "protected_tb"))

    def test_annual_licence_concurrent_demand(self):
        self.assertEqual(digital_demand("licence_year", 24, 5), (True, 10, "licence"))
        self.assertEqual(digital_demand("licence_year", 18, 5), (False, None, None))
        self.assertEqual(digital_demand("device_year", 12, 5), (True, 5, "licence"))

    def test_unknown_or_malformed_unit_does_not_validate(self):
        self.assertEqual(digital_demand("service_month", 12, 5), (False, None, None))
        self.assertEqual(digital_demand("instance_month", True, 5), (False, None, None))

    def test_pool_signature_ignores_catalogue_attributes_and_quantity(self):
        attrs = {"edition": "business", "category": "cloud_services_and_subscriptions",
                 "archetype_code": "IAAS_COMPUTE", "demand_class": "regular"}
        config = {"edition": "business", "units_per_period": 5}
        self.assertEqual(digital_signature(attrs, config), {"edition": "business"})


if __name__ == "__main__":
    unittest.main()
