# Phase 1C release review — provisional decisions

**10 October 2026.** This is the compact review sheet for the generation freeze. The 36-deal development pilot passes PostgreSQL, and 80 customer masters and 400 historical inputs/runs have been generated. Historical labels, completed specialist executions, and the final independent evaluation release remain open. `ready_for_generation` remains false.

[PostgreSQL Actions run 37821625969](https://github.com/alialnaggar/dealdeskdata/actions/runs/37821625969) passed the typed-row, manifest, provider-reader, and full decision workflow after aligning the reader with the new evidence record shape. The local suite has 165 tests, with 35 database cases exercised in CI rather than locally.

## Decisions already bounded by executable evidence

| Decision | Current rule and evidence | Limit |
| --- | --- | --- |
| Product popularity | The top-fifth 60–70% historical line share is an explicit **synthetic coverage target**, not an Olist-derived enterprise statistic. Config and field basis reject a silent observed-source claim. | Check achieved share and per-product minimum on the 400 generated historical deals. |
| Capacity horizon | A confirmed component receipt beyond represented capacity dates yields `unknown`, with no invented later production slot. BUILD-HORIZON and stale-capacity cases pass in PostgreSQL. | A longer lead is not a longer capacity forecast. |
| Offered configurations | The draft's 18 make-to-order products and 24 offered BOM variants have exact signatures and one effective BOM per offered configuration. | Detailed sourced part fit remains open for 23 BOMs; structural coverage does not prove hardware compatibility. |
| Digital and shipping evidence | The pilot checks an independent full-term provider manifest, missing/partial proof, and dated Central/West shipping. | Provider and lane records are synthetic; no real commitment is claimed. |
| Ledger types and locations | The field checker now distinguishes 18 `TIMESTAMPTZ` fields from the one `TIME` field. Pilot source locations are restricted to the configured Central and West sites with matching origin time zones. | The full generator must obey the same mapping. |

## Remaining decisions before generation

| Gate | Field marks | Required closure |
| --- | --- | --- |
| Product fit, price and cost | `products.attributes_json`, `products.list_price`, `products.standard_cost` | Sourced comparable configurations and dated EUR price/unit/tax basis; check cross-kit interfaces, thermal and power limits for the remaining 23 BOMs; reconcile the €1,050 workstation and proposed margin band. Otherwise retain clearly synthetic price and fit assumptions with explicit limits. |
| Distribution | `customers.industry`, `customers.country_code`, `deal_lines.product_id` | Generate 80 customers and 400 historical deals, then measure country/industry, top-fifth product share, at-least-three occurrences per SKU, line-count bins and configured tolerances. The 36-deal case-designed pilot is not that sample. |
| Source evidence and replay | `customer_credit_profiles.commitment_evidence_ref`, `accounts_receivable.as_of_date`, `inbound_supply.evidence_ref`, `deals.evidence_refs_json`, `deal_runs.data_snapshot_ref` | The manifest validator checks typed provider records, full-term binding coverage, reference resolution, SHA-256 snapshot entries and as-of ordering. The pilot is pinned as `PILOT-OPERATIONS-SNAPSHOT`. Historical reader runs now require a complete frozen credit/AR manifest matching the run cutoff; generate and validate those manifests plus independent no-PO inbound proof before closing this gate. |
| Row and relationship checks | `suppliers.order_calendar_json`, `compatibility_rules.condition_json` | Execute typed row checks on all generated rows, dependency and installation predicates, and supplier lead/dispatch calendars. The pilot validator now closes the location, requirements, and per-mode line-configuration checks on 36 deals / 65 lines; dependency coverage remains open. |
| Runtime output | `agent_execution_log.output_json` | `validate_phase1c_runtime_outputs.py` now checks unique attempts, outcome-free inputs, typed output envelopes, agent identity and manifest evidence IDs. Populate and validate actual specialist runs; never fabricate execution logs as source data. |

The two remaining calibration-level review items are the provisional **36 components / 156 products** mix (structural BOM coverage exists, detailed sourcing/fit does not) and comparable **catalogue price dates, currencies, units and tax bases**. The ledger now has **14 field marks** open. No final threshold, source claim, distribution tolerance or release target is frozen by this sheet.

## Immediate build order

Historical operational replay now fails closed without a complete dated
manifest. This prevents later stock, supplier, capacity, digital or undated
shipping lane rows from leaking into a past run. No-PO confirmed receipts
require matching supplier evidence. The 400 queued runs therefore still need
their actual operational source ledger before baseline decisions can be
derived; the field marks remain open.

The provisional operational source has daily dated stock for 48 products,
38 standard lanes, 54 supplier/component offer SKUs, independently proved
inbound receipts, a dated workshop plan and synthetic digital provider pools
across all 400 cutoffs. They are hash pinned. Workshop feasibility does not
book a slot. Measure source distributions before deriving historical outcome
labels.

1. Generate independent credit, no-PO inbound and historical AR manifests; replay historical rows at their frozen as-of times and validate actual runtime output envelopes.
2. Finish product fit and comparable price/cost evidence, or explicitly label any unresolved values as bounded synthetic assumptions for thesis scope.
3. The provisional 80-customer master and 400 chronological historical input deals / 1,200 lines are generated. Their configured line bins and product share are exact. A separate synthetic source ledger resolves 400 SHA-pinned dated credit/AR views, and 400 queued baseline runs link to them. Generate and connect operational snapshots, derive documented baseline decisions and measure source provenance before constructing the 100 generated tests.
4. Author the 36 evaluation variants and expected findings independently, keep them outside agent-visible inputs, then run fresh import, repeat-seed checksum and decision gates. Only then freeze the dataset version.

## Dated workshop capacity increment — 9 October 2026

A separate hash-pinned synthetic workshop plan resolves 180 resource/day rows
per historical cutoff: 30 represented days across assembly, configuration and
test, each with equipment and workforce. Daily observations are within 24 hours
of each run cutoff; weekends have zero available hours. Existing allocations
and downtime follow provisional ranges. The resolver rejects missing days and
source digest changes; selection rejects future snapshots. This supports a
**feasible, uncommitted** build path, not a booked production slot. Capacity
beyond the window remains unknown. Baseline decisions, 14 field marks and two
calibration reviews remain open.

## Dated digital provider increment — 9 October 2026

A synthetic independent pool ledger now covers 36 of 41 digital SKUs in the
five configured countries, with daily as-of observations and six-day proof
refreshes. Across 5,580 pool epochs, the configured binding/provisional/unknown
mix is exactly 70/20/10%. Binding rows have separately hash-pinned provider
proof for the exact product, configuration, region, 12-month term, unit,
capacity and allocation; the proof states a full-term coverage interval.
Missing, changed or future proof fails closed. This is **synthetic test
evidence**, not a real provider promise. The five SKUs without exact pool
coverage remain unknown. The provisional protected-TB pool totals use the
instance range pending calibration review. The source resolves at all 400
historical cutoffs; generated historical decisions and actual agent execution
still have not been run.

## Historical baseline diagnostic — 9 October 2026

The disposable PostgreSQL pass read all 400 queued runs with compiled baseline
policy and frozen credit, operational and provider evidence. It wrote a
separate provisional diagnostic artifact and rolled back the imported rows;
no expected outcome or agent execution was written to deal inputs.

The first pass exposed a source-cadence mismatch: monthly commitment
observations made 386 of 400 credit views stale under the existing 24-hour
freshness rule. A provisional independent daily observation schedule at 85%
capture now yields 329 fresh and 71 stale views. The agreed calibration file
and threshold were not changed. Service coverage rules for 22 products now
cover DE, NL and BE with one explicit excluded region in each; FR and AT
remain unknown, and no service slot is claimed. Missing service coverage
fell from 184 to 52 line findings.

[PostgreSQL diagnostic run 37956989726](https://github.com/alialnaggar/dealdeskdata/actions/runs/37956989726)
passed all 400 reads. Its provisional gate distribution is 6
`approval_required`, 30 `needs_commitment`, 129 `needs_evidence`, 211
`needs_revision` and 24 `blocked`. Evidence-gap counts include 71 stale
credit commitments, 438 missing delivery findings, 185 missing digital
confirmations and 52 missing service coverage findings. These are overlapping
line/run findings, not exclusive deal counts. Delivery gaps need a per-mode
review before any historical labels are materialized or used for training.
The 14 field marks and two calibration reviews remain open.

## Historical workshop alignment — 10 October 2026

The provisional source now locates all 36 component SKUs at the configured
Central workshop. Finished stock continues to use the configured locations.
The reader also reports an unschedulable build as `infeasible` or `unknown`
according to its production classification, rather than leaving a
`pending_production_check` fulfillment status after the check has run.

[PostgreSQL run 38022399576](https://github.com/alialnaggar/dealdeskdata/actions/runs/38022399576)
passed the full workflow. All 220 historical make-to-order lines have matching,
selected BOMs; 200 now have feasible but uncommitted builds and 20 are
infeasible without replenishment. The 400-deal provisional gate mix is 6
`approval_required`, 24 `blocked`, 69 `needs_commitment`, 212
`needs_evidence` and 89 `needs_revision`. Evidence-gap findings are 71 stale
credit commitments, 238 missing delivery findings, 185 missing digital
confirmations and 52 missing service coverage findings. These findings can
overlap within a deal. The 20 material shortfalls and the remaining evidence
gaps require review before any labels or execution logs are authored.

## Dated inbound source increment — 8 October 2026

The independent provisional inbound ledger now has 441 supplier/component receipts across 63 products and seven monthly observation dates. Its Confirmed/Planned/Delayed/Cancelled mix follows the configured 70/20/8/2% target within 0.5 percentage points. Four SHA-256-pinned shards and a matching 400-cutoff index supply dated PO headers or independent supplier proofs for confirmed no-PO receipts. The historical resolver validates all 400 views; expired confirmations remain historical records but are not binding. Historical labels, actual execution logs, detailed product fit and comparable prices remain pending. The 14 field marks and two calibration reviews stay open.

## Remaining gap classification — 10 October 2026

[PostgreSQL run 38024615223](https://github.com/alialnaggar/dealdeskdata/actions/runs/38024615223)
passed the full workflow with a per-mode diagnostic and a corrected digital
gate. Of 185 previously reported digital confirmation gaps, 108 have fresh,
full-term provider proof and enough capacity but cannot meet the requested
activation date. They now receive a date revision; the other 77 have no
matching pool and remain evidence gaps. The provisional 400-deal mix is 6
`approval_required`, 24 `blocked`, 69 `needs_commitment`, 142
`needs_evidence`, and 159 `needs_revision`.

The 238 delivery evidence findings comprise 213 supplier-finished, 20
make-to-order, and five stocked-finished lines. Supplier-finished lines
include 168 conditional offers and 45 infeasible supply findings; an offer
is not a binding receipt. The remaining evidence findings are 71 stale
credit commitments, 77 digital pool gaps, and 52 service coverage gaps.
These counts overlap across deals and do not establish final labels.

## Weekly provisional inbound pipeline — 10 October 2026

The original monthly inbound observation schedule left 205 of 213
supplier-finished lines without a binding receipt even though confirmed
receipt history was visible: nine-day confirmations expired before many
deal cutoffs. The configured evidence recheck cadence is seven days. The
provisional independent source now records a fresh supplier pipeline each
week, with 1,764 separately evidenced events for 63 SKUs, while preserving
the configured 70/20/8/2% status mix and nine-day validity. It does not
extend old confirmations or use deal outcomes to create receipts.

[PostgreSQL run 38042504618](https://github.com/alialnaggar/dealdeskdata/actions/runs/38042504618)
passed. Of 257 supplier-finished lines, 159 are confirmed by the requested
date, 29 have a late alternative, 60 have conditional offers, and nine are
infeasible. Total missing delivery findings across physical lines fell from
238 to 82. The provisional 400-deal gate mix is 11 `approval_required`,
24 `blocked`, 102 `needs_commitment`, 124 `needs_evidence`, and 139
`needs_revision`. The weekly pipeline cadence and outcome mix remain
subject to calibration review; no historical label is frozen.
