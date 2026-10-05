"""Pure tests for deterministic BOM substitute-group selection."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from phase1c_bom_selection import select_bom_components


AS_OF = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)


def component_line(line_id, component, priority, group="POWER"):
    return {
        "bom_id": "BOM-1",
        "bom_line_id": line_id,
        "component_product_id": component,
        "required_quantity_per_output": Decimal("1"),
        "scrap_pct": Decimal("0"),
        "substitute_group_code": group,
        "priority": priority,
        "is_mandatory": True,
    }


def bundle(inventory=(), receipts=()):
    return {
        "production_capacity": [{"location_id": "WH-1"}],
        "inventory": list(inventory),
        "inbound_supply": list(receipts),
    }


def inventory(product, quantity, allocated=0):
    return {
        "inventory_id": f"I-{product}",
        "product_id": product,
        "location_id": "WH-1",
        "quantity_on_hand": Decimal(str(quantity)),
        "quantity_allocated": Decimal(str(allocated)),
        "snapshot_at": AS_OF,
    }


def receipt(product, quantity, allocated=0):
    return {
        "supply_id": f"S-{product}",
        "purchase_order_id": f"PO-{product}",
        "product_id": product,
        "location_id": "WH-1",
        "quantity": Decimal(str(quantity)),
        "quantity_allocated": Decimal(str(allocated)),
        "status": "Confirmed",
        "confirmed_at": AS_OF,
        "valid_until": datetime(2026, 11, 1, tzinfo=timezone.utc),
        "po_status": "Confirmed",
        "po_confirmed_at": AS_OF,
        "destination_location_id": "WH-1",
        "evidence_ref": f"E-{product}",
    }


class BomSelectionTests(unittest.TestCase):
    def test_lowest_priority_candidate_with_stock_wins(self):
        lines = [component_line("L-A", "COMP-A", 1), component_line("L-B", "COMP-B", 2)]
        selected, groups = select_bom_components(
            {"bom_id": "BOM-1", "output_quantity": Decimal("1")},
            lines,
            Decimal("5"),
            bundle(inventory=[inventory("COMP-B", 5)]),
            AS_OF,
        )
        self.assertEqual([row["component_product_id"] for row in selected], ["COMP-B"])
        self.assertEqual(groups[0]["selection_reason"], "lowest_priority_candidate_with_sufficient_selectable_units")
        self.assertEqual(groups[0]["selected_bom_line_id"], "L-B")

    def test_confirmed_inbound_counts_as_selectable_evidence(self):
        lines = [component_line("L-A", "COMP-A", 1), component_line("L-B", "COMP-B", 2)]
        selected, groups = select_bom_components(
            {"bom_id": "BOM-1", "output_quantity": Decimal("1")},
            lines,
            Decimal("5"),
            bundle(receipts=[receipt("COMP-A", 5)]),
            AS_OF,
        )
        self.assertEqual(selected[0]["component_product_id"], "COMP-A")
        self.assertEqual(groups[0]["candidates"][0]["evidence_ids"], ["S-COMP-A"])

    def test_shortage_still_has_deterministic_choice_and_is_visible(self):
        lines = [component_line("L-A", "COMP-A", 1), component_line("L-B", "COMP-B", 2)]
        selected, groups = select_bom_components(
            {"bom_id": "BOM-1", "output_quantity": Decimal("1")},
            lines,
            Decimal("5"),
            bundle(inventory=[inventory("COMP-B", 2)]),
            AS_OF,
        )
        self.assertEqual(selected[0]["component_product_id"], "COMP-A")
        self.assertEqual(groups[0]["selection_reason"], "lowest_priority_candidate; no_candidate_has_sufficient_selectable_units")
        self.assertFalse(any(candidate["covers_requirement"] for candidate in groups[0]["candidates"]))


if __name__ == "__main__":
    unittest.main()
