"""Historical operational replay must reject live/future and unproved facts."""

from copy import deepcopy
from datetime import datetime, timezone
import unittest

from phase1c_historical_operational import TABLES, select_historical_operational


RUN = {"data_snapshot_ref": "HIST-CREDIT-0001",
       "as_of_at": datetime(2026, 3, 1, 9, tzinfo=timezone.utc)}
EMPTY = {"schema_version": 1, "snapshot_id": "HIST-CREDIT-0001",
         "as_of_at": "2026-03-01T09:00:00Z", "complete": True,
         "inbound_evidence": [], "purchase_order_evidence": [],
         **{table: [] for table in TABLES}}


class HistoricalOperationalTests(unittest.TestCase):
    def test_complete_empty_view_is_explicitly_unknown(self):
        result = select_historical_operational(EMPTY, RUN)
        self.assertEqual({key: len(rows) for key, rows in result.items()},
                         {table: 0 for table in TABLES})

    def test_missing_wrong_and_future_views_fail_closed(self):
        for change in ({"complete": False}, {"snapshot_id": "TODAY"},
                       {"as_of_at": "2026-03-02T09:00:00Z"}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    select_historical_operational(dict(EMPTY, **change), RUN)
        with self.assertRaises(ValueError):
            select_historical_operational(dict(EMPTY, shipping_lanes=None), RUN)
        future = deepcopy(EMPTY)
        future["inventory"].append({"inventory_id": "FUTURE", "product_id": "P",
                                     "location_id": "WH-EU-CENTRAL", "quantity_on_hand": 1,
                                     "quantity_allocated": 0, "snapshot_at": "2026-03-02T08:00:00Z"})
        with self.assertRaisesRegex(ValueError, "future"):
            select_historical_operational(future, RUN)

    def test_undated_or_future_shipping_lane_rejected(self):
        lane = {"lane_id": "L1", "is_active": True,
                "origin_location_id": "WH-EU-CENTRAL", "origin_time_zone": "Europe/Berlin",
                "destination_country_code": "DE", "destination_region": "DE-NW",
                "shipping_service_code": "standard", "cutoff_local_time": "16:00:00",
                "dispatch_weekdays_json": [1, 2, 3, 4, 5], "transit_workdays": 2,
                "effective_from": "2026-02-01T00:00:00Z",
                "expires_at": "2026-04-01T00:00:00Z"}
        for updates in ({}, {"verified_at": "2026-03-02T00:00:00Z"},
                        {"verified_at": "2026-02-01T00:00:00Z",
                         "effective_from": "2026-03-02T00:00:00Z"}):
            case = deepcopy(EMPTY)
            case["shipping_lanes"] = [dict(lane, **updates)]
            with self.assertRaises(ValueError):
                select_historical_operational(case, RUN)
        case = deepcopy(EMPTY)
        case["shipping_lanes"] = [dict(lane, verified_at="2026-02-01T00:00:00Z")]
        self.assertEqual(len(select_historical_operational(case, RUN)["shipping_lanes"]), 1)

    def test_no_po_receipt_requires_matching_independent_proof(self):
        row = {"supply_id": "R1", "purchase_order_id": None, "product_id": "P",
               "location_id": "WH-EU-CENTRAL", "quantity": 3, "quantity_allocated": 0,
               "expected_date": "2026-03-03", "status": "Confirmed",
               "confirmed_at": "2026-02-28T08:00:00Z", "observed_at": "2026-02-28T09:00:00Z",
               "valid_until": "2026-03-04T00:00:00Z", "evidence_ref": "PROOF-1"}
        case = deepcopy(EMPTY)
        case["inbound_supply"] = [row]
        with self.assertRaisesRegex(ValueError, "independent proof"):
            select_historical_operational(case, RUN)
        case["inbound_evidence"] = [{"evidence_ref": "PROOF-1",
            "source_class": "synthetic_supplier_manifest", "product_id": "P",
            "location_id": "WH-EU-CENTRAL", "quantity": 3,
            "expected_date": "2026-03-03", "issued_at": "2026-02-28T08:00:00Z",
            "confirmed_at": "2026-02-28T08:00:00Z",
            "valid_until": "2026-03-04T00:00:00Z"}]
        self.assertEqual(len(select_historical_operational(case, RUN)["inbound_supply"]), 1)
        case["inbound_evidence"][0]["quantity"] = 2
        with self.assertRaisesRegex(ValueError, "independent proof"):
            select_historical_operational(case, RUN)

    def test_po_receipt_requires_matching_dated_header(self):
        case = deepcopy(EMPTY)
        case["inbound_supply"] = [{"supply_id": "PO-R1", "purchase_order_id": "PO-1",
            "product_id": "P", "location_id": "WH-EU-CENTRAL", "quantity": 3,
            "quantity_allocated": 0, "expected_date": "2026-03-03", "status": "Confirmed",
            "confirmed_at": "2026-02-28T08:00:00Z", "observed_at": "2026-02-28T09:00:00Z",
            "valid_until": "2026-03-04T00:00:00Z", "evidence_ref": "PO-CONFIRM-1",
            "po_status": "Confirmed", "po_confirmed_at": "2026-02-28T08:00:00Z",
            "destination_location_id": "WH-EU-CENTRAL"}]
        with self.assertRaisesRegex(ValueError, "independent header"):
            select_historical_operational(case, RUN)
        case["purchase_order_evidence"] = [{"purchase_order_id": "PO-1",
            "status": "Confirmed", "confirmed_at": "2026-02-28T08:00:00Z",
            "issued_at": "2026-02-28T08:00:00Z",
            "destination_location_id": "WH-EU-CENTRAL"}]
        self.assertEqual(len(select_historical_operational(case, RUN)["inbound_supply"]), 1)
        case["purchase_order_evidence"][0]["destination_location_id"] = "WH-EU-WEST"
        with self.assertRaisesRegex(ValueError, "independent header"):
            select_historical_operational(case, RUN)


if __name__ == "__main__":
    unittest.main()
