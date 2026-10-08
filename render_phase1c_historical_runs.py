"""Link staged historical submissions to registered credit/AR cutoffs.

Queued runs carry no decisions, output logs, or operational proof claims.
"""

import hashlib
import json
from pathlib import Path

from render_phase1c_vertical_pilot import insert


HERE = Path(__file__).resolve().parent
PREFIX = "phase1c_historical_run_rows_"


def build(index, config_hash):
    if len(index["snapshots"]) != 400 or index["schema_version"] != 1:
        raise ValueError("historical cutoff registry drift")
    shards = ["-- Queued historical reads; credit/AR views are pinned, operational evidence pending.\n"
              "SET search_path TO deal_desk, public;\n" for _ in range(4)]
    for n, item in enumerate(index["snapshots"], 1):
        if (item["snapshot_id"] != f"HIST-CREDIT-{n:04d}" or
                item["customer_id"] != f"SYN-CUST-{(n-1)%80+1:03d}"):
            raise ValueError("historical cutoff is not aligned with deal/customer")
        deal = f"HIST-DEAL-{n:04d}"
        shards[(n-1)//100] += insert("deal_runs", dict(
            run_id=f"00000000-0000-4000-8000-{280000+n:012d}",
            deal_id=deal, original_policy_set_code="BASELINE_2026",
            applied_policy_set_code="BASELINE_2026",
            catalog_version_used="CATALOGUE_2026_V1",
            as_of_at=item["as_of_at"], data_snapshot_ref=item["snapshot_id"],
            input_snapshot_json={}, config_hash=config_hash,
            run_status="queued", started_at=item["as_of_at"]))
    return shards


def main():
    index = json.loads((HERE / "phase1c_historical_credit_index.json").read_text())
    config_hash = hashlib.sha256((HERE / "calibration_config.yaml").read_bytes()).hexdigest()
    for n, output in enumerate(build(index, config_hash), 1):
        (HERE / f"{PREFIX}{n:02d}.sql").write_text(output)
    print("Rendered 400 queued historical run rows")


if __name__ == "__main__":
    main()
