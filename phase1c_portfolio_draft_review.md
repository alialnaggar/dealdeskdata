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
| Components reused in at least two BOMs | 18/36 (50%) |
| BOMs with substitution groups | 1/24 (4.17%) |

The nine sellable category counts follow `calibration_config.yaml`. The
**proposed operating mix** is:

| Product category | Total | Stocked | Supplier-finished | Locally configured/buildable | Digital activation | Scheduled service |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| End-user devices and workplace | 18 | 10 | 6 | 2 | 0 | 0 |
| Servers and compute | 12 | 0 | 2 | 10 | 0 | 0 |
| Storage and data protection | 10 | 2 | 2 | 6 | 0 | 0 |
| Networking | 16 | 0 | 14 | 0 | 2 | 0 |
| Cybersecurity | 12 | 0 | 3 | 0 | 9 | 0 |
| Cloud subscriptions | 12 | 0 | 0 | 0 | 12 | 0 |
| Enterprise software | 18 | 0 | 0 | 0 | 18 | 0 |
| Implementation services | 12 | 0 | 0 | 0 | 0 | 12 |
| Support and warranty | 10 | 0 | 0 | 0 | 0 | 10 |
| **Total** | **120** | **12** | **27** | **18** | **41** | **22** |

The 18 locally buildable SKUs are 2 workstations, 10 servers (4 rack, 3
tower, 2 edge, 1 GPU), and 6 storage systems (3 arrays, 2 NAS, 1 backup
appliance). The two workstations and four rack servers offer both standard
and alternate options at the same product price; the other 12 offer standard
only. That yields 24 explicit configurations and 24 effective BOMs. Every BOM contains one part
from each of the four component families (compute, storage, network/power,
chassis/other) and has assembly and test operations. Eighteen components are
reused in at least two BOMs.

All 156 draft products now have the common typed product attributes. Digital
products have an edition, services have a service code, and components declare
their supported build platform. The three synthetic platforms are workstation,
server and storage system. Every BOM component supports its finished product's
platform. A product offers only the options declared in its attributes, and
the paired standard/alternate BOMs use different components. Negative tests
reject undeclared options, wrong-platform parts and missing attributes.

These allocations are **synthetic design assumptions**, not observed market
shares. The user approved a small local configuration and test workshop for
the 18 buildable SKUs on 6 October 2026. The precise 10/6/2 product mix,
component identities and commercial values remain proposed. This model
assumes the provider can assemble/configure the listed systems locally;
supplier-finished hardware is sourced as a complete item. Real OEMs offer
configurable workstations, servers and storage, but those examples do not
prove our fictional provider builds them in-house. Neutral IDs are used;
the projection has no names, prices, costs, supplier offers, inventories,
capacity dates, customers, or deals. The chosen component IDs and quantities
are placeholders and require compatibility and cost validation.

One standard workstation BOM has two same-family network/power alternatives.
The selector takes **one**, preferring sufficient fresh stock or confirmed
inbound; it does not consume both. A focused test gives the second-priority
part one available unit and the first none, so the second is selected for
the one whole kit required by one build. This proves the selection
mechanic, not electrical or form-factor interchangeability. The remaining
23 BOMs have no substitute group.

