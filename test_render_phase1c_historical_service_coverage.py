"""Synthetic service eligibility includes explicit negatives and unknown regions."""

import json
from pathlib import Path
import unittest

import yaml

from render_phase1c_historical_service_coverage import (
    build, COVERED, HERE, OUTPUT, UNSUPPORTED)


class HistoricalServiceCoverageTests(unittest.TestCase):
    def test_coverage_is_deterministic_and_bounded(self):
        portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
        config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        sql = build(portfolio, contract, config)
        self.assertEqual(sql, OUTPUT.read_text())
        self.assertEqual(sql.count("HIST-SERVICE-"), 242)
        self.assertEqual(set(COVERED), {"DE", "NL", "BE"})
        self.assertEqual(len(UNSUPPORTED), 3)
        self.assertNotIn("FR-IDF", sql)
        self.assertNotIn("AT-9", sql)
        self.assertIn("DE-BY", sql)
        self.assertIn("NL-NB", sql)
        self.assertIn("BE-WAL", sql)
        self.assertNotIn("service_slot", sql)


if __name__ == "__main__":
    unittest.main()
