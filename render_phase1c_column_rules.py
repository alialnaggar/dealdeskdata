"""Render field-level YAML contract as readable Markdown."""

from pathlib import Path
import argparse
import yaml


def render(contract):
    total = sum(len(columns) for columns in contract["tables"].values())
    lines = [
        "# Phase 1C field-by-field calibration rules",
        "",
        f"**4 October 2026 · pre-generation draft · {len(contract['tables'])} tables, {total} columns**",
        "",
        "This is the readable view of phase1c_column_rules.yaml in the "
        "[draft GitHub branch](https://github.com/alialnaggar/dealdeskdata/tree/phase1c-reader-draft). "
        "schema.sql determines column names, SQL types, nullability and database constraints. "
        "Each row adds a generation/source rule and a validation rule. A written rule does not "
        "prove that a generator or row validator exists. No full dataset has been generated.",
        "",
        "**Basis codes:** SYS = generated ID/observation; SYN = fictional-company assumption; "
        "CAT = catalogue taxonomy/visible price anchor adapted to brand-neutral SKUs; "
        "OBS = transformed Olist shape, not copied rows or B2B norms; CFG = chosen config/policy; "
        "DER = computed from other facts; SUB = submitted input sampled synthetically. "
        "Microsoft's fictional samples support structural and calculation patterns, not empirical rates.",
        "",
        "SQL requiredness, uniqueness, FKs, checks and triggers also apply. A **Review** mark means "
        "an executable generation or validation choice is still open. The checker verifies exact "
        "column coverage and SQL shape; it cannot certify the prose or empirical realism.",
        "The companion phase1c_data_contract.yaml now fixes the synthetic geography, location/time-zone, "
        "weekday/calendar, industry/country mix, structured deal/evidence JSON and agent-output contract. "
        "This closes the vocabulary and shape definitions; row generation and full validator execution remain pending.",
        "",
        "## Cross-field and cross-table relationships",
        "",
        "1. Catalogue version, type, billing unit, fulfillment mode and stock unit agree. Quoted SKUs are "
        "active and sellable. Price anchors use comparable units/terms; assembly cost follows components, "
        "scrap, labor and overhead independently of quote discount.",
        "2. Offered configurations have one active effective BOM and compatible options. Shared components "
        "aggregate across deal lines. Ordered operations consume matching capability/day hours; feasible "
        "capacity remains unreserved.",
        "3. Offers are conditional. Only valid confirmed inbound and free quantities support a physical "
        "path. PO, product, location and dates agree; dispatch cutoff and transit determine customer arrival.",
        "4. Digital full-term billed units convert to concurrent demand. Independent proof matches product, "
        "provider (including internal/null), configuration, region, term, unit, total, allocation, binding "
        "state and dates. A reference string alone is not proof.",
        "5. Credit exposure is open AR plus distinct dated unbilled commitments plus the proposal. Compute "
        "line/deal discount and margin independently, then apply complete versioned policy and review routes.",
        "6. Evidence exists at or before run as-of. Submitted inputs and run context are immutable. Historical "
        "outcomes and evaluation answers are excluded from agent-visible inputs.",
        "7. Generate coherent facts first, inject declared conflicts into causal facts, preserve unrelated "
        "invariants and independently recompute findings. Test quotas are coverage design, not prevalence.",
        "",
        "**Delivery limit:** Olist's consumer actual-delivery rate cannot be an actual-delivery target here: "
        "this schema has no delivered event/date. We can validate requested-date feasibility. Historical "
        "credit replay likewise needs frozen evidence at each decision, not today's single profile.",
        "",
        "## Field ledger",
        "",
    ]
    for table, columns in contract["tables"].items():
        lines += [
            f"### {table} ({len(columns)} columns)",
            "",
            "| Column | SQL type / null | Basis | Value or generation rule | How to judge it | State |",
            "|---|---|---|---|---|---|",
        ]
        for name, row in columns.items():
            values = [
                name,
                f"{row['sql_type']} / {'nullable' if row['nullable'] else 'required'}",
                row["basis"], row["generation"], row["validation"],
                "**Review**" if row.get("review_before_generation") else "Draft rule",
            ]
            lines.append("| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in values) + " |")
        lines.append("")
    lines += ["## Open field decisions (generation blocked)", ""]
    for table, columns in contract["tables"].items():
        for name, row in columns.items():
            if row.get("review_before_generation"):
                lines.append(f"- {table}.{name}: {row['review_before_generation']}")
    lines += [
        "",
        "## Closure before generation",
        "",
        "Resolve marked fields with typed executable rules. Verify price/source provenance, freeze geography "
        "and calendar vocabularies, prove BOM/configuration coverage, define independent evidence manifests "
        "and historical snapshots, close agent-facing JSON and output contracts, and set achieved "
        "distribution tolerances. The 1–8 historical lines/deal weights and 2.8–3.2 mean tolerance are "
        "already configured. Keep actual delivery lateness out of achieved statistics.",
        "",
        "Then pilot SQL integrity, cross-row chronology/arithmetic, distributions, independent deal decisions, "
        "reproducibility and answer isolation. The 14 reference scenarios check selected mechanics, not "
        "the full generated dataset.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = yaml.safe_load(Path(__file__).with_name("phase1c_column_rules.yaml").read_text(encoding="utf-8"))
    args.output.write_text(render(contract), encoding="utf-8")


if __name__ == "__main__":
    main()
