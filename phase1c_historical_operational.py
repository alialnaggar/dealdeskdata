"""Validate the complete operational view available at a historical cutoff.

The current operational tables and undated shipping lanes cannot be used as
fallback for a historical run. Every record must belong to the registered
snapshot and be known by that run's as-of instant.
"""

from datetime import date, datetime
from decimal import Decimal


TABLES = ("inventory", "inbound_supply", "supplier_offers", "production_capacity",
          "digital_capacity", "shipping_lanes")
REQUIRED = {
    "inventory": ("inventory_id", "product_id", "location_id", "quantity_on_hand",
                  "quantity_allocated", "snapshot_at"),
    "inbound_supply": ("supply_id", "product_id", "location_id", "quantity",
                       "quantity_allocated", "expected_date", "status", "confirmed_at",
                       "valid_until", "purchase_order_id", "evidence_ref", "observed_at"),
    "supplier_offers": ("supplier_item_id", "product_id", "is_active", "valid_from",
                        "valid_to", "lead_days_mode", "verified_at"),
    "production_capacity": ("capacity_id", "location_id", "capability_code", "resource_type",
                            "capacity_date", "available_capacity_hours", "allocated_capacity_hours",
                            "snapshot_at", "status", "evidence_ref", "time_zone"),
    "digital_capacity": ("digital_capacity_id", "product_id", "configuration_signature_json",
                         "provider_id", "region_code", "term_code", "capacity_unit", "capacity_total",
                         "quantity_allocated", "activation_lead_days", "commitment_status",
                         "confirmed_at", "valid_until", "snapshot_at", "evidence_ref"),
    "shipping_lanes": ("lane_id", "origin_location_id", "origin_time_zone",
                       "destination_country_code", "destination_region", "shipping_service_code",
                       "transit_workdays", "dispatch_weekdays_json", "cutoff_local_time",
                       "is_active", "verified_at", "effective_from", "expires_at"),
}


def _instant(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("operational timestamp missing")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("operational timestamp requires timezone")
    return parsed


def _date(value):
    return value if isinstance(value, date) and not isinstance(value, datetime) else date.fromisoformat(value)


def select_historical_operational(manifest, run):
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or
            manifest.get("snapshot_id") != run["data_snapshot_ref"] or
            manifest.get("complete") is not True or
            _instant(manifest.get("as_of_at")) != run["as_of_at"]):
        raise ValueError("missing or incomplete historical operational snapshot")
    as_of = run["as_of_at"]
    proofs = manifest.get("inbound_evidence")
    if not isinstance(proofs, list):
        raise ValueError("historical operational snapshot missing inbound evidence registry")
    by_ref = {}
    for proof in proofs:
        if not isinstance(proof, dict) or not proof.get("evidence_ref") or proof["evidence_ref"] in by_ref:
            raise ValueError("duplicate or malformed inbound evidence")
        if _instant(proof["issued_at"]) > as_of:
            raise ValueError("future inbound evidence")
        by_ref[proof["evidence_ref"]] = proof
    result = {}
    for table in TABLES:
        rows = manifest.get(table)
        if not isinstance(rows, list):
            raise ValueError(f"historical operational snapshot missing {table}")
        result[table] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{table} record must be an object")
            value = dict(row)
            if any(key not in value for key in REQUIRED[table]):
                raise ValueError(f"{table} record missing required fields")
            for field in ("snapshot_at", "confirmed_at", "valid_until", "ordered_at",
                          "po_confirmed_at", "observed_at", "verified_at"):
                if value.get(field) is not None:
                    value[field] = _instant(value[field])
            for field in ("expected_date", "capacity_date", "valid_from", "valid_to"):
                if value.get(field) is not None:
                    value[field] = _date(value[field])
            if table == "shipping_lanes":
                for field in ("effective_from", "expires_at"):
                    value[field] = _instant(value.get(field))
                if (not value.get("verified_at") or value["verified_at"] > as_of or value["effective_from"] > as_of or
                        value["expires_at"] <= as_of):
                    raise ValueError("shipping lane is not proven at historical cutoff")
                value["cutoff_local_time"] = datetime.strptime(value["cutoff_local_time"], "%H:%M:%S").time()
            elif table == "supplier_offers":
                if (value.get("valid_from") is None or value["valid_from"] > as_of.date()
                        or not value.get("verified_at") or value["verified_at"] > as_of):
                    raise ValueError("supplier offer is future at historical cutoff")
            elif table == "inbound_supply":
                if not value.get("observed_at") or value["observed_at"] > as_of:
                    raise ValueError("inbound record is future or missing")
                if value.get("status") == "Confirmed" and value.get("purchase_order_id") is None:
                    proof = by_ref.get(value.get("evidence_ref"))
                    if (not proof or proof.get("source_class") != "synthetic_supplier_manifest" or
                            any(str(proof.get(key)) != str(value.get(key)) for key in
                                ("product_id", "location_id", "quantity", "expected_date")) or
                            _instant(proof["valid_until"]) <= as_of or
                            not value.get("confirmed_at") or value["confirmed_at"] > as_of):
                        raise ValueError("no-PO confirmed inbound lacks matching independent proof")
            elif value.get("snapshot_at") is None or value["snapshot_at"] > as_of:
                raise ValueError(f"{table} snapshot is future or missing")
            if value.get("confirmed_at") and value["confirmed_at"] > as_of:
                raise ValueError(f"{table} confirmation is future")
            if value.get("po_confirmed_at") and value["po_confirmed_at"] > as_of:
                raise ValueError("purchase order confirmation is future")
            for key in ("quantity_on_hand", "quantity_allocated", "quantity", "minimum_order_qty",
                        "order_multiple", "unit_cost", "available_capacity_hours", "allocated_capacity_hours",
                        "capacity_total"):
                if key in value:
                    value[key] = Decimal(str(value[key]))
            result[table].append(value)
    return result
