from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from phase1c_historical_credit import select_historical_credit


RUN = {"data_snapshot_ref": "HIST-SNAP-1",
       "as_of_at": datetime(2026, 9, 1, 12, tzinfo=timezone.utc)}
MANIFEST = {
    "schema_version": 1, "snapshot_id": "HIST-SNAP-1", "complete": True,
    "customer_id": "C-1", "as_of_at": "2026-09-01T12:00:00Z",
    "account_status": "Active",
    "credit_profile": {"customer_id": "C-1", "credit_limit": "1000.00",
                       "unbilled_committed_amount": "100.00",
                       "commitments_as_of_at": "2026-09-01T08:00:00Z",
                       "commitment_evidence_ref": "COMMIT-1", "credit_status": "Active"},
    "commitment_evidence": {"evidence_ref": "COMMIT-1", "customer_id": "C-1",
                            "amount": "100.00", "issued_at": "2026-09-01T09:00:00Z"},
    "receivables": [{"customer_id": "C-1", "receivable_id": "AR-1", "invoice_number": "INV-1",
                     "invoice_date": "2026-08-01", "due_date": "2026-08-31",
                     "as_of_date": "2026-09-01", "original_amount": "300.00",
                     "outstanding_amount": "250.00", "status": "Overdue"}],
    "payments": [{"customer_id": "C-1", "paid_date": "2026-08-20", "payment_id": "PAY-1"}],
}


class HistoricalCreditTests(unittest.TestCase):
    def test_frozen_snapshot_yields_typed_credit_and_ar(self):
        profile, ar, payments, status = select_historical_credit(MANIFEST, RUN, "C-1")
        self.assertEqual(profile["unbilled_committed_amount"], Decimal("100.00"))
        self.assertEqual(ar[0]["outstanding_amount"], Decimal("250.00"))
        self.assertEqual(payments[0]["paid_date"].isoformat(), "2026-08-20")
        self.assertEqual(status, "Active")

    def test_missing_manifest_or_wrong_snapshot_fails_closed(self):
        for change in ({"complete": False}, {"snapshot_id": "TODAY"}, {"customer_id": "C-2"}):
            with self.subTest(change=change):
                snapshot = deepcopy(MANIFEST)
                snapshot.update(change)
                with self.assertRaises(ValueError):
                    select_historical_credit(snapshot, RUN, "C-1")

    def test_future_ar_payment_and_credit_proof_are_rejected(self):
        paths = [
            ("receivables", "as_of_date", "2026-09-02"),
            ("payments", "paid_date", "2026-09-02"),
            ("commitment_evidence", "issued_at", "2026-09-02T09:00:00Z"),
        ]
        for section, key, value in paths:
            with self.subTest(section=section):
                snapshot = deepcopy(MANIFEST)
                row = snapshot[section][0] if isinstance(snapshot[section], list) else snapshot[section]
                row[key] = value
                with self.assertRaises(ValueError):
                    select_historical_credit(snapshot, RUN, "C-1")

    def test_commitment_amount_and_invoice_uniqueness_are_independent(self):
        snapshot = deepcopy(MANIFEST)
        snapshot["commitment_evidence"]["amount"] = "200.00"
        with self.assertRaises(ValueError):
            select_historical_credit(snapshot, RUN, "C-1")
        snapshot = deepcopy(MANIFEST)
        snapshot["receivables"].append(deepcopy(snapshot["receivables"][0]))
        with self.assertRaises(ValueError):
            select_historical_credit(snapshot, RUN, "C-1")


if __name__ == "__main__":
    unittest.main()
