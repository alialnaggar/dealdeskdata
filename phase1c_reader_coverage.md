# Phase 1C data reading layer

`read_run(connection, run_id)` reads a submitted deal, its frozen catalogue and applied commercial profile, and operational evidence available at `deal_runs.as_of_at`. It returns source rows with IDs plus derived numeric facts. It does not approve a deal or create reservations. Call it inside a PostgreSQL `REPEATABLE READ READ ONLY` transaction to prevent a mix of database states. Install `psycopg[binary]>=3.2,<4` to use it.

Source of truth: the **83 KB current** `02-Deal-Desk-Orchestrator-Phase1C.md` on Drive (updated 29 September 2026) and its `Phase1C-row-fixture-coverage-map.md`. The 11 KB attachment supplied to the coding chat is stale. This document tracks the initial reader against that current coverage map. The reader is a first data layer, not the full agent rule engine.

| Reference case | Selected evidence | Finding checked |
|---|---|---|
| Stock then confirmed receipt | Latest stock and binding PO receipt at one location; shipping lane | 8 free stock + 3 receipt units cover 10; arrival by request |
| Assembly later workday | Active matching BOM, components, dated receipt, labor need and daily capacity | Build 8, need 16 components and 5 hours; first fitting day September 2 |
| Offer without supplier commitment | Active supplier offer, no binding receipt | 10 day lead estimate; no confirmed shipping promise |
| Digital exact binding pool | Matching product, configuration, region and 12 month pool | 5 concurrent demand, 6 free, fresh binding **candidate**; full-term proof still needs validation |
| Digital provisional offer | Same scope, provisional capacity | 6 free, conditional, no confirmed entitlement |
| Digital stale pool | Same scope, older snapshot | Binding state exists, but unknown with stale evidence |
| Friday after cutoff | Stock snapshot and Berlin local lane clock | Monday dispatch, Wednesday arrival |
| Installation rule missing | No matching installation rule; separate stock/lane evidence | Eligibility unknown; shipment still feasible |
| Installation explicitly ineligible | Matching rule and separate stock/lane evidence | Installation ineligible; shipment still feasible |
| Inventory snapshot expired | Latest stock snapshot | 7 numeric free, but stale and cannot confirm |
| Credit exception within cap | Credit profile, latest invoice snapshot, deal total | Exposure 110,000 EUR, 10% over limit |
| Discount profile replay | One immutable deal, three run profile codes, product list price | Derived discount 10% in each profile; profile-specific policy evaluation is pending compiled rules |
| Assembled cost rollup | Product cost, matching BOM component cost and work hours | Reads 1,375 EUR product cost, 1,100 EUR component cost, 5 labor hours |
| Two lines share component | Both lines, one BOM, component stock and receipt | Aggregate demand 14, supply 13; no fitting day |

`test_phase1c_reader.py` loads the fixture rows into a disposable database after the existing rollback-only fixture check and compares selected outputs for all 14 cases. Run it only against a fresh test database; its loader inserts rows and must never point at production. CI is configured to run it after the schema checks. It does not use the SQL fixture's expected-answer assertions to compute its Python expectations. **These reader tests have not yet run against PostgreSQL.** They do not yet prove the full expected findings in the current Drive coverage map.

## Decisions to review before calibration is frozen

- **Freshness:** 24 hours is a provisional maximum age for inventory, digital pool and capacity snapshots, and credit commitments. Configure per source and business profile before generating a large dataset. A stale number is retained as evidence but cannot confirm capacity.
- **Digital quantity and proof:** `quantity` is billed units over the contract, while `configuration_json.units_per_period` is concurrent entitlement demand. The current reader requires `quantity = contract_months × units_per_period` and matches product attributes, country and term. Its `binding_candidate` must not be promoted to `confirmed_by_date` without validating full-term commitment evidence and activation lead time. Define this evidence contract before loading the large dataset.
- **Shipping:** A receipt expected on a given date is conservatively available for dispatch the *next* allowed workday. Workdays currently follow the lane's weekday list; holidays and supplier calendars are not yet evaluated.
- **Assembly:** Capacity is checked for one day and one resource at a time. The current finding must not be used as a final production promise if multiple operation steps, substitutions or shared resource consumption apply. Add ordered operations and all required resources before full dataset generation.
- **Commercial rules:** The SQL row fixture has no populated pricing, policy or approval rules. The reader selects rows only for the run's `applied_policy_set_code`; it does not invent discount bands or decide approvers. The current coverage map expects baseline credit and strict discount routes, but those cannot pass as agent findings until compiled rules are loaded and interpreted.
- **Cost:** The 1,375 EUR assembled cost is read from product master data. The fixture demonstrates a component + labor + overhead calculation, but the reader does not independently price labor or validate that rollup against the master cost. Decide where the labor rate and overhead percentage live.
- **Snapshot completeness:** Invoice snapshots are selected per invoice at or before the run date. A missing invoice or source-wide completeness marker cannot be detected with the current schema. Review that limit for credit conclusions.

The old narrative also describes 30–50 independent adversarial evaluation deals. These 14 database reference cases are implementation checks and do not replace that evaluation set.
