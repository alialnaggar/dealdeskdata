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
SHARED_COMPONENTS_BY_FAMILY = {
    "compute": 5, "storage": 4, "network_and_power": 4, "chassis_and_other": 3,
}
AS_OF = "2026-10-06T12:00:00Z"


def build(config):
    catalogue = config["product_catalogue"]["metadata"]["catalogue_version"]
    params = config["fulfillment_production_calibration"]["proposed_parameters"]
    products, mto_ids = [], []
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
                products.append({"product_id": pid, "catalog_version": catalogue,
                                 "is_sellable": True, "product_type": product_type,
                                 "fulfillment_mode": mode,
                                 "attributes_json": {"category": category, "subcategory": subcategory}})
                if mto:
                    mto_ids.append(pid)

    component_ids = []
    components_by_family = {}
    for family, count in params["component_catalogue"]["family_counts"].items():
        components_by_family[family] = []
        for ordinal in range(1, count + 1):
            pid = f"COMP-{family.upper()}-{ordinal:03d}"
            component_ids.append(pid)
            components_by_family[family].append(pid)
            products.append({"product_id": pid, "catalog_version": catalogue,
                             "is_sellable": False, "product_type": "component",
                             "fulfillment_mode": "component",
                             "attributes_json": {"component_family": family}})

    # Two workstations and four rack servers have two explicitly offered
    # variants; the remaining twelve assembled SKUs have one. Sixteen of the
    # 36 parts recur in BOMs. Component assignments are structural placeholders.
    variants = [(pid, variant) for index, pid in enumerate(mto_ids)
                for variant in (["standard", "enhanced"] if index < 6 else ["standard"])]
    assert len(variants) == 24 and len(component_ids) == 36
    component_slots = {}
    for family, ids in components_by_family.items():
        repeatable = ids[:SHARED_COMPONENTS_BY_FAMILY[family]]
        component_slots[family] = ids + [repeatable[i % len(repeatable)]
                                         for i in range(len(variants) - len(ids))]
    offered, headers, lines, requirements = [], [], [], []
    for index, (pid, variant) in enumerate(variants):
        signature = {"selected_options": [variant]}
        bid = f"BOM-{index + 1:03d}"
        offered.append({"product_id": pid, "configuration_signature_json": signature})
        headers.append({"bom_id": bid, "finished_product_id": pid,
                        "catalog_version": catalogue, "configuration_signature_json": signature,
                        "output_quantity": 1, "effective_from": "2026-01-01T00:00:00Z",
                        "effective_to": None, "status": "active"})
        for slot, (family, ids) in enumerate(component_slots.items(), start=1):
            cid = ids[index]
            lines.append({"bom_line_id": f"{bid}-{slot}", "bom_id": bid,
                          "component_product_id": cid, "required_quantity_per_output": 2,
                          "scrap_pct": 1, "substitute_group_code": None, "priority": 0,
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
