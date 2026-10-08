"""Freeze credit and AR as they were known at a historical run's cutoff.

The current credit/AR tables have one mutable-looking row per customer or
invoice. Historical decisions must use a separate, complete snapshot selected
by the run's data_snapshot_ref; today's rows are never a fallback.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def _instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("historical instant requires a time zone")
    return parsed


def _money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid historical money amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("historical money amount must be finite and nonnegative")
    return amount


def select_historical_credit(manifest, run, customer_id):
    """Return (profile, receivables, payments, account_status) or fail closed."""
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or manifest.get("snapshot_id") != run["data_snapshot_ref"]
            or manifest.get("customer_id") != customer_id
            or manifest.get("complete") is not True):
        raise ValueError("missing or incomplete historical credit snapshot")
    as_of = run["as_of_at"]
    if _instant(manifest["as_of_at"]) != as_of:
        raise ValueError("historical credit snapshot cutoff differs from run")
    if manifest.get("account_status") not in {"Active", "Inactive", "Suspended", "Blocked"}:
        raise ValueError("invalid historical account status")
    profile = dict(manifest["credit_profile"])
    proof = manifest["commitment_evidence"]
    if profile.get("customer_id") != customer_id or proof.get("customer_id") != customer_id:
        raise ValueError("historical credit customer mismatch")
    profile["credit_limit"] = _money(profile["credit_limit"])
    if profile["credit_limit"] <= 0:
        raise ValueError("historical credit limit must be positive")
    profile["unbilled_committed_amount"] = _money(profile["unbilled_committed_amount"])
    profile["commitments_as_of_at"] = _instant(profile["commitments_as_of_at"])
    issued = _instant(proof["issued_at"])
    if (profile["commitments_as_of_at"] > as_of or issued > as_of
            or not isinstance(profile.get("commitment_evidence_ref"), str)
            or not profile["commitment_evidence_ref"].strip()
            or proof.get("evidence_ref") != profile.get("commitment_evidence_ref")
            or _money(proof.get("amount")) != profile["unbilled_committed_amount"]
            or issued < profile["commitments_as_of_at"]):
        raise ValueError("historical commitment proof is absent, future or inconsistent")
    receivables = []
    invoices = set()
    for source in manifest["receivables"]:
        row = dict(source)
        if row.get("customer_id") != customer_id or row.get("invoice_number") in invoices:
            raise ValueError("historical AR customer or invoice mismatch")
        invoices.add(row["invoice_number"])
        for field in ("invoice_date", "due_date", "as_of_date"):
            row[field] = date.fromisoformat(row[field])
        row["original_amount"] = _money(row["original_amount"])
        row["outstanding_amount"] = _money(row["outstanding_amount"])
        if (row["invoice_date"] > row["as_of_date"] or row["as_of_date"] > as_of.date()
                or row["outstanding_amount"] > row["original_amount"]):
            raise ValueError("historical AR row is future or arithmetically invalid")
        receivables.append(row)
    payments = []
    for source in manifest["payments"]:
        row = dict(source)
        if row.get("customer_id") != customer_id:
            raise ValueError("historical payment customer mismatch")
        row["paid_date"] = date.fromisoformat(row["paid_date"])
        if row["paid_date"] > as_of.date():
            raise ValueError("future payment in historical snapshot")
        payments.append(row)
    return profile, receivables, payments, manifest["account_status"]
