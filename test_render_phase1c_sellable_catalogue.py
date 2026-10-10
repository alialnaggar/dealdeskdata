"""Check the first full-category PostgreSQL catalogue increment."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

import yaml

from render_phase1c_sellable_catalogue import product_rows, render


HERE = Path(__file__).resolve().parent


class SellableCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
        cls.costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
        cls.config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
        cls.contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())

    def test_five_modes_and_cost_boundaries(self):
        rows = product_rows(self.portfolio, self.costs, self.config, self.contract)
        self.assertEqual(len(rows), 102)
        self.assertEqual({row[12] for row in rows},
                         {"stocked_finished", "supplier_finished", "digital_activation",
                          "scheduled_service"})
        self.assertEqual(len({row[0] for row in rows}), 102)
        self.assertTrue(all(Decimal(row[7]) > Decimal(row[8]) >= 0 for row in rows))
        digital = [row for row in rows if row[12] == "digital_activation"]
        self.assertTrue(digital)
        self.assertTrue(all(row[10] in {"instance_month", "protected_tb_month", "licence_year"}
                            for row in digital))
        self.assertEqual(render(rows), (HERE / "phase1c_sellable_catalogue.sql").read_text())

    def test_missing_buildable_cost_is_rejected(self):
        draft = deepcopy(self.costs)
        draft["products"].pop()
        with self.assertRaisesRegex(ValueError, "unpriced buildable product"):
            product_rows(self.portfolio, draft, self.config, self.contract)

    def test_out_of_contract_attribute_is_rejected(self):
        draft = deepcopy(self.portfolio)
        first = next(p for p in draft["products"] if p["fulfillment_mode"] == "digital_activation")
        first["attributes_json"]["unreviewed_field"] = "x"
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            product_rows(draft, self.costs, self.config, self.contract)


if __name__ == "__main__":
    unittest.main()
