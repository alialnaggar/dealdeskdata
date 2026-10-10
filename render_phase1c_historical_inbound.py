"""Deterministic dated supplier receipts, independent of historical deals."""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random

import yaml

HERE = Path(__file__).resolve().parent
PREFIX = "phase1c_historical_inbound_source_"
INDEX = "phase1c_historical_inbound_index.json"


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def build(portfolio, config, credit_index):
    snapshots = credit_index["snapshots"]
    if len(snapshots) != 400:
        raise ValueError("historical cutoff registry drift")
    products = sorted((p for p in portfolio["products"] if p["fulfillment_mode"] in
                       ("component", "supplier_finished")), key=lambda p: p["product_id"])
    if len(products) != 63:
        raise ValueError("inbound product coverage drift")
    rng = random.Random(config["random_seed"] + 1400)
    # Keep independent supplier observations in step with the configured
    # seven-day confirmation evidence recheck, rather than leaving a monthly
    # gap behind each short-lived confirmation.
    first_observation = date(2026, 2, 20)
    last_observation = date(2026, 8, 31)
    observations = [first_observation + timedelta(days=7 * n)
                    for n in range((last_observation - first_observation).days // 7 + 1)]
    count = len(products) * len(observations)
    targets = config["commercial_supply"]["availability"]["inbound_status_target_share"]
    counts = {status: round(count * share) for status, share in targets.items()}
    counts["Confirmed"] += count - sum(counts.values())
    statuses = [status for status, amount in counts.items() for _ in range(amount)]
    rng.shuffle(statuses)
    locations = config["commercial_supply"]["availability"]["inventory_locations"]
    events = []
    for observation_index, observation_day in enumerate(observations):
        for product_index, product in enumerate(products):
            sequence = observation_index * len(products) + product_index
            status = statuses[sequence]
            observed = datetime.combine(observation_day, time(8), timezone.utc)
            expected = (observed + timedelta(days=rng.randint(3, 12))).date()
            valid_until = observed + timedelta(days=9)
            location = locations[product_index % len(locations)]
            quantity = rng.randint(5, 35)
            no_po = status == "Confirmed" and sequence % 4 == 0
            po_id = None if no_po else f"HIST-PO-{sequence+1:04d}"
            confirmation = (observed - timedelta(hours=1)).isoformat() if status == "Confirmed" else None
            proof_ref = f"HIST-SUP-PROOF-{sequence+1:04d}" if no_po else f"HIST-PO-EVIDENCE-{sequence+1:04d}"
            po_status = "Confirmed" if status == "Confirmed" else {
                "Planned": "Placed", "Delayed": "Delayed", "Cancelled": "Cancelled"}[status]
            events.append({"supply_id": f"HIST-RECEIPT-{sequence+1:04d}",
                "purchase_order_id": po_id, "product_id": product["product_id"],
                "location_id": location, "destination_location_id": location if po_id else None,
                "quantity": quantity, "quantity_allocated": rng.randint(0, quantity // 4),
                "expected_date": expected.isoformat(), "status": status,
                "confirmed_at": confirmation, "observed_at": observed.isoformat(),
                "valid_until": valid_until.isoformat() if status == "Confirmed" else None,
                "evidence_ref": proof_ref, "po_status": po_status if po_id else None,
                "po_confirmed_at": confirmation if po_id else None,
                "purchase_order_evidence": ({"purchase_order_id": po_id,
                    "status": po_status, "confirmed_at": confirmation,
                    "issued_at": (observed - timedelta(hours=2)).isoformat(),
                    "destination_location_id": location} if po_id else None),
                "inbound_evidence": ({"evidence_ref": proof_ref,
                    "source_class": "synthetic_supplier_manifest",
                    "product_id": product["product_id"], "location_id": location,
                    "quantity": quantity, "expected_date": expected.isoformat(),
                    "issued_at": (observed - timedelta(hours=2)).isoformat(),
                    "confirmed_at": confirmation, "valid_until": valid_until.isoformat()}
                    if no_po else None)})
    shard_size = (len(events) + 3) // 4
    files = {f"{PREFIX}{n+1:02d}.json": encode({"schema_version": 1,
        "provenance": "synthetic_provisional_supplier_receipts",
        "events": events[n*shard_size:(n+1)*shard_size]}) for n in range(4)}
    index = {"schema_version": 1, "provenance": "synthetic_provisional_inbound_source",
             "source_sha256": {name: hashlib.sha256(content.encode()).hexdigest()
                               for name, content in files.items()}, "snapshots": snapshots}
    return files, index


def load_resolver(base_dir=HERE):
    index = json.loads((base_dir / INDEX).read_text())
    credit = json.loads((base_dir / "phase1c_historical_credit_index.json").read_text())
    if index.get("schema_version") != 1 or index.get("snapshots") != credit.get("snapshots"):
        raise ValueError("inbound and credit cutoff registries differ")
    events = []
    for name, digest in index["source_sha256"].items():
        raw = (base_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"historical inbound source digest mismatch: {name}")
        payload = json.loads(raw)
        if payload.get("schema_version") != 1:
            raise ValueError("historical inbound source schema drift")
        events.extend(payload["events"])
    if len(events) != 1764 or len({x["supply_id"] for x in events}) != 1764:
        raise ValueError("incomplete historical inbound source")
    lookup = {entry["snapshot_id"]: entry for entry in index["snapshots"]}

    def resolve(snapshot_id):
        if snapshot_id not in lookup:
            raise ValueError("unregistered historical inbound cutoff")
        as_of = datetime.fromisoformat(lookup[snapshot_id]["as_of_at"])
        visible = [event for event in events if datetime.fromisoformat(event["observed_at"]) <= as_of]
        # Expired confirmations are retained as dated history but cannot bind.
        return {"inbound_supply": [{key: value for key, value in event.items()
                 if key not in ("purchase_order_evidence", "inbound_evidence")}
                 for event in visible],
                "purchase_order_evidence": [event["purchase_order_evidence"] for event in visible
                     if event["purchase_order_evidence"]],
                "inbound_evidence": [event["inbound_evidence"] for event in visible
                     if event["inbound_evidence"]]}
    return resolve


def main():
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
    files, index = build(portfolio, config, credit)
    for name, content in files.items():
        (HERE / name).write_text(content)
    (HERE / INDEX).write_text(encode(index))
    print(f"Wrote {sum(len(json.loads(content)['events']) for content in files.values())} independent inbound events")


if __name__ == "__main__":
    main()
