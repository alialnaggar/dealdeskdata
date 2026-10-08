# Phase 1C release review — provisional decisions

**8 October 2026.** This is the compact review sheet for the generation freeze. The 36-deal development pilot passes PostgreSQL, but the full 80-customer / 400-history / 100-test release and separate 36-case evaluation set have not been generated. `ready_for_generation` remains false.

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

1. Generate independent credit, no-PO inbound and historical AR manifests; replay historical rows at their frozen as-of times and validate actual runtime output envelopes.
2. Finish product fit and comparable price/cost evidence, or explicitly label any unresolved values as bounded synthetic assumptions for thesis scope.
3. Generate the 80 customers and 400 chronological historical deals; measure the configured distributions and source provenance. Fix or document deviations before constructing the 100 generated tests.
4. Author the 36 evaluation variants and expected findings independently, keep them outside agent-visible inputs, then run fresh import, repeat-seed checksum and decision gates. Only then freeze the dataset version.
