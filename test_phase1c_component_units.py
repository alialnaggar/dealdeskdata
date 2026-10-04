"""Check indivisible stock accounting at the shared-demand boundary."""

from decimal import Decimal
import unittest

from phase1c_component_units import whole_component_requirements


class ComponentUnitTests(unittest.TestCase):
    def test_rounds_after_aggregating_same_component_across_builds(self):
        theoretical = {"shared": Decimal("3.2") + Decimal("2.3"), "other": Decimal("6") / Decimal("0.99")}
        self.assertEqual(whole_component_requirements(theoretical),
                         {"shared": Decimal(6), "other": Decimal(7)})

    def test_negative_or_nonfinite_demand_is_rejected(self):
        for value in (Decimal("-0.1"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                whole_component_requirements({"component": value})


if __name__ == "__main__":
    unittest.main()
