"""Deterministic selection of one component from each BOM substitute group."""

from collections import defaultdict
from decimal import Decimal, ROUND_CEILING
from datetime import timedelta


def _fresh(row, as_of, hours=24):
    return row["snapshot_at"] <= as_of and as_of - row["snapshot_at"] <= timedelta(hours=hours)


def _binding(receipt, as_of):
    return (
        receipt["status"] == "Confirmed"
        and receipt["confirmed_at"] is not None
        and receipt["confirmed_at"] <= as_of
        and (receipt["valid_until"] is None or receipt["valid_until"] > as_of)
        and (receipt["purchase_order_id"] is not None or receipt.get("evidence_ref"))
        and (
            receipt["purchase_order_id"] is None
            or (
                receipt.get("po_status") == "Confirmed"
                and receipt.get("po_confirmed_at") is not None
                and receipt["po_confirmed_at"] <= as_of
                and receipt.get("destination_location_id") == receipt["location_id"]
            )
        )
    )


def _available_units(component_id, bundle, as_of):
    """Return current selectable units and the contributing evidence IDs."""
    locations = {row["location_id"] for row in bundle["production_capacity"]}
    quantity = Decimal(0)
    evidence = []
    for row in bundle["inventory"]:
        if row["product_id"] != component_id or row["location_id"] not in locations:
            continue
        if _fresh(row, as_of):
            quantity += row["quantity_on_hand"] - row["quantity_allocated"]
            evidence.append(row["inventory_id"])
    for row in bundle["inbound_supply"]:
        if row["product_id"] != component_id or row["location_id"] not in locations:
            continue
        if _binding(row, as_of):
            quantity += row["quantity"] - row["quantity_allocated"]
            evidence.append(row["supply_id"])
    return quantity, sorted(evidence)


def select_bom_components(bom, bom_lines, build_units, bundle, as_of):
    """Select mandatory BOM lines and one deterministic alternative per group.

    `build_units` is theoretical finished output. Availability is used only to
    choose among alternatives; the production scheduler still checks the
    selected component at one location and on each operation date.
    """
    groups = defaultdict(list)
    mandatory = []
    for line in bom_lines:
        if line["bom_id"] != bom["bom_id"]:
            continue
        group = line["substitute_group_code"]
        if group is None:
            mandatory.append(line)
        else:
            groups[group].append(line)

    selected = list(mandatory)
    details = []
    for group_code in sorted(groups):
        candidates = groups[group_code]
        scored = []
        for line in candidates:
            per_unit = (
                line["required_quantity_per_output"]
                / bom["output_quantity"]
                / (Decimal(1) - line["scrap_pct"] / 100)
            )
            required_units = (build_units * per_unit).to_integral_value(rounding=ROUND_CEILING)
            available, evidence = _available_units(line["component_product_id"], bundle, as_of)
            scored.append({
                "line": line,
                "required_units": required_units,
                "available_units": available,
                "evidence_ids": evidence,
                "covers_requirement": available >= required_units,
            })
        chosen = min(
            scored,
            key=lambda item: (
                not item["covers_requirement"],
                item["line"]["priority"],
                item["line"]["component_product_id"],
            ),
        )
        selected.append(chosen["line"])
        details.append({
            "group_code": group_code,
            "selected_bom_line_id": chosen["line"]["bom_line_id"],
            "selected_component_product_id": chosen["line"]["component_product_id"],
            "selection_reason": (
                "lowest_priority_candidate_with_sufficient_selectable_units"
                if chosen["covers_requirement"]
                else "lowest_priority_candidate; no_candidate_has_sufficient_selectable_units"
            ),
            "required_units_for_build": chosen["required_units"],
            "candidates": [
                {
                    "bom_line_id": item["line"]["bom_line_id"],
                    "component_product_id": item["line"]["component_product_id"],
                    "priority": item["line"]["priority"],
                    "available_units": item["available_units"],
                    "covers_requirement": item["covers_requirement"],
                    "evidence_ids": item["evidence_ids"],
                }
                for item in sorted(scored, key=lambda item: (item["line"]["priority"], item["line"]["component_product_id"]))
            ],
        })
    return selected, details
