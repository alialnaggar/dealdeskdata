"""Measure the 36-deal development pilot against compiled reader decisions.

Loads provisional SQL into one disposable transaction. The JSON is a CI
diagnostic artifact, not an agent-visible answer key or a calibration freeze.
"""

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

import psycopg

from phase1c_reader import read_run, load_provider_evidence
from phase1c_deal_decision import assemble_deal_decision

HERE = Path(__file__).resolve().parent
SOURCES = ("phase1c_buildable_master.sql", "phase1c_sellable_catalogue.sql",
           "phase1c_vertical_pilot.sql", "phase1c_conflict_pilot.sql",
           "phase1c_stress_pilot.sql")


def inspect(conn):
    resolver = load_provider_evidence(HERE / "phase1c_conflict_provider_manifest.json")
    ids = list(range(260001, 260019)) + list(range(270001, 270019))
    statuses, modes, categories, lines_per_deal = Counter(), Counter(), Counter(), Counter()
    source_use = Counter()
    rule_areas = Counter()
    as_of = Counter()
    for index in ids:
        bundle = read_run(conn, f"00000000-0000-4000-8000-{index:012d}",
                          digital_evidence_resolver=resolver,
                          cost_parameters={"workforce_cost_eur_per_hour": 30,
                                           "overhead_fraction": "0.1"},
                          commercial_rule_mode="compiled")
        decision = assemble_deal_decision(bundle)
        statuses[decision["status"]] += 1
        lines_per_deal[len(bundle["lines"])] += 1
        modes.update(line["fulfillment_mode"] for line in bundle["lines"])
        categories.update(line["category"] for line in bundle["lines"])
        as_of[bundle["run"]["as_of_at"].isoformat()] += 1
        rule_areas.update(hit["area"] for hit in decision["commercial_rule_hits"])
        source_use.update({source for finding in decision["specialists"]["availability"]
                           for source in finding["source_ids"]
                           if source.startswith(("PILOT-STOCK", "CONFLICT-STOCK", "STRESS-STOCK"))})
    line_count = sum(modes.values())
    if (sum(statuses.values()) != 36 or len(modes) != 5 or
            sum(int(k) * v for k, v in lines_per_deal.items()) != line_count):
        raise ValueError("Incomplete or inconsistent development pilot")
    return {"schema_version": 1, "scope": "provisional_development_pilot",
            "deal_count": len(ids), "line_count": line_count,
            "mean_lines_per_deal": str((Decimal(line_count) / len(ids)).quantize(Decimal("0.01"))),
            "lines_per_deal": {str(k): v for k, v in sorted(lines_per_deal.items())},
            "line_mode_counts": dict(sorted(modes.items())),
            "line_category_counts": dict(sorted(categories.items())),
            "decision_counts": dict(sorted(statuses.items())),
            "commercial_hit_area_counts": dict(sorted(rule_areas.items())),
            "as_of_counts": dict(sorted(as_of.items())),
            "shared_stock_source_count": sum(v > 1 for v in source_use.values()),
            "most_reused_stock_source_count": max(source_use.values(), default=0),
            "source_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                              for name in (*SOURCES, "calibration_config.yaml",
                                           "phase1c_scenario_matrix.yaml",
                                           "phase1c_conflict_provider_manifest.json")},
            "limitations": ["pilot_case_mix_is_not_a_target_distribution",
                            "read_only_runs_do_not_reserve_supply_across_deals",
                            "decision_counts_are_diagnostics_not_independent_oracle_labels"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL required")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("SET search_path TO deal_desk, public")
        try:
            for name in SOURCES:
                for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                            (HERE / name).read_text(), re.M | re.S):
                    conn.execute(statement)
            report = inspect(conn)
        finally:
            conn.rollback()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("deal_count", "line_count",
          "mean_lines_per_deal", "decision_counts", "shared_stock_source_count")},
          sort_keys=True))


if __name__ == "__main__":
    main()
