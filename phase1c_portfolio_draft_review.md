# Phase 1C structural portfolio draft — 6 October 2026

This is a reproducible **proposal for review**, not a generated operational
dataset or calibrated price catalogue. `build_phase1c_portfolio_draft.py`
produces `phase1c_portfolio_draft.json`; the portfolio checker validates the
file against current proposed counts and effective BOM relationships.

| Check | Draft result |
| --- | ---: |
| Sellable products / component products | 120 / 36 |
| Make-to-order products | 18 |
| Explicitly offered configurations / effective BOMs | 24 / 24 |
| Components reused in at least two BOMs | 16/36 (44.44%) |
| BOMs with substitution groups | 0 |

The nine sellable category counts follow `calibration_config.yaml`. As a
**draft allocation**, six server, six storage, and six networking products
are make-to-order; the first six of those have two variants. Every BOM has
three required parts and assembly/test steps. The other products receive
placeholder fulfillment modes based on category type. These assignments are
not externally calibrated or approved. Neutral IDs are intentionally used;
the projection has no names, prices, costs, supplier offers, inventories,
capacity dates, customers, or deals.

The validator reports no structural errors and still returns
`ready_for_full_generation: false`. The pass proves only that one explicit
allocation can meet the proposed 18/24/36 coverage and 40% reuse threshold.
It does **not** prove the mix is commercially believable, that BOM variants
are compatible, that component costs fit price bands, that substitutions are
covered, or that the whole 24-table dataset can be generated. The remaining
field reviews and the source/price checks stay open.

Next: review the product and component allocation, add a justified small
substitution/option pattern, then run row-level checks on representative
generated master data and compare BOM costs to the draft sellable cost bands.
The user only needs to judge the proposed mix when it is presented in
business terms; no local database setup is required for this structural pass.
