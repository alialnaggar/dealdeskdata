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
shares. They model a provider with a small local configuration workshop;
supplier-finished hardware is sourced as a complete item. Real OEMs offer
configurable workstations, servers and storage, but those examples do not
prove our fictional provider builds them in-house. Neutral IDs are used;
the projection has no names, prices, costs, supplier offers, inventories,
capacity dates, customers, or deals. The chosen component IDs and quantities
are placeholders and require compatibility and cost validation.

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

**User review before freeze:** decide whether the fictional provider should
have its own small assembly/configuration workshop for the 18 buildable
products, or whether any of these should instead be supplier-configured.
The precise 10/6/2 mix is adjustable. No database setup is required for this
review.

Next: make product-option and component compatibility explicit, add a
justified substitute example, then validate costs and representative master
data rows. Keep the dataset-generation gate closed until those checks pass.
