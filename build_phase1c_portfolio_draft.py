"""Produce a deterministic structural portfolio proposal for review.

This is a catalogue/BOM projection, not SQL data, price calibration, or a
production generator. The allocation choices below are explicit assumptions.
"""

from collections import Counter
from pathlib import Path
import argparse
import json

import yaml

from validate_phase1c_bom_portfolio import validate_portfolio


HERE = Path(__file__).resolve().parent
MTO_BY_SUBCATEGORY = {
    "workstation": 2,
    "rack_server": 4,
    "tower_server": 3,
    "edge_compact_server": 2,
    "gpu_accelerated_server": 1,
    "storage_array": 3,
    "nas_file_storage": 2,
    "backup_appliance": 1,
}
STOCKED_SUBCATEGORIES = {"business_laptop", "monitor", "dock_peripheral", "enterprise_drive"}
SUBSCRIPTION_SUBCATEGORIES = {
    "network_controller_management", "endpoint_xdr", "identity_access",
    "email_cloud_security", "siem_vulnerability_management",
}
COMPONENT_POOL_SIZES = {
    "compute": {"workstation": 3, "server": 6, "storage_system": 3},
    "storage": {"workstation": 2, "server": 4, "storage_system": 3},
    "network_and_power": {"workstation": 2, "server": 4, "storage_system": 3},
    "chassis_and_other": {"workstation": 1, "server": 3, "storage_system": 2},
}
REUSED_POOL_SIZES = {
    "compute": {"workstation": 1, "server": 3, "storage_system": 1},
    "storage": {"workstation": 1, "server": 2, "storage_system": 1},
    "network_and_power": {"workstation": 1, "server": 2, "storage_system": 1},
    "chassis_and_other": {"workstation": 1, "server": 2, "storage_system": 1},
}
COMPONENT_ROLES = {
    "compute": ("compute_kit", 1, 0),
    "storage": ("storage_drive", 2, 1),
    "network_and_power": ("network_power_kit", 1, 0),
    "chassis_and_other": ("enclosure_kit", 1, 0),
}
AS_OF = "2026-10-06T12:00:00Z"