Illustrative official configuration references: [HP Z workstation options](https://www.hp.com/emea_middle_east-en/workstations/desktop-workstation-pc.html),
[Dell PowerEdge configuration services](https://i.dell.com/sites/csdocuments/Legal_Docs/en/us/dell-emc-configuration-services-enterprise-sd-en.pdf),
and [Dell PowerVault ME5 enclosure variants](https://www.dell.com/support/manuals/en-us/powervault-me5012/me5_series_om/enclosure-configurations).
These support configurable product examples, not the draft category counts.

The validator reports no structural errors and still returns
`ready_for_full_generation: false`. The pass proves only that one explicit
allocation can meet the proposed 18/24/36 coverage and 40% reuse threshold.
It does **not** prove the mix is commercially believable, that individual
parts fit at socket/interface/power level, that component costs fit price
bands, or that the whole 24-table dataset can be generated. The
remaining field reviews and source/price checks stay open.

**User review before freeze:** the shared-price paired-option model is settled. The
precise 10/6/2 mix, detailed part compatibility, component identity/cost and price
bands are still open. No database setup is required for this structural pass.

Next: prepare representative master-data rows, then consider whether the fictional part catalogue needs
more detailed compatibility fields. Keep the dataset-generation gate closed.

## Variant cost boundary

The user chose the simpler shared-price route on 6 October 2026. The six
paired options are **technical alternatives**, so the label is `alternate`
rather than `enhanced`; they do not imply a separate premium price. The schema
has one `list_price` and one `standard_cost` per product, even when
the product has two configured BOMs. `validate_phase1c_variant_cost_pilot.py`
therefore requires one standard cost to stay within the configured 5% rollup
tolerance for **both** BOMs and to be at least the higher BOM cost. This is the
documented conservative-cost route in the current calibration rule; a
materially larger variant cost would need another priced SKU or a schema and
pricing-design change.

The explicit **illustrative** workstation pilot uses €30 per workforce hour,
10% overhead, and component costs supplied in
`phase1c_variant_cost_pilot.json`. With the current explicit kit quantities, it calculates €683.33 and €705.33 for the
two configurations. A single €715 standard cost is conservative and fits
both within 5%. Its €1,050 list price is the draft category median anchor,
**not a verified comparable current workstation price**. The resulting
31.90% catalogue margin is arithmetic only, not an achieved market margin.
Negative tests reject an undercosted shared standard cost, a materially
more expensive option, a missing part cost, and an unresolved substitute.
The initial workstation is retained unchanged in the broader synthetic draft.

## All-build cost feasibility draft

`phase1c_build_cost_draft.json` provides one shared component-cost set for all
36 proposed parts, explicit substitute choices, and one list price and
standard cost for each of the 18 buildable products. The batch check reuses
the product cost gate rather than adding a new product or pricing schema. It
passes all 18 products and all 24 offered BOMs; no paired option exceeds the
5% shared-cost tolerance. It rejects missing products, missing component
costs and invalid per-product cost rollups. The generation gate remains closed.

These values are **constructed to test arithmetic**, not independently
calibrated commercial inputs. Except for the retained workstation pilot,
component costs use simple platform/family bases with small ordinal variation;
prices are derived from the resulting cost and the category's proposed p50
margin, rounded up to the next €10. The resulting workstation margins are
18.59% and 31.90%, server margins 16.02–16.07%, and storage margins
19.00–19.03%. Because inputs and prices were jointly constructed, passing
the cost gate cannot establish realistic market prices, GPU premiums,
individual component compatibility or credible supplier sourcing. Those
reviews remain open before full dataset generation. The retained €1,050
workstation pilot's 31.90% margin also exceeds its category's proposed p90
margin of 28%; reconcile that mismatch with cost and price evidence before
treating the product as calibrated.

## Representative PostgreSQL master slice

`render_phase1c_master_slice.py` maps one proposed workstation, one rack
server and one storage array into the actual `products`, `bom_headers`,
`bom_lines` and `production_requirements` columns. The five offered BOMs
reuse their shared component-cost inputs and include the workstation's
declared substitute group. The generated `phase1c_master_slice.sql` inserts
the rows in a transaction, checks product/BOM counts, component platform
support and the selected BOM cost against each finished product's one
standard cost, then rolls back. CI also checks that the SQL matches its JSON
source before applying it to PostgreSQL. This is a focused schema/relationship
fixture; it does not load all 156 products or prove supplier, inventory,
capacity, deal and evidence coverage for the final dataset.

## Compatibility and price evidence audit — 6 October 2026

`audit_phase1c_build_readiness.py` makes the remaining evidence boundary
visible. All 36 component records lack basic interface/form-factor/power
specifications, so all 24 BOMs await detailed fit checking. The existing
platform check still passes; it cannot establish electrical, mechanical or
vendor interchangeability. Filling the fields alone would not establish fit:
cross-part constraints and independently sourced component identities are
still needed. The audit also finds the €1,050 workstation at a 31.90% draft
margin, above the proposed category p90 of 28%.

Official manufacturer pages illustrate why price evidence must include an
exact configuration and tax basis. [HP's Z2 Tower G1i German listing](https://www.hp.com/de-de/shop/products/desktops/hp-z2-tower-g1i-workstation-desktop-pc-a40mdet-abd)
shows €4,049 including VAT for a Core Ultra 9, 32 GB, 1 TB SSD and RTX 2000
Ada configuration. [Dell's Precision 5860 Ireland configurator](https://www.dell.com/en-ie/shop/dell-pro-max-pcs-and-workstations/precision-5860-tower-workstation/spd/precision-5860-workstation/xctopt5860emea_vp)
shows €3,504.96 including VAT for its selected configuration and exposes
separate choices for graphics, memory, storage and chassis power. These
retail listings are **not** comparable to the anonymous €1,050 draft build:
the draft has no CPU/GPU/RAM/storage specification, brand, support term,
country or tax treatment. Neither listing reveals the fictional provider's
component purchase costs or gross margin. Prices are time-sensitive snapshots
checked on 6 October 2026; no market price or 28% margin is frozen from them.

Next input to prepare is a named specification for one workstation and its
alternatives (CPU/socket or controller, storage interface/form factor, power
draw and supply budget), plus a comparable dated price excluding or including
tax consistently. Then test actual cross-part fit before extending this to
the other 23 BOMs. Full generation remains gated.

## Enclosure quantity correction — 6 October 2026

The first draft assigned two units to every component family, including the
`chassis_and_other` family. For this proposal that family represents one
enclosure or assembly kit per finished system. Its 24 BOM lines now use one
unit with zero scrap. The six **synthetic** enclosure unit costs were doubled
to keep the arithmetic pilot roughly comparable, not to claim market cost
evidence. The workstation option rollups changed from €688.56/€710.78 to
€686.56/€708.78 at that correction step; its €715 standard cost and €1,050 list price were unchanged.
The draft JSON and representative SQL slice were regenerated, and the batch
cost rule still passes 18 products and 24 BOMs. The compute, storage and
network/power quantities remain illustrative until the part roles are named;
the entire portfolio still awaits technical compatibility and price sourcing.

## Explicit component roles and quantities — 6 October 2026

The four families now have concrete **synthetic bundle roles**: one compute
kit (board, CPU and memory as a prevalidated bundle), two storage drives, one
network/power kit, and one enclosure kit per finished system. Each part record
declares its role; the portfolio validator rejects a role that does not match
its family. The standard workstation substitutes one network/power kit for
another, so the selector now needs one available kit. The only nonzero draft
scrap remains 1% for the two drives. These are deliberately simple assembly
assumptions, not a claim that arbitrary CPUs, boards, drives, supplies and
chassis fit together.

Synthetic unit costs for compute and network/power kits were doubled when
their quantities fell from two to one, to retain comparable cost arithmetic.
The current workstation option rollups are €683.33 and €705.33; one €715
standard cost still covers both within the proposed 5% tolerance. The
€1,050 list price and 31.90% catalogue margin remain **unverified**. All 18
buildable products and 24 BOM cost rollups pass locally. Full generation
stays gated on sourced kit specifications, cross-kit interfaces and power,
and comparable price/cost evidence.
