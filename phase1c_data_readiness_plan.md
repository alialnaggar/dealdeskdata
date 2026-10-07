# Phase 1C — path to usable synthetic data

**Working plan, 7 October 2026.** The current PostgreSQL reader and decision
tests cover the 24-table design and all 24 proposed build variants, but there
is no generated operational dataset. `ready_for_generation` is still false:
four calibration review items and 22 field-level review marks remain open.
All portfolio identities, prices, costs and operating quantities are
synthetic drafts. This plan keeps that distinction visible through delivery.

## Outcome and scope

The deliverable is a reproducible, versioned synthetic dataset that the six
agents and Orchestrator can read in PostgreSQL, plus a separate hidden
evaluation set with independently authored expected findings. Its initial
targets are 156 products (120 sellable and 36 components), 18 buildable
products with 24 offered BOMs, 80 customers, 400 historical deals and 100
generated test deals. The evaluation-case count is chosen from a scenario
matrix before the final run, not guessed from the 100 test deals. The existing
seed is `22495`. Targets and tolerance decisions remain provisional until
the freeze described below.

"Ready for use" means a clean rebuild from the pinned configuration and
seed, a database import, passing integrity and reader checks, an achieved
distribution report against explicit tolerances, evidence provenance, and
separated evaluation answer keys. It does not mean live supplier commitments,
real customers, or completed six-agent execution. `agent_execution_log` and
other genuine runtime output are written by actual test/agent runs, rather
than fabricated as source facts to fill a table.

## Critical path

| Stage | Work and artifact | Exit check |
| --- | --- | --- |
| 1. Freeze a **pilot contract** | Pin current schema, field ledger, config, seed and data provenance in a run manifest. Write an explicit scenario matrix for stocked, supplier-finished, assembled, digital and service lines; include confirmed, conditional, unknown, revision and policy/credit cases. Define evaluation count and per-scenario minimums. Keep unresolved values tagged `provisional`. | Every generated field has a rule or an explicit open decision; scenario matrix covers each fulfillment path and each material decision state. |
| 2. Build one vertical slice | Implement one deterministic Python generator with separate modules for masters, operational facts, customer history, submissions and evidence. In dependency order: products/BOMs/compatibility and offers; POs/inbound, stock, capacity, digital and shipping evidence; customers, as-of AR and commitments; immutable deals/runs. Load roughly 10–20 varied pilot deals into disposable PostgreSQL, with all five fulfillment paths represented. | Clean import; PK/FK, types, uniqueness and allocation constraints pass; existing readers and deal gate produce evidence-backed outcomes on the pilot. Re-running the same seed produces identical rows and manifest hashes. |
| 3. Calibrate and close evidence **while stage 2 runs** | Source representative component archetypes and comparable dated price configurations, then check cross-kit interfaces, quantities, slots, power and material thermal limits for all 24 BOMs. Reconcile the €1,050 workstation / 31.90% draft margin against the proposed 28% p90. Verify the Olist mirror against its canonical source or exclude its derived rates. Decide how leads beyond the 30-day represented capacity horizon are labeled. Review the 36-component/156-product mix now that structural BOM coverage has passed. Resolve the 22 field marks with tests and evidence, or document bounded synthetic assumptions. | Four calibration items and 22 field marks are dispositioned; no unverified public-derived rate is represented as an enterprise statistic; every offered BOM has a checked compatibility basis and every commercial band has a comparable unit/date/tax basis or an explicitly synthetic label. User reviews the compact decision sheet before final freeze. |
| 4. Stress the pilot and freeze | Generate a larger mixed pilot (about 30–50 deals). Check as-of chronology, stale/absent proof, cancelled or allocated supply, shared material and capacity contention, cost rollups, credit exposure, and decision labels. Produce distribution diagnostics for deal lines, categories, popularity, modes, dates, credit, supply and outcomes. Correct rules or targets, then freeze config, scenario matrix, tolerances and source manifest. | No leakage of expected decisions into input rows; independent answer-key authoring; all material negative cases fail as intended; achieved pilot metrics are within documented pilot tolerances or an approved explicit exception. Both generation validators change to ready only after their real gates pass. |
| 5. Generate and release | Run the frozen generator with seed `22495` for the 80/400/100 targets and the frozen evaluation matrix. Import into a fresh PostgreSQL database, run schema/contract, calibration, relationship, evidence, chronology, replay and distribution checks in CI, then package the data, SQL/load instructions, manifest, checksums and validation report. Keep hidden evaluation inputs and keys outside agent-visible data. | Fresh import and repeat run agree by checksum; all blocking checks pass; achieved distributions and any documented deviations are in the report; agents can read the data and produce real run logs. Tag the dataset version and freeze its configuration. |

Stages 2 and 3 overlap. A provisional pilot is useful for engineering without
turning the draft numbers into final calibration. Stage 5 waits for the stage
3/4 freeze, because changing price, fit or evidence rules afterward would
make the released rows and answer keys inconsistent.

## Work queue and decisions

The implementation work is the generator, provenance manifest, independent
scenario/answer-key builder, PostgreSQL loader, validation report and CI
gate. The review package should contain only the material choices: component
archetype/fit basis, comparable price and cost bands (including the
workstation outlier), treatment of the unverified Olist metric, horizon
labeling, and any target/tolerance revisions. Existing approvals already
settled the synthetic strategy, local workshop model and same-price paired
technical alternatives; these are not being reopened.

At each stage, record the command, seed, commit, row counts, achieved metrics,
failed checks and remaining blockers in this file or a linked run report.
Treat a pilot as **development usable** after stage 2. Treat the dataset as
**evaluation usable** only after stage 5. The immediate next work item is
the scenario matrix and deterministic 10–20-deal vertical generator; the
evidence review can proceed in parallel.

## Progress — 7 October 2026

Stage 1's provisional coverage contract is now executable. The matrix has 18
scenario archetypes across all five fulfillment modes and credit, pricing and
policy conflicts. It specifies one case per archetype for an 18-deal pilot and
two independently reviewed variants per archetype for a 36-case evaluation
target. `validate_phase1c_scenario_matrix.py` checks the seed and baseline
against calibration, coverage, counts, and answer-key isolation. Its manifest
pins hashes of the schema, calibration, field and JSON contracts, portfolio,
cost draft and matrix. These are targets, not generated rows or validated
outcomes. Stage 2's vertical data generator remains the next implementation
step; the four calibration and 22 field reviews remain open.
