"""Build provisional history submissions; outcomes and replay snapshots come later.

The four SQL shards can be loaded after the provisional product/customer masters.
No source evidence, historical decision, or agent result is invented here.
"""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import random

import yaml

from phase1c_digital_units import digital_demand
from render_phase1c_sellable_catalogue import product_rows
from render_phase1c_vertical_pilot import insert


HERE = Path(__file__).resolve().parent
REPORT_PATH = HERE / "phase1c_historical_inputs_report.json"
PREFIX = "phase1c_historical_inputs_"


def build(portfolio, costs, config, contract, customers):
    dataset = config["dataset"]
    total = dataset["historical_deals"]
    if total != 400 or dataset["time_model"]["evaluation_as_of_date"] != "2026-09-01":
        raise ValueError("historical target or evaluation date drift")
    rng = random.Random(config["random_seed"] + 400)
    customer_ids = [entry["customer_id"] for entry in customers["commitments"]]
    if len(customer_ids) != dataset["customers"] or len(set(customer_ids)) != len(customer_ids):
        raise ValueError("missing customer master ledger")
    sizes = dataset["historical_lines_per_deal_sampling_percent"]
    bins = {int(n): int(Decimal(str(pct)) * total / 100) for n, pct in sizes.items()}
    if sum(bins.values()) != total:
        raise ValueError("historical line bins do not yield integer quotas")
    line_counts = [n for n, count in bins.items() for _ in range(count)]
    rng.shuffle(line_counts)
    count_lines = sum(line_counts)
    available = {p[0]: (Decimal(str(p[7])), p[10], p[12])
                 for p in product_rows(portfolio, costs, config, contract)}
    available.update({p["product_id"]: (Decimal(str(p["product_list_price_eur"])),
                         "device", "make_to_order") for p in costs["products"]})
    catalog = {p["product_id"]: p for p in portfolio["products"] if p["is_sellable"]}
    if set(available) != set(catalog) or len(available) != 120 or count_lines != 1200:
        raise ValueError("sellable catalogue or line target drift")
    popularity = dataset["product_popularity"]
    if Decimal(str(popularity["top_product_share"])) != Decimal("0.2"):
        raise ValueError("top-product fraction drift")
    top = set(rng.sample(sorted(available), 24))
    tail = sorted(set(available) - top)
    rng.shuffle(tail)
    remaining = {pid: (32 if pid in top else 5 if pid in tail[:48] else 4)
                 for pid in available}
    if sum(remaining.values()) != count_lines:
        raise ValueError("product occurrences do not cover historical lines")
    shards = ["-- Provisional historical submissions only; decisions and evidence are pending.\n"
              "SET search_path TO deal_desk, public;\n" for _ in range(8)]
    mode_counts = Counter()
    customer_counts = Counter()
    first = datetime(2026, 3, 1, 9, tzinfo=timezone.utc)
    last_date = date.fromisoformat(dataset["time_model"]["evaluation_as_of_date"])
    for n, size in enumerate(line_counts, 1):
        shard = (n - 1) // 50
        chosen = []
        for _ in range(size):
            candidates = [pid for pid, count in remaining.items() if count and pid not in chosen]
            if not candidates:
                raise ValueError("product assignment exhausted")
            pid = rng.choices(candidates, weights=[remaining[pid] for pid in candidates])[0]
            chosen.append(pid)
            remaining[pid] -= 1
        submitted = first + timedelta(minutes=(n - 1) * 660)
        if submitted.date() >= last_date:
            raise ValueError("historical submission reaches evaluation date")
        customer = customer_ids[(n - 1) % len(customer_ids)]
        customer_counts[customer] += 1
        deal_id = f"HIST-DEAL-{n:04d}"
        modes = {available[pid][2] for pid in chosen}
        physical = bool(modes & {"stocked_finished", "supplier_finished", "make_to_order"})
        country_shares = contract["controlled_vocabularies"]["customer_country_target_share_pct"]
        country = rng.choices(list(country_shares), weights=list(country_shares.values()))[0]
        region = rng.choice(contract["controlled_vocabularies"]["destination_regions"][country])
        terms = {"payment_terms_days": 30, "contract_clause_codes": ["standard"],
                 "allow_partial_delivery": False}
        if "digital_activation" in modes:
            terms["contract_months"] = 12
        shards[shard] += insert("deals", dict(deal_id=deal_id, customer_id=customer,
            salesperson_id=f"SALES-{1 + (n - 1) % 12:03d}",
            deal_name=f"Synthetic historical submission {n:04d}",
            submitted_at=submitted.isoformat(), catalog_version=portfolio["catalog_version"],
            policy_set_code=dataset["historical_policy_set_code"],
            requested_delivery_date=(submitted.date() + timedelta(days=14)).isoformat(),
            destination_country_code=country, destination_region=region,
            shipping_service_code="standard" if physical else None,
            terms_json=terms, requirements_json={}, evidence_refs_json=[],
            deal_status="Draft", dataset_type="historical"))
        for line_no, pid in enumerate(chosen, 1):
            price, unit, mode = available[pid]
            mode_counts[mode] += 1
            configuration = ({"selected_options": ["standard"]} if mode == "make_to_order" else
                             {"edition": catalog[pid]["attributes_json"]["edition"],
                              "units_per_period": 1} if mode == "digital_activation" else {})
            quantity = digital_demand(unit, 12, 1)[1] if mode == "digital_activation" else rng.randint(1, 3)
            if quantity is None:
                raise ValueError(f"unsupported digital unit {unit}")
            discount = Decimal(rng.choice(["0", "0.02", "0.04"]))
            shards[shard] += insert("deal_lines", dict(deal_line_id=f"HIST-LINE-{n:04d}-{line_no:02d}",
                deal_id=deal_id, line_number=line_no, product_id=pid, quantity=quantity,
                quoted_unit_price=(price * (1 - discount)).quantize(Decimal("0.01")),
                configuration_json=configuration,
                requested_activation_date=(submitted.date() + timedelta(days=3)).isoformat()
                if mode == "digital_activation" else None))
        shards[shard] += f"UPDATE deals SET deal_status='Submitted' WHERE deal_id='{deal_id}';\n"
    if any(remaining.values()):
        raise ValueError("unassigned product occurrences")
    report = {"schema_version": 1, "provenance": "synthetic_provisional_inputs",
              "seed": config["random_seed"] + 400,
              "historical_deals": total, "deal_lines": count_lines,
              "lines_per_deal": {str(k): v for k, v in sorted(bins.items())},
              "mean_lines_per_deal": count_lines / total,
              "sellable_products": len(available), "top_product_count": len(top),
              "top_product_line_count": 24 * 32,
              "top_product_line_share": 24 * 32 / count_lines,
              "minimum_product_occurrences": 4,
              "fulfillment_mode_lines": dict(sorted(mode_counts.items())),
              "customers_used": len(customer_counts),
              "historical_decisions_recorded": 0,
              "historical_evidence_snapshots_recorded": 0}
    return shards, report


def main():
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    customers = json.loads((HERE / "phase1c_customer_commitment_ledger.json").read_text())
    shards, report = build(portfolio, costs, config, contract, customers)
    for n, shard in enumerate(shards, 1):
        (HERE / f"{PREFIX}{n:02d}.sql").write_text(shard)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
