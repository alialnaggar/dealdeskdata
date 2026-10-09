"""Read all provisional historical runs without writing decisions to source data.

Requires the schema and compiled policy rows in a disposable PostgreSQL
database. Masters, submitted deals and queued runs are loaded in one rolled
back transaction. The output is a diagnostic, not an evaluation answer key.
"""

import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re

import psycopg

from phase1c_deal_decision import assemble_deal_decision
from phase1c_reader import read_run
from render_phase1c_historical_credit import load_resolver as load_credit
from render_phase1c_historical_digital import (
    load_provider_resolver, load_resolver as load_digital)
from render_phase1c_historical_stock_lanes import load_resolver as load_operational

HERE = Path(__file__).resolve().parent
INPUTS = [
    "phase1c_buildable_master.sql",
    "phase1c_sellable_catalogue.sql",
    "phase1c_customer_master.sql",
    *[f"phase1c_historical_inputs_{n:02d}.sql" for n in range(1, 9)],
    *[f"phase1c_historical_run_rows_{n:02d}.sql" for n in range(1, 5)],
]


def load_inputs(conn):
    conn.execute("SET search_path TO deal_desk, public")
    for name in INPUTS:
        sql = (HERE / name).read_text()
        for statement in re.findall(r"^(?:INSERT INTO|UPDATE deals SET) .*?;",
                                    sql, re.M | re.S):
            conn.execute(statement)
    conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    rows = conn.execute("""SELECT count(*) FROM deal_desk.deals
                           WHERE dataset_type='historical'""").fetchone()[0]
    runs = conn.execute("""SELECT count(*) FROM deal_desk.deal_runs r
             JOIN deal_desk.deals d USING (deal_id)
             WHERE d.dataset_type='historical' AND r.run_status='queued'""").fetchone()[0]
    if (rows, runs) != (400, 400):
        raise ValueError(f"historical input/run count drift: {(rows, runs)}")
    policy = [conn.execute(f"SELECT count(*) FROM deal_desk.{table} "
                           "WHERE policy_set_code='BASELINE_2026'").fetchone()[0]
              for table in ("pricing_rules", "policy_rules", "approval_rules")]
    if any(count == 0 for count in policy):
        raise ValueError("compiled baseline policy missing")


def summarize(decisions):
    if len(decisions) != 400 or len({d["deal_id"] for d in decisions}) != 400:
        raise ValueError("historical baseline did not cover 400 unique deals")
    status_counts = Counter(d["status"] for d in decisions)
    gap_counts = Counter(gap.split(":")[0] for d in decisions
                         for gap in d["evidence_gaps"])
    fulfillment = Counter((item["mode"], item["status"]) for d in decisions
                          for item in d["specialists"]["availability"])
    records = []
    for d in decisions:
        records.append({
            "deal_id": d["deal_id"], "run_id": str(d["run_id"]),
            "as_of_at": d["as_of_at"].isoformat(),
            "status": d["status"],
            "block_codes": [b.get("code") or b.get("rule_id") for b in d["blocks"]],
            "revision_codes": [r["code"] for r in d["revision_reasons"]],
            "evidence_gaps": d["evidence_gaps"],
            "uncommitted_codes": [p["code"] for p in d["uncommitted_paths"]],
            "fulfillment_statuses": [{"mode": line["mode"], "status": line["status"]}
                                     for line in d["specialists"]["availability"]],
        })
    records.sort(key=lambda x: x["deal_id"])
    return {
        "schema_version": 1, "provenance": "provisional_diagnostic_baseline",
        "not_agent_input": True, "not_independent_evaluation_key": True,
        "historical_deals": len(decisions),
        "status_counts": dict(sorted(status_counts.items())),
        "evidence_gap_counts": dict(sorted(gap_counts.items())),
        "fulfillment_counts": [{"mode": mode, "status": status, "count": count}
                               for (mode, status), count in sorted(fulfillment.items())],
        "records": records,
    }


def run(database_url):
    credit = load_credit()
    operational = load_operational()
    digital = load_digital()
    decisions = []
    with psycopg.connect(database_url) as conn:
        try:
            load_inputs(conn)
            for n in range(1, 401):
                run_id = f"00000000-0000-4000-8000-{280000+n:012d}"
                snapshot_id = f"HIST-CREDIT-{n:04d}"
                bundle = read_run(
                    conn, run_id, historical_credit_resolver=credit,
                    historical_operational_resolver=operational,
                    digital_evidence_resolver=load_provider_resolver(
                        snapshot_id, resolver=digital),
                    commercial_rule_mode="compiled")
                if bundle["run"]["data_snapshot_ref"] != snapshot_id:
                    raise ValueError(f"run/snapshot mismatch: {n}")
                decisions.append(assemble_deal_decision(bundle))
        finally:
            conn.rollback()
    result = summarize(decisions)
    result["source_sha256"] = {
        name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        for name in ("calibration_config.yaml", "phase1c_historical_credit_index.json",
                     "phase1c_historical_inbound_index.json",
                     "phase1c_historical_operational_index.json",
                     "phase1c_historical_capacity_index.json",
                     "phase1c_historical_digital_index.json")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    report = run(os.environ["DATABASE_URL"])
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"historical_deals": report["historical_deals"],
                      "status_counts": report["status_counts"],
                      "evidence_gap_counts": report["evidence_gap_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
