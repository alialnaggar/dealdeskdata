"""Reproduce source and verify all dated, independent inbound receipts."""

from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

import yaml

from phase1c_historical_operational import select_historical_operational
from render_phase1c_historical_inbound import build, encode, INDEX, load_resolver
from render_phase1c_historical_stock_lanes import load_resolver as load_operational_resolver

HERE = Path(__file__).resolve().parent


class HistoricalInboundTests(unittest.TestCase):
    def test_deterministic_source_and_replay(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        files, index = build(portfolio, config, credit)
        self.assertEqual(encode(index), (HERE / INDEX).read_text())
        events = []
        for name, content in files.items():
            self.assertEqual(content, (HERE / name).read_text())
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), index["source_sha256"][name])
            events.extend(json.loads(content)["events"])
        self.assertEqual(len(events), 441)
        self.assertEqual(len({x["product_id"] for x in events}), 63)
        targets = config["commercial_supply"]["availability"]["inbound_status_target_share"]
        counts = Counter(x["status"] for x in events)
        for status, target in targets.items():
            self.assertLess(abs(counts[status] / len(events) - target), .005)
        self.assertTrue(any(x["inbound_evidence"] for x in events))
        self.assertTrue(any(x["purchase_order_evidence"] for x in events))

        resolve = load_resolver()
        operational = load_operational_resolver()
        binding = 0
        for entry in index["snapshots"]:
            as_of = datetime.fromisoformat(entry["as_of_at"])
            manifest = operational(entry["snapshot_id"])
            self.assertEqual(resolve(entry["snapshot_id"])["inbound_supply"], manifest["inbound_supply"])
            typed = select_historical_operational(manifest, {
                "data_snapshot_ref": entry["snapshot_id"], "as_of_at": as_of})
            binding += sum(row["status"] == "Confirmed" and
                           row["valid_until"] > as_of for row in typed["inbound_supply"])
        self.assertGreater(binding, 0)

    def test_tampered_proof_or_future_header_rejected(self):
        credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        entry = credit["snapshots"][-1]
        manifest = load_operational_resolver()(entry["snapshot_id"])
        run = {"data_snapshot_ref": entry["snapshot_id"],
               "as_of_at": datetime.fromisoformat(entry["as_of_at"])}
        case = deepcopy(manifest)
        case["inbound_evidence"][0]["quantity"] += 1
        with self.assertRaisesRegex(ValueError, "independent proof"):
            select_historical_operational(case, run)
        case = deepcopy(manifest)
        case["purchase_order_evidence"][0]["issued_at"] = "2027-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "future purchase order"):
            select_historical_operational(case, run)


if __name__ == "__main__":
    unittest.main()
