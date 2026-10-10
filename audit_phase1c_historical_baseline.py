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
    "phase1c_historical_service_coverage.sql",
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
    gap_by_mode = Counter()
    for decision in decisions:
        mode_by_line = {line["line_id"]: line["mode"]
                        for line in decision["specialists"]["availability"]}
        for gap in decision["evidence_gaps"]:
            code, _, line_id = gap.partition(":")
            if line_id in mode_by_line:
                gap_by_mode[(code, mode_by_line[line_id])] += 1
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
        "evidence_gap_by_mode": [{"code": code, "mode": mode, "count": count}
                                 for (code, mode), count in sorted(gap_by_mode.items())],
        "fulfillment_counts": [{"mode": mode, "status": status, "count": count}
                               for (mode, status), count in sorted(fulfillment.items())],
        "records": records,
    }


def run(database_url):
    credit = load_credit()
    operational = load_operational()
    digital_resolver = load_digital()
    decisions = []
    mto = Counter()
    digital_counts = Counter()
    supplier_counts = Counter()
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
                        snapshot_id, resolver=digital_resolver),
                    commercial_rule_mode="compiled")
                if bundle["run"]["data_snapshot_ref"] != snapshot_id:
                    raise ValueError(f"run/snapshot mismatch: {n}")
                for line, fact in zip(bundle["lines"], bundle["facts"]["lines"]):
                    if line["fulfillment_mode"] == "supplier_finished":
                        product = line["product_id"]
                        status = fact.get("fulfillment_status", "absent")
                        receipts = [r for r in bundle["inbound_supply"] if r["product_id"] == product]
                        bindings = bundle["facts"]["supply"]["binding_receipts"].get(product, [])
                        offers = [o for o in bundle["supplier_offers"] if o["product_id"] == product]
                        supplier_counts[f"status:{status}"] += 1
                        supplier_counts[f"{status}:offer_{bool(offers)}"] += 1
                        supplier_counts[f"{status}:receipt_history_{bool(receipts)}"] += 1
                        supplier_counts[f"{status}:confirmed_history_{any(r['status'] == 'Confirmed' for r in receipts)}"] += 1
                        supplier_counts[f"{status}:binding_receipt_{bool(bindings)}"] += 1
                        if bindings:
                            supplier_counts[f"{status}:binding_free_ge_demand_{any(r['free'] >= line['quantity'] for r in bindings)}"] += 1
                    if line["fulfillment_mode"] == "digital_activation":
                        finding = fact.get("digital", {})
                        status = finding.get("status", "absent")
                        digital_counts[f"status:{status}"] += 1
                        if status in ("binding_candidate", "unknown"):
                            pools = finding.get("pools", [])
                            digital_counts[f"{status}:pool_{'present' if pools else 'absent'}"] += 1
                            if pools:
                                digital_counts[f"{status}:fresh_{any(p['fresh'] for p in pools)}"] += 1
                                digital_counts[f"{status}:proof_{any(p['full_term_verified'] for p in pools)}"] += 1
                                digital_counts[f"{status}:capacity_{any(p['free'] >= finding['concurrent_demand'] for p in pools)}"] += 1
                                digital_counts[f"{status}:on_time_{any(p['activation_by_request'] for p in pools)}"] += 1
                    if line["fulfillment_mode"] == "make_to_order":
                        mto["lines"] += 1
                        if any(b["finished_product_id"] == line["product_id"]
                               and b["configuration_signature_json"] == line["configuration_json"]
                               for b in bundle["bom"]):
                            mto["matching_bom"] += 1
                        if fact.get("selected_bom_id"):
                            mto["selected_bom"] += 1
                        mto[f"production:{fact.get('production_status', 'absent')}"] += 1
                        if fact.get("production_unknown_reason"):
                            mto[f"unknown:{fact['production_unknown_reason']}"] += 1
                decisions.append(assemble_deal_decision(bundle))
        finally:
            conn.rollback()
    result = summarize(decisions)
    result["make_to_order_diagnostics"] = dict(sorted(mto.items()))
    result["digital_diagnostics"] = dict(sorted(digital_counts.items()))
    result["supplier_finished_diagnostics"] = dict(sorted(supplier_counts.items()))
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
                      "evidence_gap_counts": report["evidence_gap_counts"],
                      "evidence_gap_by_mode": report["evidence_gap_by_mode"],
                      "fulfillment_counts": report["fulfillment_counts"],
                      "make_to_order_diagnostics": report["make_to_order_diagnostics"],
                      "digital_diagnostics": report["digital_diagnostics"],
                      "supplier_finished_diagnostics": report["supplier_finished_diagnostics"]}, sort_keys=True))


if __name__ == "__main__":
    main()
