"""Render a provisional, reproducible 80-customer identity and credit slice."""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import random

import yaml

from render_phase1c_vertical_pilot import insert


HERE = Path(__file__).resolve().parent
SQL_PATH = HERE / "phase1c_customer_master.sql"
LEDGER_PATH = HERE / "phase1c_customer_commitment_ledger.json"
SNAPSHOT = "2026-09-01T09:00:00Z"


def allocated(counts, rng):
    values = [value for value, count in counts.items() for _ in range(count)]
    rng.shuffle(values)
    return values


def shares_to_counts(shares, total):
    counts = {key: int(Decimal(str(pct)) * total / 100) for key, pct in shares.items()}
    if sum(counts.values()) != total:
        raise ValueError("customer shares do not yield exact integer counts")
    return counts


def build(config, contract):
    dataset = config["dataset"]
    credit = config["commercial_supply"]["credit_profiles"]
    total = dataset["customers"]
    if total != credit["customer_count"] or total != 80:
        raise ValueError("customer count drift")
    if dataset["time_model"]["evaluation_as_of_date"] != "2026-09-01":
        raise ValueError("customer snapshot date drift")
    rng = random.Random(config["random_seed"] + 801)
    segments = allocated(dataset["customer_segment_counts"], rng)
    industries = allocated(shares_to_counts(contract["controlled_vocabularies"]["customer_industry_target_share_pct"], total), rng)
    countries = allocated(shares_to_counts(contract["controlled_vocabularies"]["customer_country_target_share_pct"], total), rng)
    risks = allocated(credit["risk_rating_exact_counts"], rng)
    statuses = allocated(credit["credit_status_exact_counts"], rng)
    if any(len(values) != total for values in (segments, industries, countries, risks, statuses)):
        raise ValueError("configured allocations must cover all customers")
    terms = {segment: allocated(counts, rng)
             for segment, counts in credit["default_payment_terms_exact_counts_by_segment"].items()}
    if any(len(terms[segment]) != count for segment, count in dataset["customer_segment_counts"].items()):
        raise ValueError("payment terms allocation drift")
    strategic = set(rng.sample([i for i, segment in enumerate(segments) if segment != "SMB"], 8))
    output = ["-- Provisional synthetic customer and credit master; load in a disposable transaction.\n",
              "-- Commitment ledger is synthetic generation evidence, not an external business record.\n",
              "SET search_path TO deal_desk, public;\n"]
    ledger = {"schema_version": 1, "snapshot_at": SNAPSHOT,
              "provenance": "synthetic_provisional", "commitments": []}
    regions = contract["controlled_vocabularies"]["destination_regions"]
    for index in range(total):
        number = index + 1
        customer_id = f"SYN-CUST-{number:03d}"
        segment = segments[index]
        country = countries[index]
        since = date(2020, 1, 1) + timedelta(days=rng.randrange(1900))
        output.append(insert("customers", dict(customer_id=customer_id,
            customer_code=customer_id, customer_name=f"Synthetic buyer {number:03d}",
            size_segment=segment, strategic_account=index in strategic,
            industry=industries[index], country_code=country,
            region=rng.choice(regions[country]), customer_since=since,
            account_status="Active")))
        band = credit["credit_limit_eur_by_segment"][segment]
        limit = Decimal(str(rng.triangular(band["minimum"], band["maximum"], band["mode"])))
        if index in strategic:
            limit *= Decimal(str(credit["strategic_account_multiplier"]))
        limit = min(limit, Decimal(str(credit["maximum_credit_limit_eur"]))).quantize(Decimal("0.01"))
        commitment = (limit * Decimal(str(rng.uniform(0, .22)))).quantize(Decimal("0.01"))
        reference = f"SYN-COMMIT-{number:03d}"
        status = statuses[index]
        ledger["commitments"].append(dict(customer_id=customer_id, size_segment=segment,
            risk_rating=risks[index], credit_status=status,
            evidence_ref=reference, amount_eur=str(commitment), recorded_at=SNAPSHOT,
            adverse_signal=("synthetic_account_hold" if status == "On-Hold" else None)))
        review = date(2026, 6, 1) + timedelta(days=rng.randrange(60))
        output.append(insert("customer_credit_profiles", dict(customer_id=customer_id,
            credit_limit=limit, unbilled_committed_amount=commitment,
            commitments_as_of_at=SNAPSHOT, commitment_evidence_ref=reference,
            risk_rating=risks[index], credit_status=status,
            default_payment_terms_days=terms[segment].pop(),
            last_review_date=review, next_review_date=review + timedelta(days=180))))
    return "".join(output), ledger


if __name__ == "__main__":
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    sql, ledger = build(config, contract)
    SQL_PATH.write_text(sql)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"Wrote {SQL_PATH.name} and {LEDGER_PATH.name}: {len(ledger['commitments'])} customers")
