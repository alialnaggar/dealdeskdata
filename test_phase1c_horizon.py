import unittest
from datetime import date
from decimal import Decimal

from phase1c_horizon import (
    classify_unscheduled_build,
    components_waiting_beyond_capacity_horizon,
    has_fresh_capacity_evidence,
)


class CapacityHorizonTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [{
            "product_id": "COMP-A", "location_id": "WH-1",
            "quantity_on_hand": Decimal("2"), "quantity_allocated": Decimal("0"),
            "is_fresh": True,
        }]
        self.receipts = [{
            "product_id": "COMP-A", "location_id": "WH-1",
            "quantity": Decimal("3"), "quantity_allocated": Decimal("0"),
            "expected_date": date(2026, 11, 15),
        }]
        self.required = {"COMP-A": Decimal("5")}
        self.horizon = date(2026, 10, 31)

    def test_shortage_with_confirmed_late_receipt_is_unknown(self):
        self.assertEqual(components_waiting_beyond_capacity_horizon(
            self.required, self.required, self.inventory, self.receipts, "WH-1", self.horizon),
            ["COMP-A"])

    def test_receipt_on_horizon_counts_inside_window(self):
        self.receipts[0]["expected_date"] = self.horizon
        self.assertEqual(components_waiting_beyond_capacity_horizon(
            self.required, self.required, self.inventory, self.receipts, "WH-1", self.horizon), [])

    def test_other_location_receipt_does_not_resolve_this_location(self):
        self.receipts[0]["location_id"] = "WH-2"
        self.assertEqual(components_waiting_beyond_capacity_horizon(
            self.required, self.required, self.inventory, self.receipts, "WH-1", self.horizon), [])

    def test_stale_inventory_does_not_count_as_available(self):
        self.inventory[0]["is_fresh"] = False
        self.assertEqual(components_waiting_beyond_capacity_horizon(
            self.required, self.required, self.inventory, self.receipts, "WH-1", self.horizon),
            ["COMP-A"])

    def test_unscheduled_build_with_late_confirmed_supply_is_unknown(self):
        self.assertEqual(classify_unscheduled_build(True, True, ["COMP-A"]),
                         ("unknown", "confirmed_component_supply_after_capacity_horizon"))

    def test_shortage_inside_complete_horizon_remains_infeasible(self):
        self.assertEqual(classify_unscheduled_build(True, True, []),
                         ("infeasible_without_replenishment", None))

    def test_missing_or_stale_capacity_window_is_unknown(self):
        self.assertEqual(classify_unscheduled_build(True, True, [], False),
                         ("unknown", "production_capacity_evidence_missing_or_stale"))

    def test_capacity_evidence_requires_every_resource_at_one_fresh_location(self):
        rows = [
            {"location_id": "WH-1", "capability_code": "assembly",
             "resource_type": "workforce", "is_fresh": True},
            {"location_id": "WH-1", "capability_code": "assembly",
             "resource_type": "equipment", "is_fresh": True},
        ]
        required = {("assembly", "workforce"), ("assembly", "equipment")}
        self.assertTrue(has_fresh_capacity_evidence(required, rows))
        self.assertFalse(has_fresh_capacity_evidence(required, rows[:1]))
        self.assertFalse(has_fresh_capacity_evidence(required, [dict(row, is_fresh=False) for row in rows]))
        split = [dict(row, location_id=f"WH-{i}") for i, row in enumerate(rows)]
        self.assertFalse(has_fresh_capacity_evidence(required, split))


if __name__ == "__main__":
    unittest.main()
