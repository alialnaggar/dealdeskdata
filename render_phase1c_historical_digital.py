"""Dated synthetic digital pools and separate full-term provider proof."""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random

import yaml

HERE = Path(__file__).resolve().parent
POOL_SOURCE = "phase1c_historical_digital_pool_source.json"
PROOF_PREFIX = "phase1c_historical_digital_proof_"
INDEX = "phase1c_historical_digital_index.json"
START = date(2026, 2, 28)
END = date(2026, 8, 31)
DAYS = (END - START).days + 1
EPOCH_DAYS = 6
COUNTRIES = ("DE", "FR", "NL", "BE", "AT")
STATUSES = ("binding", "provisional", "unknown")


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _unit(product):
    attrs = product["attributes_json"]
    if attrs["subcategory"] == "cloud_storage_backup":
        return "protected_tb"
    if attrs["category"] == "cloud_services_and_subscriptions":
        return "instance"
    return "licence"


def _signature(product):
    attrs = product["attributes_json"]
    return {key: attrs[key] for key in ("edition", "service_tier", "feature_codes")
            if key in attrs}


def build(portfolio, config, credit_index):
    snapshots = credit_index["snapshots"]
    if len(snapshots) != 400:
        raise ValueError("historical cutoff registry drift")
    digital = sorted((p for p in portfolio["products"]
                      if p["fulfillment_mode"] == "digital_activation"),
                     key=lambda p: p["product_id"])
    if len(digital) != 41:
        raise ValueError("digital catalogue coverage drift")
    covered = digital[:36]  # 36/41 exceeds the provisional 85% exact-pool target.
    parameters = config["fulfillment_production_calibration"]["proposed_parameters"]["digital_capacity"]
    rng = random.Random(config["random_seed"] + 1600)
    epochs = (DAYS + EPOCH_DAYS - 1) // EPOCH_DAYS
    total_events = len(covered) * len(COUNTRIES) * epochs
    targets = parameters["generated_commitment_status_pct"]
    counts = {status: round(total_events * targets[status] / 100) for status in STATUSES}
    counts["binding"] += total_events - sum(counts.values())
    statuses = [status for status in STATUSES for _ in range(counts[status])]
    rng.shuffle(statuses)
    cursor = 0
    pools = []
    proofs = {country: [] for country in COUNTRIES}
    for product in covered:
        unit = _unit(product)
        band = (parameters["user_and_licence_concurrent_total"] if unit == "licence"
                else parameters["instance_concurrent_total"])
        for country in COUNTRIES:
            events = []
            identity = f"{product['product_id']}-{country}"
            for epoch in range(epochs):
                start_day = START + timedelta(days=epoch * EPOCH_DAYS)
                observed = datetime.combine(start_day, time(8), timezone.utc)
                status = statuses[cursor]
                cursor += 1
                total = rng.choice(band)
                allocated = round(total * rng.triangular(
                    parameters["allocated_to_total_ratio"][0],
                    parameters["allocated_to_total_ratio"][2],
                    parameters["allocated_to_total_ratio"][1]), 3)
                lead = rng.choice(parameters["activation_lead_workdays"])
                ref = f"HIST-DIGITAL-PROOF-{identity}-{epoch:02d}" if status == "binding" else None
                events.append([status, total, allocated, lead, ref])
                if ref:
                    covers_until = start_day + timedelta(days=550)
                    confirmed = observed - timedelta(hours=1)
                    proofs[country].append({
                        "evidence_ref": ref, "evidence_type": "provider_proof",
                        "source_class": "synthetic_provider_manifest",
                        "issued_at": observed.isoformat(), "confirmed_at": confirmed.isoformat(),
                        "verified_at": observed.isoformat(),
                        "valid_until": datetime.combine(
                            covers_until + timedelta(days=1), time(0), timezone.utc).isoformat(),
                        "product_id": product["product_id"], "provider_id": "HIST-PROVIDER-01",
                        "configuration_signature_json": _signature(product),
                        "region_code": country, "term_code": "12m", "capacity_unit": unit,
                        "capacity_total": total, "quantity_allocated": allocated,
                        "commitment_status": "binding",
                        "covers_from": start_day.isoformat(),
                        "covers_until": covers_until.isoformat()})
            pools.append({"product_id": product["product_id"], "region_code": country,
                          "configuration_signature_json": _signature(product),
                          "capacity_unit": unit, "events": events})
    source = encode({"schema_version": 1, "provenance": "synthetic_provisional_daily_digital_pools",
                     "start_date": START.isoformat(), "end_date": END.isoformat(),
                     "observation_time_utc": "08:00:00", "epoch_days": EPOCH_DAYS,
                     "provider_id": "HIST-PROVIDER-01", "pools": pools})
    files = {POOL_SOURCE: source}
    for country, records in proofs.items():
        files[f"{PROOF_PREFIX}{country}.json"] = encode({
            "schema_version": 1, "provenance": "independent_synthetic_provider_proof",
            "records": records})
    index = {"schema_version": 1, "provenance": "synthetic_provisional_digital_source",
             "source_sha256": {name: hashlib.sha256(content.encode()).hexdigest()
                               for name, content in files.items()},
             "snapshots": snapshots}
    return files, index