def build(config):
    catalogue = config["product_catalogue"]["metadata"]["catalogue_version"]
    params = config["fulfillment_production_calibration"]["proposed_parameters"]
    products, mto_ids = [], []
    platform_by_product = {}
    for category, settings in config["product_catalogue"]["categories"].items():
        ordinal = 0
        for subcategory, count in settings["subcategories"].items():
            for local_index in range(count):
                ordinal += 1
                mto = local_index < MTO_BY_SUBCATEGORY.get(subcategory, 0)
                product_type = ("physical" if mto else
                                "subscription" if subcategory in SUBSCRIPTION_SUBCATEGORIES else
                                settings["product_type_mix"][0])
                mode = ("make_to_order" if mto else
                        "stocked_finished" if subcategory in STOCKED_SUBCATEGORIES else
                        "supplier_finished" if product_type == "physical" else
                        "scheduled_service" if product_type == "service" else
                        "digital_activation")
                pid = f"SELL-{category.upper()}-{ordinal:03d}"
                attributes = {"archetype_code": subcategory.upper(),
                              "demand_class": "regular", "category": category,
                              "subcategory": subcategory}
                if mto:
                    platform = ("workstation" if subcategory == "workstation" else
                                "storage_system" if category == "storage_and_data_protection" else
                                "server")
                    attributes.update({"build_platform": platform,
                                       "offered_options": ["standard", "alternate"]
                                       if len(mto_ids) < 6 else ["standard"]})
                    platform_by_product[pid] = platform
                elif mode == "digital_activation":
                    attributes["edition"] = "business"
                elif mode == "scheduled_service":
                    attributes["service_code"] = "standard"
                products.append({"product_id": pid, "catalog_version": catalogue,
                                 "is_sellable": True, "product_type": product_type,
                                 "fulfillment_mode": mode,
                                 "attributes_json": attributes})
                if mto:
                    mto_ids.append(pid)

    component_ids = []
    components_by_platform = {platform: {} for platform in ("workstation", "server", "storage_system")}
    for family, count in params["component_catalogue"]["family_counts"].items():
        sizes = COMPONENT_POOL_SIZES[family]
        assert sum(sizes.values()) == count
        for platform in components_by_platform:
            components_by_platform[platform][family] = []
        for ordinal in range(1, count + 1):
            pid = f"COMP-{family.upper()}-{ordinal:03d}"
            component_ids.append(pid)
            remaining = ordinal
            for platform, size in sizes.items():
                if remaining <= size:
                    break
                remaining -= size
            components_by_platform[platform][family].append(pid)
            products.append({"product_id": pid, "catalog_version": catalogue,
                             "is_sellable": False, "product_type": "component",
                             "fulfillment_mode": "component",
                             "attributes_json": {"archetype_code": f"COMP-{family.upper()}",
                                                 "demand_class": "regular", "component_family": family,
                                                 "component_role": COMPONENT_ROLES[family][0],
                                                 "supported_platforms": [platform]}})

    # Two workstations and four rack servers have two explicitly offered
    # variants at one catalogue price; the remaining twelve have one. Eighteen of the
    # 36 parts recur in BOMs. Component assignments are structural placeholders.
    variants = [(pid, variant) for index, pid in enumerate(mto_ids)
                for variant in (["standard", "alternate"] if index < 6 else ["standard"])]
    assert len(variants) == 24 and len(component_ids) == 36
    counts = Counter(platform_by_product[pid] for pid, _ in variants)
    component_slots = {platform: {} for platform in components_by_platform}
    for platform, families in components_by_platform.items():
        for family, ids in families.items():
            repeatable = ids[:REUSED_POOL_SIZES[family][platform]]
            component_slots[platform][family] = ids + [repeatable[i % len(repeatable)]
                                                       for i in range(counts[platform] - len(ids))]
    offered, headers, lines, requirements = [], [], [], []
    platform_index = {platform: 0 for platform in components_by_platform}
    for index, (pid, variant) in enumerate(variants):
        platform = platform_by_product[pid]
        current_index = platform_index[platform]
        platform_index[platform] += 1
        signature = {"selected_options": [variant]}
        bid = f"BOM-{index + 1:03d}"
        offered.append({"product_id": pid, "configuration_signature_json": signature})
        headers.append({"bom_id": bid, "finished_product_id": pid,
                        "catalog_version": catalogue, "configuration_signature_json": signature,
                        "output_quantity": 1, "effective_from": "2026-01-01T00:00:00Z",
                        "effective_to": None, "status": "active"})
        for slot, (family, ids) in enumerate(component_slots[platform].items(), start=1):
            cid = ids[current_index]
            _, quantity, scrap = COMPONENT_ROLES[family]
            lines.append({"bom_line_id": f"{bid}-{slot}", "bom_id": bid,
                          "component_product_id": cid, "required_quantity_per_output": quantity,
                          "scrap_pct": scrap,
                          "substitute_group_code": "NETWORK_OPTION" if index == 0 and
                          family == "network_and_power" else None,
                          "priority": 0,
                          "is_mandatory": True})
        if index == 0:
            # Exactly one network/power part is selected. The second candidate
            # illustrates supplier or inventory substitution, not extra demand.
            lines.append({"bom_line_id": f"{bid}-NETWORK-ALT", "bom_id": bid,
                          "component_product_id": components_by_platform[platform]["network_and_power"][1],
                          "required_quantity_per_output": 1, "scrap_pct": 0,
                          "substitute_group_code": "NETWORK_OPTION", "priority": 1,
                          "is_mandatory": True})
        for seq, capability, resource in ((1, "assembly", "workforce"),
                                          (2, "test", "equipment")):
            requirements.append({"requirement_id": f"{bid}-{seq}", "bom_id": bid,
                                 "operation_seq": seq, "capability_code": capability,
                                 "resource_type": resource, "setup_hours": 0.5,
                                 "hours_per_unit": 0.5, "batch_size": 4, "status": "active"})
    assert Counter(p["attributes_json"]["category"] for p in products if p["is_sellable"]) == {
        category: row["count"] for category, row in config["product_catalogue"]["categories"].items()
    }
    return {"catalog_version": catalogue, "as_of_at": AS_OF, "products": products,
            "offered_configurations": offered, "bom_headers": headers,
            "bom_lines": lines, "production_requirements": requirements}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "phase1c_portfolio_draft.json")
    args = parser.parse_args()
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text(encoding="utf-8"))
    draft = build(config)
    result = validate_portfolio(draft, config, contract)
    if result["errors"]:
        raise SystemExit(json.dumps(result, indent=2))
    args.output.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
