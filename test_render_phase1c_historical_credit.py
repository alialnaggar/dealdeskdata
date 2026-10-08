"""Verify independent dated credit/AR source and all registered cutoffs."""

from collections import Counter
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import unittest

import yaml

from phase1c_historical_credit import select_historical_credit
from render_phase1c_historical_credit import build, canonical, freeze_snapshot, load_resolver


HERE = Path(__file__).resolve().parent


class HistoricalCreditSourceTests(unittest.TestCase):
    def test_rebuild_hashes_and_all_cutoffs(self):
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        customers = json.loads((HERE / "phase1c_customer_commitment_ledger.json").read_text())
        files, index = build(config, customers)
        self.assertEqual(index, json.loads((HERE / "phase1c_historical_credit_index.json").read_text()))
        self.assertEqual(canonical(index), (HERE / "phase1c_historical_credit_index.json").read_text())
        self.assertEqual(len(files), 8)
        for name, content in files.items():
            self.assertEqual(content, (HERE / name).read_text())
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), index["source_sha256"][name])
        source = {item["customer_id"]: item for content in files.values()
                  for item in json.loads(content)["customers"]}
        self.assertEqual(len(source), 80)
        paid_bands = config["commercial_supply"]["payment_history"]["paid_invoice_count_by_segment"]
        open_bands = config["commercial_supply"]["accounts_receivable"]["open_invoice_count_by_segment"]
        for item in source.values():
            segment = item["size_segment"]
            self.assertGreaterEqual(len(item["paid_invoices"]), paid_bands[segment]["minimum"])
            self.assertLessEqual(len(item["paid_invoices"]), paid_bands[segment]["maximum"])
            self.assertGreaterEqual(len(item["open_invoices"]), open_bands[segment]["minimum"])
            self.assertLessEqual(len(item["open_invoices"]), open_bands[segment]["maximum"])
        all_open = [invoice for item in source.values() for invoice in item["open_invoices"]]
        overdue_share = sum(invoice["due_date"] < "2026-09-01" for invoice in all_open) / len(all_open)
        self.assertGreaterEqual(overdue_share, .18)
        self.assertLessEqual(overdue_share, .28)
        self.assertEqual(len(index["snapshots"]), 400)
        resolver = load_resolver()
        status = Counter()
        for item in index["snapshots"]:
            manifest = resolver(item["snapshot_id"], item["customer_id"])
            profile, receivables, payments, account = select_historical_credit(
                manifest, {"data_snapshot_ref": item["snapshot_id"],
                           "as_of_at": datetime.fromisoformat(item["as_of_at"])}, item["customer_id"])
            self.assertEqual(account, "Active")
            self.assertEqual(profile["customer_id"], item["customer_id"])
            self.assertTrue(all(invoice["as_of_date"] <= datetime.fromisoformat(item["as_of_at"]).date()
                                for invoice in receivables))
            self.assertTrue(all(payment["paid_date"] <= datetime.fromisoformat(item["as_of_at"]).date()
                                for payment in payments))
            status.update(invoice["status"] for invoice in receivables)
        self.assertGreater(status["Overdue"], 0)
        with self.assertRaises(ValueError):
            resolver("HIST-CREDIT-0001", "SYN-CUST-002")
        with self.assertRaises(ValueError):
            resolver("MISSING", "SYN-CUST-001")

    def test_future_invoice_payment_and_proof_cannot_enter_early_snapshot(self):
        index = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        source = {item["customer_id"]: item for n in range(1, 9)
                  for item in json.loads((HERE / f"phase1c_historical_credit_source_{n:02d}.json").read_text())["customers"]}
        early = freeze_snapshot(index, source, "HIST-CREDIT-0001")
        late = freeze_snapshot(index, source, "HIST-CREDIT-0321")
        self.assertLess(len(early["receivables"]), len(late["receivables"]))
        self.assertTrue(all(date.fromisoformat(p["paid_date"]) <= date(2026, 3, 1)
                            for p in early["payments"]))
        self.assertLessEqual(datetime.fromisoformat(early["commitment_evidence"]["issued_at"]),
                             datetime.fromisoformat(early["as_of_at"]))
        corrupted = deepcopy(early)
        corrupted["commitment_evidence"]["amount"] = "999999.99"
        with self.assertRaises(ValueError):
            select_historical_credit(corrupted, {"data_snapshot_ref": early["snapshot_id"],
                "as_of_at": datetime.fromisoformat(early["as_of_at"])}, early["customer_id"])


if __name__ == "__main__":
    unittest.main()
