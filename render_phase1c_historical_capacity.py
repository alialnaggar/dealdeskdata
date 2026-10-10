"""Dated, provisional workshop capacity independent of historical deal inputs."""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = "phase1c_historical_capacity_source.json"
INDEX = "phase1c_historical_capacity_index.json"
START = date(2026, 2, 28)
END = date(2026, 9, 30)
CAPABILITIES = ("assembly", "configuration", "test")
RESOURCES = ("equipment", "workforce")


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def build(config, credit_index):
    snapshots = credit_index["snapshots"]
    if len(snapshots) != 400:
        raise ValueError("historical cutoff registry drift")
    parameters = config["fulfillment_production_calibration"]["proposed_parameters"]["production_capacity"]
    rng = random.Random(config["random_seed"] + 1500)
    rows = []
    day = START
    while day <= END:
        working = day.isoweekday() <= 5
        for capability in CAPABILITIES:
            for resource in RESOURCES:
                band = parameters[f"{resource}_daily_available_hours"]
                available = rng.choice(band) if working else 0
                if working and rng.random() < parameters["downtime_working_capability_day_share"]:
                    low, mode, high = parameters["downtime_reduction_fraction"]
                    available *= 1 - rng.triangular(low, high, mode)
                low, mode, high = parameters["existing_allocation_to_available_ratio"]
                allocated = round(available * rng.triangular(low, high, mode), 2)
                rows.append([day.isoformat(), capability, resource,
                             round(available, 2), allocated])
        day += timedelta(days=1)
    source = encode({"schema_version": 1,
                     "provenance": "synthetic_provisional_workshop_capacity",
                     "location_id": parameters["workshop_location"],
                     "time_zone": "Europe/Berlin", "rows": rows})
    index = {"schema_version": 1, "provenance": "synthetic_provisional_capacity_source",
             "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
             "snapshots": snapshots}
    return source, index


def load_resolver(base_dir=HERE):
    index = json.loads((base_dir / INDEX).read_text())
    credit = json.loads((base_dir / "phase1c_historical_credit_index.json").read_text())
    if index.get("schema_version") != 1 or index.get("snapshots") != credit.get("snapshots"):
        raise ValueError("capacity cutoff registry drift")
    raw = (base_dir / SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != index["source_sha256"]:
        raise ValueError("historical capacity digest mismatch")
    source = json.loads(raw)
    if source.get("schema_version") != 1:
        raise ValueError("historical capacity schema drift")
    by_day = {}
    for day, capability, resource, available, allocated in source["rows"]:
        if (capability not in CAPABILITIES or resource not in RESOURCES or
                available < 0 or not 0 <= allocated <= available):
            raise ValueError("invalid historical capacity row")
        bucket = by_day.setdefault(day, {})
        key = (capability, resource)
        if key in bucket:
            raise ValueError("duplicate capacity resource/day")
        bucket[key] = (available, allocated)
    lookup = {entry["snapshot_id"]: entry for entry in index["snapshots"]}

    def resolve(snapshot_id):
        if snapshot_id not in lookup:
            raise ValueError("unregistered capacity cutoff")
        as_of = datetime.fromisoformat(lookup[snapshot_id]["as_of_at"])
        observed_day = as_of.date() if as_of.time() >= time(8) else as_of.date() - timedelta(days=1)
        observed = datetime.combine(observed_day, time(8), timezone.utc)
        if not observed <= as_of or as_of - observed > timedelta(hours=24):
            raise ValueError("missing fresh capacity observation")
        rows = []
        for offset in range(30):
            capacity_date = observed_day + timedelta(days=offset)
            values = by_day.get(capacity_date.isoformat())
            if values is None or len(values) != len(CAPABILITIES) * len(RESOURCES):
                raise ValueError("incomplete represented capacity horizon")
            for (capability, resource), (available, allocated) in sorted(values.items()):
                rows.append({"capacity_id": f"HIST-CAP-{observed_day}-{capacity_date}-{capability}-{resource}",
                             "location_id": source["location_id"], "capability_code": capability,
                             "resource_type": resource, "capacity_date": capacity_date.isoformat(),
                             "available_capacity_hours": available, "allocated_capacity_hours": allocated,
                             "snapshot_at": observed.isoformat(), "status": "active" if available else "unavailable",
                             "evidence_ref": f"HIST-WORKSHOP-PLAN-{observed_day}",
                             "time_zone": source["time_zone"]})
        return rows
    return resolve


def main():
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
    source, index = build(config, credit)
    (HERE / SOURCE).write_text(source)
    (HERE / INDEX).write_text(encode(index))
    resolver = load_resolver()
    for entry in index["snapshots"]:
        resolver(entry["snapshot_id"])
    print(f"Validated {len(index['snapshots'])} dated workshop views")


if __name__ == "__main__":
    main()
