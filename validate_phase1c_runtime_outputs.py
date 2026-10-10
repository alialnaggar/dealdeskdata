"""Validate typed agent execution envelopes without judging business outcomes."""

from validate_phase1c_data_contract import validate_payload


LEAKAGE_KEYS = {"historical_decision", "decision_reason", "expected_status",
                "target_bucket", "oracle", "answer_key", "approved_by_roles"}


def validate_execution_rows(rows, contract, *, known_evidence=None):
    errors = []
    seen = set()
    evidence_check_enabled = known_evidence is not None
    known_evidence = known_evidence or set()
    allowed_agents = set(contract["controlled_vocabularies"]["agent_names"])
    for index, row in enumerate(rows):
        label = f"execution[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: row must be an object")
            continue
        key = (row.get("run_id"), row.get("agent_name"), row.get("attempt_number"))
        if key in seen:
            errors.append(f"{label}: duplicate run/agent/attempt")
        seen.add(key)
        if row.get("agent_name") not in allowed_agents:
            errors.append(f"{label}: invalid agent_name")
        if not isinstance(row.get("attempt_number"), int) or row["attempt_number"] < 1:
            errors.append(f"{label}: attempt_number must be positive")
        status = row.get("status")
        if status not in {"Running", "Success", "Failed", "Retried", "Skipped"}:
            errors.append(f"{label}: invalid execution status")
        input_snapshot = row.get("input_snapshot_json")
        if not isinstance(input_snapshot, dict):
            errors.append(f"{label}: input_snapshot_json must be an object")
        elif LEAKAGE_KEYS.intersection(input_snapshot):
            errors.append(f"{label}: input snapshot contains outcome key")
        output = row.get("output_json")
        if status == "Success" and not isinstance(output, dict):
            errors.append(f"{label}: successful execution needs output_json")
        if status in {"Running", "Failed", "Skipped"} and output is not None:
            errors.append(f"{label}: {status} execution cannot carry output_json")
        if output is not None:
            for error in validate_payload("agent_output", output, contract):
                errors.append(f"{label}: {error}")
            if output.get("agent_name") != row.get("agent_name"):
                errors.append(f"{label}: output agent_name differs from execution row")
            if evidence_check_enabled:
                for finding in output.get("findings", []):
                    for ref in finding.get("evidence_refs", []):
                        if ref not in known_evidence:
                            errors.append(f"{label}: output cites unknown evidence {ref}")
    return {"errors": errors, "count": len(rows), "ready_for_runtime_checks": not errors}
