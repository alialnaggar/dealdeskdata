"""Check dated stock/lane source coverage and replay cutoff isolation."""

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

import yaml

from phase1c_historical_operational import select_historical_operational
from render_phase1c_historical_stock_lanes import build, encode, load_resolver, INDEX


HERE = Path(__file__).resolve().parent


class HistoricalStockLaneTests(unittest.TestCase):
    def test_rebuild_and_all_registered_views(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
        credit = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
        files, index = build(portfolio, config, contract, credit)
        self.assertEqual(encode(index), (HERE / INDEX).read_text())
        for name, content in files.items():
            self.assertEqual(content, (HERE / name).read_text())
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), index["source_sha256"][name])
        stocks = [p for name, content in files.items() if "stock_source" in name
                  for p in json.loads(content)["products"]]
        self.assertEqual(len(stocks), 48)
        self.assertEqual(Counter(p["state_at_generation"] for p in stocks),
                         {"healthy": 7, "tight": 3, "below_reorder": 1,
                          "zero_available": 1, "component": 36})
        self.assertTrue(all(len(p["daily"]) == 185 for p in stocks))
        self.assertTrue(all(0 <= allocated <= on_hand for p in stocks
                            for on_hand, allocated in p["daily"]))
        lanes = json.loads(files["phase1c_historical_lane_source.json"])["lanes"]
        self.assertEqual(len(lanes), 38)
        self.assertEqual(len({(x["origin_location_id"], x["destination_region"]) for x in lanes}), 38)
        offers = json.loads(files["phase1c_historical_offer_source.json"])["offers"]
        self.assertEqual(len({x["product_id"] for x in offers}), 54)
        self.assertEqual(len(offers), 162)
        resolver = load_resolver()
        for entry in index["snapshots"]:
            view = resolver(entry["snapshot_id"])
            typed = select_historical_operational(view, {"data_snapshot_ref": entry["snapshot_id"],
                                                   "as_of_at": datetime.fromisoformat(entry["as_of_at"])})
            self.assertEqual(len(typed["inventory"]), 48)
            self.assertEqual(len(typed["shipping_lanes"]), 38)
            self.assertTrue(all(0 <= (datetime.fromisoformat(entry["as_of_at"]) - row["snapshot_at"]).total_seconds() < 86400
                                for row in typed["inventory"]))
            self.assertEqual(sum(len(typed[t]) for t in (
                    "production_capacity", "digital_capacity")), 0)
            self.assertTrue(all(row["observed_at"] <= datetime.fromisoformat(entry["as_of_at"])
                                for row in typed["inbound_supply"]))
            self.assertTrue(all(row["valid_from"] <= datetime.fromisoformat(entry["as_of_at"]).date()
                                for row in typed["supplier_offers"]))

    def test_unregistered_cutoff_rejected(self):
        with self.assertRaises(ValueError):
            load_resolver()("TODAY")


if __name__ == "__main__":
    unittest.main()
