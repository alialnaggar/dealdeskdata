"""Check scenario coverage and output isolation before pilot row generation."""

import argparse
import hashlib
import json
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
MODES = {"stocked_finished", "supplier_finished", "make_to_order",
         "digital_activation", "scheduled_service", "cross_cutting"}
BUCKETS = {"feasible_uncommitted", "revision", "unknown", "commercial_exception"}
SOURCES = ("schema.sql", "calibration_config.yaml", "phase1c_column_rules.yaml",
           "phase1c_data_contract.yaml", "phase1c_portfolio_draft.json",
           "phase1c_build_cost_draft.json", "phase1c_scenario_matrix.yaml")


def validate(matrix, config):
    errors = []
    cases = matrix.get("archetypes")
    if not isinstance(cases, list) or not cases:
        return ["archetypes must be a nonempty list"]
    if matrix.get("random_seed") != config.get("random_seed"):
        errors.append("seed differs from calibration config")
    if matrix.get("catalog_version") != config["dataset"]["catalog_version"]:
        errors.append("catalogue differs from calibration config")
    if matrix.get("policy_set_code") != config["dataset"]["historical_policy_set_code"]:
        errors.append("pilot policy differs from baseline")
    if matrix.get("status") != "pilot_design_provisional":
        errors.append("scenario matrix must retain provisional status until freeze")
    pilot, evaluation = matrix.get("pilot", {}), matrix.get("evaluation", {})
    if pilot.get("dataset_type") != "generated_test" or not pilot.get("one_deal_per_archetype"):
        errors.append("pilot must contain one generated_test deal per archetype")
    if pilot.get("target_deals") != len(cases):
        errors.append("pilot count must equal the number of archetypes")
    variants = evaluation.get("variants_per_archetype")
    if type(variants) is not int or variants < 2 or evaluation.get("target_cases") != len(cases) * variants:
        errors.append("evaluation target must give at least two cases per archetype")
    if not evaluation.get("separate_output") or evaluation.get("answer_keys_agent_visible") is not False:
        errors.append("evaluation answer keys must stay outside agent-visible output")
    if evaluation.get("oracle_rule") != "independently_review_expected_findings_from_frozen_facts":
        errors.append("evaluation oracle must be independent of the agent decision")
    ids, modes, buckets = set(), set(), set()
    required = {"id", "mode", "setup", "check", "target_bucket"}
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != required:
            errors.append(f"archetypes[{i}]: expected only {sorted(required)}")
            continue
        if not all(isinstance(case[k], str) and case[k] for k in required):
            errors.append(f"archetypes[{i}]: every value must be nonempty text")
            continue
        if case["id"] in ids:
            errors.append(f"duplicate archetype {case['id']}")
        ids.add(case["id"])
        modes.add(case["mode"])
        buckets.add(case["target_bucket"])
        if any(key in case["setup"].lower() for key in ("expected_decision", "agent_output")):
            errors.append(f"{case['id']}: outcome leakage in setup")
    if modes != MODES:
        errors.append(f"mode coverage differs: missing={sorted(MODES - modes)}")
    if buckets != BUCKETS:
        errors.append(f"finding buckets differ: missing={sorted(BUCKETS - buckets)}")
    if not {"CREDIT-LIMIT", "PRICE-FLOOR", "POLICY-CLAUSE"}.issubset(ids):
        errors.append("pricing, credit and policy cross-cutting cases are required")
    return errors


def manifest(root, matrix):
    return {
        "schema_version": 1,
        "status": "pilot_design_provisional",
        "seed": matrix["random_seed"],
        "pilot_target_deals": matrix["pilot"]["target_deals"],
        "evaluation_target_cases": matrix["evaluation"]["target_cases"],
        "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                          for name in SOURCES},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="write a pinned pilot input manifest")
    args = parser.parse_args()
    matrix = yaml.safe_load((HERE / "phase1c_scenario_matrix.yaml").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    errors = validate(matrix, config)
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        raise SystemExit(1)
    result = manifest(HERE, matrix)
    if args.manifest:
        args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "source_sha256"}, indent=2))


if __name__ == "__main__":
    main()