def load_resolver(base_dir=HERE):
    index = json.loads((base_dir / INDEX).read_text())
    credit = json.loads((base_dir / "phase1c_historical_credit_index.json").read_text())
    if index.get("schema_version") != 1 or index.get("snapshots") != credit.get("snapshots"):
        raise ValueError("digital cutoff registry drift")
    source = None
    proofs = {}
    for name, digest in index["source_sha256"].items():
        raw = (base_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"historical digital source digest mismatch: {name}")
        data = json.loads(raw)
        if data.get("schema_version") != 1:
            raise ValueError("historical digital source schema drift")
        if name == POOL_SOURCE:
            source = data
        else:
            for proof in data["records"]:
                ref = proof["evidence_ref"]
                if ref in proofs:
                    raise ValueError("duplicate historical provider proof")
                proofs[ref] = proof
    if (source is None or source.get("start_date") != START.isoformat()
            or source.get("end_date") != END.isoformat() or source.get("epoch_days") != EPOCH_DAYS
            or len(source.get("pools", [])) != 36 * len(COUNTRIES)):
        raise ValueError("incomplete historical digital pool source")
    lookup = {entry["snapshot_id"]: entry for entry in index["snapshots"]}

    def resolve(snapshot_id):
        if snapshot_id not in lookup:
            raise ValueError("unregistered digital cutoff")
        as_of = datetime.fromisoformat(lookup[snapshot_id]["as_of_at"])
        observed_day = as_of.date() if as_of.time() >= time(8) else as_of.date() - timedelta(days=1)
        offset = (observed_day - START).days
        if not 0 <= offset < DAYS:
            raise ValueError("digital source outside dated range")
        observed = datetime.combine(observed_day, time(8), timezone.utc)
        epoch = offset // EPOCH_DAYS
        rows, visible_proofs = [], []
        for pool in source["pools"]:
            if len(pool["events"]) != (DAYS + EPOCH_DAYS - 1) // EPOCH_DAYS:
                raise ValueError("incomplete historical digital epochs")
            status, total, allocated, lead, ref = pool["events"][epoch]
            if (status not in STATUSES or total < 0 or not 0 <= allocated <= total
                    or (status == "binding") != bool(ref)):
                raise ValueError("malformed historical digital event")
            proof = proofs.get(ref) if ref else None
            if ref:
                if not proof or datetime.fromisoformat(proof["issued_at"]) > as_of:
                    raise ValueError("missing or future independent provider proof")
                visible_proofs.append(proof)
            rows.append({
                "digital_capacity_id": f"HIST-DIGITAL-{pool['product_id']}-{pool['region_code']}-{observed_day}",
                "product_id": pool["product_id"],
                "configuration_signature_json": pool["configuration_signature_json"],
                "provider_id": source["provider_id"], "region_code": pool["region_code"],
                "term_code": "12m", "capacity_unit": pool["capacity_unit"],
                "capacity_total": total, "quantity_allocated": allocated,
                "activation_lead_days": lead, "commitment_status": status,
                "confirmed_at": proof["confirmed_at"] if proof else None,
                "valid_until": proof["valid_until"] if proof else None,
                "snapshot_at": observed.isoformat(), "evidence_ref": ref})
        return {"digital_capacity": rows, "provider_evidence": visible_proofs}
    return resolve


def load_provider_resolver(snapshot_id, base_dir=HERE, *, resolver=None):
    """Supply the reader with proof visible at one registered cutoff only."""
    view = (resolver or load_resolver(base_dir))(snapshot_id)
    records = {}
    for raw in view["provider_evidence"]:
        record = dict(raw)
        for key in ("issued_at", "confirmed_at", "verified_at", "valid_until"):
            record[key] = datetime.fromisoformat(record[key])
        for key in ("covers_from", "covers_until"):
            record[key] = date.fromisoformat(record[key])
        for key in ("capacity_total", "quantity_allocated"):
            record[key] = Decimal(str(record[key]))
        records[record["evidence_ref"]] = record
    return records.get


def main():
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
    files, index = build(portfolio, config, credit)
    for name, content in files.items():
        (HERE / name).write_text(content)
    (HERE / INDEX).write_text(encode(index))
    resolver = load_resolver()
    for entry in index["snapshots"]:
        resolver(entry["snapshot_id"])
    print(f"Validated {len(index['snapshots'])} dated digital pool/proof views")


if __name__ == "__main__":
    main()
