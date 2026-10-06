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
and enhanced options; the other 12 offer standard only. That yields 24
explicit configurations and 24 effective BOMs. Every BOM contains one part
from each of the four component families (compute, storage, network/power,
chassis/other) and has assembly and test operations. Sixteen components are
reused in at least two BOMs.

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
part three available units and the first none, so the second is selected for
the three whole parts required by one build. This proves the selection
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
parts are compatible, that component costs fit price bands, that substitutions
are covered, or that the whole 24-table dataset can be generated. The
remaining field reviews and source/price checks stay open.

**User review before freeze:** the workshop operating model is settled. The
precise 10/6/2 mix, option compatibility, component identity/cost and price
bands are still open. No database setup is required for this structural pass.

Next: make product-option and component compatibility explicit, then validate
costs and representative master-data rows. Keep the dataset-generation gate
closed until those checks pass.
