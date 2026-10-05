"""Helpers for separating a bounded planning window from a true shortage."""

from decimal import Decimal


def components_waiting_beyond_capacity_horizon(
    component_ids,
    required_units,
    inventory_rows,
    binding_receipts,
    location_id,
    horizon_end,
):
    """Return required components short by ``horizon_end`` but due afterward.

    Inventory rows must include a precomputed ``is_fresh`` flag. Receipts are
    expected to have passed the reader's independent binding-evidence checks.
    A returned component makes the outcome unknown; it does not promise that
    production will be feasible after the current capacity window.
    """
    waiting = []
    for component_id in sorted(component_ids):
        needed = Decimal(str(required_units.get(component_id, 0)))
        if needed <= 0:
            continue
        on_hand = sum((
            Decimal(str(row["quantity_on_hand"])) - Decimal(str(row["quantity_allocated"]))
            for row in inventory_rows
            if row["product_id"] == component_id
            and row["location_id"] == location_id
            and row["is_fresh"]
        ), Decimal(0))
        before_or_on_horizon = sum((
            Decimal(str(row["quantity"])) - Decimal(str(row["quantity_allocated"]))
            for row in binding_receipts
            if row["product_id"] == component_id
            and row["location_id"] == location_id
            and row["expected_date"] <= horizon_end
        ), Decimal(0))
        after_horizon = sum((
            Decimal(str(row["quantity"])) - Decimal(str(row["quantity_allocated"]))
            for row in binding_receipts
            if row["product_id"] == component_id
            and row["location_id"] == location_id
            and row["expected_date"] > horizon_end
        ), Decimal(0))
        if on_hand + before_or_on_horizon < needed and after_horizon > 0:
            waiting.append(component_id)
    return waiting


def classify_unscheduled_build(has_material_evidence, has_operation_steps, late_components):
    """Classify a build that did not fit any represented capacity dates."""
    if late_components:
        return "unknown", "confirmed_component_supply_after_capacity_horizon"
    if not has_material_evidence or not has_operation_steps:
        return "unknown", None
    return "infeasible_without_replenishment", None
