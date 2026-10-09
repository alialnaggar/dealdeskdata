"""Capacity must be reproducible, dated, complete and bounded to 30 days."""

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import unittest

import yaml

from phase1c_historical_operational import select_historical_operational
from render_phase1c_historical_capacity import build, encode, INDEX, SOURCE, load_resolver
from render_phase1c_historical_stock_lanes import load_resolver as load_operational

HERE = Path(__file__).resolve().parent


class HistoricalCapacityTests(unittest.TestCase):
    def test_reproducible_source_and_all_cutoffs(self):
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        source, index = build(config, credit)
        self.assertEqual(source, (HERE / SOURCE).read_text())
        self.assertEqual(encode(index), (HERE / INDEX).read_text())
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), index["source_sha256"])
        resolve = load_resolver()
        operational = load_operational()
        for entry in index["snapshots"]:
            cutoff = datetime.fromisoformat(entry["as_of_at"])
            rows = resolve(entry["snapshot_id"])
            self.assertEqual(len(rows), 180)
            self.assertEqual(len({(x["capacity_date"], x["capability_code"], x["resource_type"])
                                  for x in rows}), 180)
            self.assertTrue(all(datetime.fromisoformat(x["snapshot_at"]) <= cutoff and
                                cutoff - datetime.fromisoformat(x["snapshot_at"]) <= timedelta(hours=24)
                                and 0 <= x["allocated_capacity_hours"] <= x["available_capacity_hours"]
                                for x in rows))
            days = sorted({x["capacity_date"] for x in rows})
            self.assertEqual(len(days), 30)
            self.assertEqual(datetime.fromisoformat(days[-1]) -
                             datetime.fromisoformat(days[0]), timedelta(days=29))
            manifest = operational(entry["snapshot_id"])
            typed = select_historical_operational(manifest, {
                "data_snapshot_ref": entry["snapshot_id"], "as_of_at": cutoff})
            self.assertEqual(len(typed["production_capacity"]), 180)

    def test_future_capacity_snapshot_rejected(self):
        entry = json.loads((HERE / INDEX).read_text())["snapshots"][0]
        cutoff = datetime.fromisoformat(entry["as_of_at"])
        manifest = load_operational()(entry["snapshot_id"])
        case = deepcopy(manifest)
        case["production_capacity"][0]["snapshot_at"] = (
            cutoff + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "future"):
            select_historical_operational(case, {
                "data_snapshot_ref": entry["snapshot_id"], "as_of_at": cutoff})

    def test_digest_and_missing_day_fail_closed(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            for name in (SOURCE, INDEX, "phase1c_historical_credit_index.json"):
                (folder / name).write_bytes((HERE / name).read_bytes())
            (folder / SOURCE).write_text("{}")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_resolver(folder)
            (folder / SOURCE).write_bytes((HERE / SOURCE).read_bytes())
            data = json.loads((folder / SOURCE).read_text())
            data["rows"] = [row for row in data["rows"] if row[0] != "2026-03-01"]
            source = encode(data)
            (folder / SOURCE).write_text(source)
            index = json.loads((folder / INDEX).read_text())
            index["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
            (folder / INDEX).write_text(encode(index))
            with self.assertRaisesRegex(ValueError, "incomplete represented"):
                load_resolver(folder)(index["snapshots"][0]["snapshot_id"])


if __name__ == "__main__":
    unittest.main()
