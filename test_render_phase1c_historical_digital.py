"""Reproduce digital pools and reject forged or future provider proof."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import unittest

import yaml

from phase1c_historical_operational import select_historical_operational
from render_phase1c_historical_digital import (
    build, encode, INDEX, load_provider_resolver, load_resolver)
from render_phase1c_historical_stock_lanes import load_resolver as load_operational

HERE = Path(__file__).resolve().parent


class HistoricalDigitalTests(unittest.TestCase):
    def test_reproducible_source_and_historical_replay(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        files, index = build(portfolio, config, credit)
        self.assertEqual(encode(index), (HERE / INDEX).read_text())
        for name, content in files.items():
            self.assertEqual(content, (HERE / name).read_text())
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(),
                             index["source_sha256"][name])
        pools = json.loads(files["phase1c_historical_digital_pool_source.json"])["pools"]
        self.assertEqual(len(pools), 180)
        self.assertEqual(len({p["product_id"] for p in pools}), 36)
        statuses = Counter(event[0] for pool in pools for event in pool["events"])
        self.assertEqual(statuses, {"binding": 3906, "provisional": 1116, "unknown": 558})
        digital = load_resolver()
        operational = load_operational()
        binding_seen = 0
        for entry in index["snapshots"]:
            as_of = datetime.fromisoformat(entry["as_of_at"])
            view = digital(entry["snapshot_id"])
            self.assertEqual(len(view["digital_capacity"]), 180)
            self.assertTrue(all(datetime.fromisoformat(row["snapshot_at"]) <= as_of and
                                as_of - datetime.fromisoformat(row["snapshot_at"]) <= timedelta(hours=24)
                                for row in view["digital_capacity"]))
            self.assertTrue(all(datetime.fromisoformat(proof["verified_at"]) <= as_of
                                for proof in view["provider_evidence"]))
            binding_seen += len(view["provider_evidence"])
            manifest = operational(entry["snapshot_id"])
            self.assertEqual(manifest["digital_capacity"], view["digital_capacity"])
            typed = select_historical_operational(manifest, {
                "data_snapshot_ref": entry["snapshot_id"], "as_of_at": as_of})
            self.assertEqual(len(typed["digital_capacity"]), 180)
        self.assertGreater(binding_seen, 0)

    def test_provider_proof_is_bound_to_pool_and_cutoff(self):
        credit = json.loads((HERE / INDEX).read_text())
        entry = credit["snapshots"][-1]
        as_of = datetime.fromisoformat(entry["as_of_at"])
        manifest = load_operational()(entry["snapshot_id"])
        run = {"data_snapshot_ref": entry["snapshot_id"], "as_of_at": as_of}
        ref = manifest["provider_evidence"][0]["evidence_ref"]
        proof = load_provider_resolver(entry["snapshot_id"])(ref)
        self.assertEqual(proof["evidence_ref"], ref)
        self.assertLessEqual(proof["verified_at"], as_of)
        case = deepcopy(manifest)
        case["provider_evidence"][0]["capacity_total"] += 1
        with self.assertRaisesRegex(ValueError, "independent provider proof"):
            select_historical_operational(case, run)
        case = deepcopy(manifest)
        case["provider_evidence"][0]["issued_at"] = (
            as_of + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "future or unordered provider"):
            select_historical_operational(case, run)
        case = deepcopy(manifest)
        case["provider_evidence"] = case["provider_evidence"][1:]
        with self.assertRaisesRegex(ValueError, "independent provider proof"):
            select_historical_operational(case, run)
        case = deepcopy(manifest)
        binding = next(row for row in case["digital_capacity"]
                       if row["commitment_status"] == "binding")
        binding["snapshot_at"] = (as_of + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "future"):
            select_historical_operational(case, run)

    def test_reader_full_term_proof_when_dependency_available(self):
        try:
            from phase1c_reader import _digital_proof
        except ModuleNotFoundError as exc:
            self.skipTest(f"reader dependency {exc.name} available in full PostgreSQL CI")
        entry = json.loads((HERE / INDEX).read_text())["snapshots"][-1]
        as_of = datetime.fromisoformat(entry["as_of_at"])
        manifest = load_operational()(entry["snapshot_id"])
        pool = next(row for row in manifest["digital_capacity"]
                    if row["commitment_status"] == "binding")
        typed = select_historical_operational(manifest, {
            "data_snapshot_ref": entry["snapshot_id"], "as_of_at": as_of})
        selected = next(row for row in typed["digital_capacity"]
                        if row["digital_capacity_id"] == pool["digital_capacity_id"])
        line = {"requested_activation_date": as_of.date() + timedelta(days=3)}
        deal = {"terms_json": {"contract_months": 12}}
        resolver = load_provider_resolver(entry["snapshot_id"])
        self.assertTrue(_digital_proof(selected, line, deal, as_of, resolver))
        self.assertFalse(_digital_proof(selected, line, deal, as_of, None))
        line["requested_activation_date"] = as_of.date() + timedelta(days=600)
        self.assertFalse(_digital_proof(selected, line, deal, as_of, resolver))


if __name__ == "__main__":
    unittest.main()
