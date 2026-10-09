"""Synthetic daily inventory and dated lane source, independent of deal inputs.

Production slots and digital commitments remain absent from this source.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random

import yaml

from phase1c_historical_operational import select_historical_operational
from render_phase1c_historical_inbound import load_resolver as load_inbound_resolver
from render_phase1c_historical_capacity import load_resolver as load_capacity_resolver
from render_phase1c_historical_digital import load_resolver as load_digital_resolver


HERE = Path(__file__).resolve().parent
PREFIX = "phase1c_historical_stock_source_"
LANES = "phase1c_historical_lane_source.json"
OFFERS = "phase1c_historical_offer_source.json"
INDEX = "phase1c_historical_operational_index.json"
START = date(2026, 2, 28)
END = date(2026, 8, 31)
DAYS = (END - START).days + 1


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def build(portfolio, config, contract, credit_index):
    if len(credit_index["snapshots"]) != 400:
        raise ValueError("historical cutoff registry drift")
    rng = random.Random(config["random_seed"] + 1300)
    products = sorted((p for p in portfolio["products"]
                       if p["fulfillment_mode"] in ("stocked_finished", "component")),
                      key=lambda p: p["product_id"])
    if len(products) != 48:
        raise ValueError("physical stock source coverage drift")
    stocked = [p for p in products if p["fulfillment_mode"] == "stocked_finished"]
    state = ["healthy"] * 7 + ["tight"] * 3 + ["below_reorder", "zero_available"]
    rng.shuffle(state)
    states = dict(zip((p["product_id"] for p in stocked), state))
    availability = config["commercial_supply"]["availability"]
    ratios = availability["available_to_target_stock_ratio_by_state"]
    stock = []
    for i, product in enumerate(products):
        pid = product["product_id"]
        location = availability["inventory_locations"][i % 2]
        if product["fulfillment_mode"] == "component":
            band = config["fulfillment_production_calibration"]["proposed_parameters"]["aggregate_inventory"]
            baseline = round(rng.triangular(*band["component_on_hand_units"][::2], band["component_on_hand_units"][1]))
            stock_state = "component"
        else:
            stock_state = states[pid]
            low, high = ratios[stock_state]
            target = availability["target_stock_units_by_demand_class"]["regular"]["mode"]
            baseline = round(target * rng.uniform(low, high))
        daily = []
        for day in range(DAYS):
            if stock_state == "zero_available":
                on_hand, allocated = 0, 0
            else:
                available = max(1, baseline + rng.choice([-2, -1, 0, 0, 0, 1, 2]))
                allocated = round(available * rng.uniform(0, .3))
                on_hand = available + allocated
            daily.append([on_hand, allocated])
        stock.append({"product_id": pid, "location_id": location,
                      "state_at_generation": stock_state, "daily": daily})
    regions = contract["controlled_vocabularies"]["destination_regions"]
    location_info = contract["controlled_vocabularies"]["location_codes"]
    lanes = []
    for location, info in location_info.items():
        for country, region_codes in regions.items():
            for region in region_codes:
                transit = (2 if country == info["country_code"] else 4 if country in ("DE", "NL", "BE") else 7)
                lanes.append({"lane_id": f"HIST-LANE-{location}-{region}",
                    "origin_location_id": location, "origin_time_zone": info["time_zone"],
                    "destination_country_code": country, "destination_region": region,
                    "shipping_service_code": "standard", "transit_workdays": transit,
                    "dispatch_weekdays_json": [1, 2, 3, 4, 5], "cutoff_local_time": "15:00:00",
                    "is_active": True, "verified_at": "2026-01-01T09:00:00Z",
                    "effective_from": "2026-01-01T00:00:00Z",
                    "expires_at": "2027-01-01T00:00:00Z"})
    files = {f"{PREFIX}{n+1:02d}.json": encode({"schema_version": 1,
             "provenance": "synthetic_provisional_daily_stock", "start_date": START.isoformat(),
             "end_date": END.isoformat(), "products": stock[n*12:(n+1)*12]}) for n in range(4)}
    files[LANES] = encode({"schema_version": 1,
                           "provenance": "synthetic_provisional_shipping_lanes", "lanes": lanes})
    offer_products = [p for p in portfolio["products"] if p["fulfillment_mode"] in
                      ("supplier_finished", "component")]
    offer_products.sort(key=lambda p: p["product_id"])
    # Covers 32/36 components and 22/27 supplier-finished SKUs; an offer is not a commitment.
    covered = ([p for p in offer_products if p["fulfillment_mode"] == "component"][:32] +
               [p for p in offer_products if p["fulfillment_mode"] == "supplier_finished"][:22])
    offers = []
    for product in covered:
        for quarter, start in enumerate(("2026-01-01", "2026-04-01", "2026-07-01"), 1):
            start_day = date.fromisoformat(start)
            offers.append({"supplier_item_id": f"HIST-OFFER-{product['product_id']}-{quarter}",
                "supplier_id": f"HIST-SUP-{1 + len(offers) % 10:02d}",
                "product_id": product["product_id"], "is_active": True,
                "valid_from": start, "valid_to": (start_day + timedelta(days=89)).isoformat(),
                "verified_at": datetime.combine(start_day, time(8), timezone.utc).isoformat(),
                "lead_days_mode": 10 if product["fulfillment_mode"] == "component" else 14})
    files[OFFERS] = encode({"schema_version": 1,
                            "provenance": "synthetic_provisional_supplier_offers", "offers": offers})
    index = {"schema_version": 1, "provenance": "synthetic_provisional_operational_source",
             "source_sha256": {name: hashlib.sha256(content.encode()).hexdigest()
                               for name, content in files.items()},
             "snapshots": credit_index["snapshots"]}
    return files, index


def load_resolver(base_dir=HERE):
    index = json.loads((base_dir / INDEX).read_text())
    credit = json.loads((base_dir / "phase1c_historical_credit_index.json").read_text())
    if index.get("snapshots") != credit.get("snapshots"):
        raise ValueError("operational and credit cutoff registries differ")
    stock, lanes, offers = [], None, None
    for name, digest in index["source_sha256"].items():
        raw = (base_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"historical operational source digest mismatch: {name}")
        payload = json.loads(raw)
        if payload.get("schema_version") != 1:
            raise ValueError("historical operational source schema drift")
        if name == LANES:
            lanes = payload["lanes"]
        elif name == OFFERS:
            offers = payload["offers"]
        else:
            if payload.get("start_date") != START.isoformat() or payload.get("end_date") != END.isoformat():
                raise ValueError("historical inventory date range drift")
            stock.extend(payload["products"])
    if len(stock) != 48 or lanes is None or offers is None:
        raise ValueError("incomplete historical stock/lane/offer source")
    inbound_resolver = load_inbound_resolver(base_dir)
    capacity_resolver = load_capacity_resolver(base_dir)
    digital_resolver = load_digital_resolver(base_dir)
    lookup = {entry["snapshot_id"]: entry for entry in index["snapshots"]}
    def resolve(snapshot_id):
        if snapshot_id not in lookup:
            raise ValueError("unregistered historical operational cutoff")
        entry = lookup[snapshot_id]
        as_of = datetime.fromisoformat(entry["as_of_at"])
        day = as_of.date() if as_of.time() >= time(8) else as_of.date() - timedelta(days=1)
        offset = (day - START).days
        if not 0 <= offset < DAYS:
            raise ValueError("inventory source outside dated range")
        observed = datetime.combine(day, time(8), timezone.utc).isoformat()
        rows = []
        for item in stock:
            if len(item["daily"]) != DAYS:
                raise ValueError("incomplete daily stock source")
            on_hand, allocated = item["daily"][offset]
            rows.append({"inventory_id": f"HIST-STOCK-{item['product_id']}-{day.isoformat()}",
                         "product_id": item["product_id"], "location_id": item["location_id"],
                         "quantity_on_hand": on_hand, "quantity_allocated": allocated,
                         "snapshot_at": observed})
        digital_source = digital_resolver(snapshot_id)
        manifest = {"schema_version": 1, "snapshot_id": snapshot_id,
                    "as_of_at": entry["as_of_at"], "complete": True,
                    "coverage_label": "provisional_stock_lanes_offers_inbound",
                    "inventory": rows, "shipping_lanes": lanes,
                    **inbound_resolver(snapshot_id),
                    "supplier_offers": [item for item in offers
                        if date.fromisoformat(item["valid_from"]) <= as_of.date() <=
                           date.fromisoformat(item["valid_to"]) and
                           datetime.fromisoformat(item["verified_at"]) <= as_of],
                    "production_capacity": capacity_resolver(snapshot_id),
                    **digital_source}
        select_historical_operational(manifest, {"data_snapshot_ref": snapshot_id,
                                                  "as_of_at": as_of})
        return manifest
    return resolve


def main():
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
    files, index = build(portfolio, config, contract, credit)
    for name, content in files.items():
        (HERE / name).write_text(content)
    (HERE / INDEX).write_text(encode(index))
    resolver = load_resolver()
    for entry in index["snapshots"]:
        resolver(entry["snapshot_id"])
    print(f"Validated {len(index['snapshots'])} provisional stock/lane views")


if __name__ == "__main__":
    main()
