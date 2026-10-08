"""Generate a dated synthetic credit, commitment, invoice and payment source ledger.

Separate from the historical deal-input generator. A resolver freezes only the
facts available at a registered cutoff; it never reads current credit/AR tables.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random

import yaml

from phase1c_historical_credit import select_historical_credit


HERE = Path(__file__).resolve().parent
INDEX_PATH = HERE / "phase1c_historical_credit_index.json"
PREFIX = "phase1c_historical_credit_source_"
FIRST = datetime(2026, 3, 1, 9, tzinfo=timezone.utc)


def canonical(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def money(value):
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def historical_cutoff(n):
    return FIRST + timedelta(minutes=(n - 1) * 660)


def build(config, customers):
    if config["dataset"]["historical_deals"] != 400 or len(customers["commitments"]) != 80:
        raise ValueError("historical or customer target drift")
    rng = random.Random(config["random_seed"] + 905)
    settings = config["commercial_supply"]
    credit = settings["credit_profiles"]
    payments = settings["payment_history"]
    ar = settings["accounts_receivable"]
    source = []
    for customer in customers["commitments"]:
        cid = customer["customer_id"]
        segment = customer["size_segment"]
        risk = customer["risk_rating"]
        band = credit["credit_limit_eur_by_segment"][segment]
        limit = Decimal(money(rng.triangular(band["minimum"], band["maximum"], band["mode"])))
        commitments = []
        for month in range(2, 9):
            recorded = datetime(2026, month, 1, 8, tzinfo=timezone.utc)
            commitments.append({"evidence_ref": f"HIST-COMMIT-{cid}-{month:02d}",
                                "recorded_at": recorded.isoformat(),
                                "amount_eur": money(limit * Decimal(str(rng.uniform(0, .18))))})
        count_band = payments["paid_invoice_count_by_segment"][segment]
        paid_count = round(rng.triangular(count_band["minimum"], count_band["maximum"], count_band["mode"]))
        paid = []
        for k in range(paid_count):
            issued = date(2025, 4, 1) + timedelta(days=round(k * 300 / max(1, paid_count - 1)))
            due = issued + timedelta(days=30)
            delay_bands = payments["payment_delay_day_bands_by_risk"][risk]
            draw = rng.random()
            running = 0
            selected = None
            for code, entry in delay_bands.items():
                running += entry["share"]
                if draw <= running:
                    selected = entry
                    break
            selected = selected or list(delay_bands.values())[-1]
            delay = rng.randint(*selected["range"])
            paid_day = max(issued, due + timedelta(days=delay))
            amount = money(rng.uniform(250, 3000) * (1 if segment == "SMB" else 3 if segment == "Mid-Market" else 9))
            paid.append({"customer_id": cid, "payment_id": f"HIST-PAY-{cid}-{k+1:02d}",
                         "invoice_number": f"HIST-PAID-{cid}-{k+1:02d}",
                         "invoice_date": issued.isoformat(), "due_date": due.isoformat(),
                         "paid_date": paid_day.isoformat(), "invoice_amount": amount,
                         "paid_amount": amount})
        open_band = ar["open_invoice_count_by_segment"][segment]
        open_count = round(rng.triangular(open_band["minimum"], open_band["maximum"], open_band["mode"]))
        invoices = []
        for k in range(open_count):
            issued = date(2026, 7, 10) + timedelta(days=rng.randrange(45))
            due = issued + timedelta(days=90)
            original = Decimal(money(rng.uniform(400, 3200) *
                                    (1 if segment == "SMB" else 3 if segment == "Mid-Market" else 9)))
            fraction = Decimal(str(rng.choice(["0", "0.25", "0.5"])))
            invoice = {"customer_id": cid, "receivable_id": f"HIST-AR-{cid}-{k+1:02d}",
                       "invoice_number": f"HIST-OPEN-{cid}-{k+1:02d}",
                       "invoice_date": issued.isoformat(), "due_date": due.isoformat(),
                       "original_amount": money(original), "partial_paid_amount": money(original * fraction),
                       "partial_paid_date": (issued + timedelta(days=7)).isoformat() if fraction else None}
            invoices.append(invoice)
        source.append({"customer_id": cid, "size_segment": segment, "risk_rating": risk,
                       "credit_status": customer["credit_status"], "credit_limit": money(limit),
                       "account_status": "Active", "commitments": commitments,
                       "paid_invoices": paid, "open_invoices": invoices,
                       "adverse_signal": customer["adverse_signal"]})
    all_open = [invoice for customer in source for invoice in customer["open_invoices"]]
    for position in rng.sample(range(len(all_open)), round(len(all_open) * .23)):
        invoice = all_open[position]
        issued = date(2026, 5, 1) + timedelta(days=rng.randrange(62))
        invoice["invoice_date"] = issued.isoformat()
        invoice["due_date"] = (issued + timedelta(days=30)).isoformat()
        if invoice["partial_paid_date"] is not None:
            invoice["partial_paid_date"] = (issued + timedelta(days=7)).isoformat()
    shards = [dict(schema_version=1, provenance="synthetic_historical_credit_source",
                   customers=source[n:n+10]) for n in range(0, 80, 10)]
    files = {f"{PREFIX}{n:02d}.json": canonical(shard) for n, shard in enumerate(shards, 1)}
    index = {"schema_version": 1, "provenance": "synthetic_historical_credit_source",
             "source_sha256": {name: hashlib.sha256(content.encode()).hexdigest()
                               for name, content in files.items()},
             "snapshots": [{"snapshot_id": f"HIST-CREDIT-{n:04d}",
                            "customer_id": customers["commitments"][(n-1) % 80]["customer_id"],
                            "as_of_at": historical_cutoff(n).isoformat()}
                           for n in range(1, 401)]}
    return files, index


def freeze_snapshot(index, sources, snapshot_id):
    matches = [item for item in index["snapshots"] if item["snapshot_id"] == snapshot_id]
    if len(matches) != 1:
        raise ValueError("unregistered historical credit cutoff")
    entry = matches[0]
    as_of = datetime.fromisoformat(entry["as_of_at"])
    customer = sources.get(entry["customer_id"])
    if not customer:
        raise ValueError("missing historical credit source customer")
    events = [event for event in customer["commitments"]
              if datetime.fromisoformat(event["recorded_at"]) <= as_of]
    if not events:
        raise ValueError("no contemporaneous commitment record")
    event = max(events, key=lambda item: item["recorded_at"])
    cutoff = as_of.date()
    receivables = []
    payment_rows = [row for row in customer["paid_invoices"]
                    if date.fromisoformat(row["paid_date"]) <= cutoff]
    for invoice in customer["open_invoices"]:
        issued = date.fromisoformat(invoice["invoice_date"])
        if issued > cutoff:
            continue
        partial_date = date.fromisoformat(invoice["partial_paid_date"]) if invoice["partial_paid_date"] else None
        partial = Decimal(invoice["partial_paid_amount"]) if partial_date and partial_date <= cutoff else Decimal(0)
        original = Decimal(invoice["original_amount"])
        outstanding = original - partial
        due = date.fromisoformat(invoice["due_date"])
        status = "Overdue" if due < cutoff else "Partially Paid" if partial else "Open"
        receivables.append({key: invoice[key] for key in ("customer_id", "receivable_id", "invoice_number",
                           "invoice_date", "due_date", "original_amount")}
                           | {"outstanding_amount": money(outstanding), "status": status,
                              "as_of_date": cutoff.isoformat()})
        if partial:
            payment_rows.append({"customer_id": customer["customer_id"],
                "payment_id": f"HIST-PARTIAL-{invoice['receivable_id']}",
                "invoice_number": invoice["invoice_number"], "invoice_date": invoice["invoice_date"],
                "due_date": invoice["due_date"], "paid_date": partial_date.isoformat(),
                "invoice_amount": invoice["original_amount"], "paid_amount": money(partial)})
    cid = customer["customer_id"]
    return {"schema_version": 1, "snapshot_id": snapshot_id, "complete": True,
            "customer_id": cid, "as_of_at": entry["as_of_at"],
            "account_status": customer["account_status"],
            "credit_profile": {"customer_id": cid, "credit_limit": customer["credit_limit"],
                "unbilled_committed_amount": event["amount_eur"],
                "commitments_as_of_at": event["recorded_at"],
                "commitment_evidence_ref": event["evidence_ref"],
                "risk_rating": customer["risk_rating"], "credit_status": customer["credit_status"]},
            "commitment_evidence": {"evidence_ref": event["evidence_ref"],
                "customer_id": cid, "amount": event["amount_eur"],
                "issued_at": event["recorded_at"],
                "adverse_signal": customer["adverse_signal"]},
            "receivables": receivables, "payments": payment_rows}


def load_resolver(base_dir=HERE):
    index = json.loads((base_dir / INDEX_PATH.name).read_text())
    sources = {}
    for name, digest in index["source_sha256"].items():
        raw = (base_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"historical source digest mismatch: {name}")
        shard = json.loads(raw)
        if shard.get("schema_version") != 1 or shard.get("provenance") != index["provenance"]:
            raise ValueError("historical source schema/provenance mismatch")
        for entry in shard["customers"]:
            cid = entry["customer_id"]
            if cid in sources:
                raise ValueError("duplicate historical source customer")
            sources[cid] = entry
    def resolve(snapshot_id, customer_id):
        result = freeze_snapshot(index, sources, snapshot_id)
        if result["customer_id"] != customer_id:
            raise ValueError("historical snapshot customer mismatch")
        return result
    return resolve


def main():
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    customers = json.loads((HERE / "phase1c_customer_commitment_ledger.json").read_text())
    files, index = build(config, customers)
    for name, content in files.items():
        (HERE / name).write_text(content)
    INDEX_PATH.write_text(canonical(index))
    resolver = load_resolver()
    for item in index["snapshots"]:
        manifest = resolver(item["snapshot_id"], item["customer_id"])
        select_historical_credit(manifest, {"data_snapshot_ref": item["snapshot_id"],
                                 "as_of_at": datetime.fromisoformat(item["as_of_at"])}, item["customer_id"])
    print(f"Validated {len(index['snapshots'])} frozen historical credit/AR views")


if __name__ == "__main__":
    main()
