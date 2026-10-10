from pathlib import Path
import unittest

import yaml

from validate_phase1c_runtime_outputs import validate_execution_rows


HERE = Path(__file__).resolve().parent
CONTRACT = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())


def row():
    return {"run_id": "RUN-1", "agent_name": "Pricing", "attempt_number": 1,
            "status": "Success", "input_snapshot_json": {"deal_id": "D-1"},
            "output_json": {"agent_name": "Pricing", "status": "supported", "findings": [{
                "code": "PRICE-OK", "severity": "info", "message": "Within policy",
                "evidence_refs": ["PRICE-1"]}]}}


class RuntimeOutputTests(unittest.TestCase):
    def test_typed_success_and_evidence_pass(self):
        self.assertEqual(validate_execution_rows([row()], CONTRACT,
                                                  known_evidence={"PRICE-1"})["errors"], [])

    def test_outcome_leakage_and_unknown_evidence_fail(self):
        bad = row()
        bad["input_snapshot_json"]["expected_status"] = "supported"
        errors = validate_execution_rows([bad], CONTRACT, known_evidence=set())["errors"]
        self.assertTrue(any("outcome key" in e for e in errors))
        self.assertTrue(any("unknown evidence" in e for e in errors))

    def test_status_output_pairing_and_agent_identity_fail(self):
        bad = row()
        bad["status"] = "Failed"
        bad["output_json"]["agent_name"] = "Credit"
        errors = validate_execution_rows([bad], CONTRACT)["errors"]
        self.assertTrue(any("cannot carry output" in e for e in errors))
        self.assertTrue(any("differs" in e for e in errors))

    def test_duplicate_attempt_is_rejected(self):
        errors = validate_execution_rows([row(), row()], CONTRACT)["errors"]
        self.assertTrue(any("duplicate" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
