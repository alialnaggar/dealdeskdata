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
**evaluation usable** only after stage 5. The evidence review can proceed
in parallel with pilot engineering.

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

The first stage 2 master-data increment is `render_phase1c_sellable_catalogue.py`.
It renders 102 additional sellable products from the draft portfolio and
joins the existing 18 buildable products and 36 components in one disposable
PostgreSQL check. Every sellable fulfillment mode is present. Category price
draws use the configured p10/p50/p90 anchors and p50 synthetic cost margins;
these values are provisional and will be regenerated after sourcing review.
This is catalogue coverage, **not** the 18-deal pilot or operational data.
Next: independently generate supplier, stock, capacity, digital, shipping and
credit evidence, then the 18 scenario deals/runs on the 1 September 2026
configuration as-of date and read their results.

The catalogue integration exposed a digital reader mismatch before any pilot
deal was generated: monthly quantities and whole product attributes had been
assumed for every provider pool. The reader now derives concurrent demand for
monthly or annual billable units and compares only the declared digital
configuration identity (edition, tier and features). The provisional
catalogue uses pool-compatible `instance_month`, `protected_tb_month` and
`licence_year` units. Existing monthly reference checks and focused annual
unit tests pass; a connected rich-attribute digital row is still required
in the operational pilot.

## Progress — 8 October 2026

The reader and gate now treat `scheduled_service` as a bounded coverage check:
an explicit eligible region with a future requested date is conditional and
the service slot remains uncommitted; an ineligible region needs revision and
missing coverage needs evidence. There is no service-worker calendar or booked
appointment table, so the pilot must never claim a confirmed service slot.
The `SERVICE-COVERED` matrix bucket was corrected to
`conditional_uncommitted`.

`render_phase1c_vertical_pilot.py` now renders five source-connected
generated-test deals at the configured 1 September as-of date. The five
paths use catalogue rows, confirmed supplier inbound, fresh stock, dated
workshop capacity, a trusted digital provider manifest, explicit service
coverage, shipping and customer credit. It emits source evidence before the
deals and omits expected decisions from submitted rows. The output is a
disposable pilot fixture, not the intended 18-deal varied pilot or the full
dataset. PostgreSQL reader verification is the next gate, followed by the
13 remaining scenario archetypes and distribution checks.

[PostgreSQL Actions run 37770210410](https://github.com/alialnaggar/dealdeskdata/actions/runs/37770210410)
passed the full workflow, including the five generated deal reads and the
service coverage negative cases. The stock and confirmed inbound paths reach
dated delivery; the selected BOM reaches an uncommitted build path; the
separate provider proof confirms the digital term; and explicit service
coverage remains conditional until a slot is committed. The matrix's other
13 conflict cases are still designs, not generated rows.

## Eighteen-case source conflict pilot — 8 October 2026

`render_phase1c_conflict_pilot.py` adds 13 source-connected cases to the five
mode baselines, one for every archetype in the provisional matrix. Each case
has a separate generated-test submission and immutable run; the case-to-run
map stays in test code, outside submitted rows. The examples cover allocated
and stale stock, an uncommitted supplier offer, cancelled inbound, an
alternate BOM kit, stale capacity, a component ETA beyond the represented
capacity window, absent and partial-term digital proof, out-of-region service,
and credit, price and contract-clause exceptions. The partial-term provider
record is stored separately from the deal; a reference string alone never
confirms digital capacity.

[PostgreSQL Actions run 37771255791](https://github.com/alialnaggar/dealdeskdata/actions/runs/37771255791)
passed the full schema/load/reader/compiled-policy workflow with the five
baselines and 13 conflicts. This establishes an **18-deal development pilot**,
not a calibrated distribution or independent evaluation answer key. The
supplier-offer-only case is conditional operationally, but its final gate
needs evidence because a dated delivery commitment is absent. This makes
the matrix's `unknown` target a gate/evidence bucket, not a claim that no
offer exists. No outcome labels are in the agent-visible SQL.

Next: build the seeded 30–50-deal mixed stress pilot with shared capacity and
inventory contention, as-of replay, a provenance manifest and achieved
distribution report. In parallel, disposition the four calibration reviews
and 22 field marks; only then freeze tolerances, independently author the
36-case evaluation oracle, and generate the 80/400/100 release targets.

## Seeded 36-deal stress increment — 8 October 2026

`render_phase1c_stress_pilot.py` adds 18 seeded mixed deals and 47 lines to
the 18-archetype pilot. The added deals have eight two-line, nine three-line
and one four-line submissions; line mode counts are 11 stocked, nine
supplier-finished, nine make-to-order, ten digital and eight scheduled service.
`phase1c_stress_pilot_report.json` records seed `22531`, these achieved input
counts and SHA-256 of the rendered SQL. The added records use later source
snapshots, so the reader can replay earlier baseline decisions at their
original as-of timestamp. At least two runs cite the same stock source,
exposing the current read-only model's cross-deal reservation limit; the
intra-run build quantity cases also exercise capacity shortfall.

[PostgreSQL Actions run 37772292678](https://github.com/alialnaggar/dealdeskdata/actions/runs/37772292678)
passed the 36-deal SQL import, deterministic rendering, reader/gate checks,
as-of isolation and prior workflow. This is a development stress increment,
**not** an achieved calibrated business distribution. The input diagnostic is
versioned beside the generated SQL. A separate database audit now records
aggregate reader decisions and source hashes in a CI artifact: 36 deals,
65 total lines (mean 1.81), with nine `approval_required`, two `blocked`,
12 `needs_commitment`, nine `needs_evidence` and four `needs_revision`.
Five distinct stock evidence IDs appear in more than one read-only run.
[The measured report from run 37772681168](https://github.com/alialnaggar/dealdeskdata/actions/runs/37772681168)
also captures line mode/category counts, as-of counts and SHA-256 of five SQL
inputs plus configuration, matrix and provider manifest. The diagnostic
is separate from deal inputs and expires with GitHub's CI artifact retention;
the code reproduces it from a fresh database. These pilot frequencies are
design-induced and must not be presented as target business rates.

Next: compare pilot metrics with explicit tolerances, resolve the four calibration
and 22 field reviews, and only then freeze the release generator and hidden
independent evaluation cases. Cross-deal allocation needs an explicit
reservation or replay rule before claims of portfolio-wide availability.
