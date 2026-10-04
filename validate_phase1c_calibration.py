"""Pre-generation checks for the Phase 1C parameter contract.

This checks configured arithmetic and coverage relationships. It does not
claim that synthetic operational numbers are measured industry statistics or
that generated database rows already exist.
"""

from pathlib import Path
import argparse
import json

import yaml


PROVIDER_FIELDS = {
    "evidence_ref", "product_id", "provider_id", "configuration_signature_json",
    "region_code", "term_code", "capacity_unit", "capacity_total",
    "quantity_allocated", "commitment_status", "verified_at", "covers_from", "covers_until",
}


def validate(config):
    errors, review = [], []

    def check(ok, label):
        if not ok:
            errors.append(label)

    def triplet(values, label, nonnegative=True):
        check(isinstance(values, list) and len(values) == 3 and
              all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values) and
              values[0] <= values[1] <= values[2] and
              (not nonnegative or values[0] >= 0), label)

    def shares(values, total, label):
        check(isinstance(values, dict) and values and
              all(isinstance(v, (int, float)) and v >= 0 for v in values.values()) and
              abs(sum(values.values()) - total) < 1e-8, label)

    ds = config["dataset"]
    catalogue = config["product_catalogue"]["categories"]
    commercial = config["commercial_supply"]
    p = config["fulfillment_production_calibration"]["proposed_parameters"]
    injected = config["conflict_injection"]

    check(ds["sellable_products"] == sum(c["count"] for c in catalogue.values()),
          "sellable category counts must equal dataset target")
    for name, category in catalogue.items():
        check(category["count"] == sum(category["subcategories"].values()),
              f"subcategory counts mismatch: {name}")
        price = category["price_eur"]
        check(0 < price["p10"] < price["p50"] < price["p90"],
              f"price anchors are not ordered: {name}")
        margin = commercial["standard_cost"]["target_list_margin_percent_by_category"].get(name)
        check(margin is not None and 0 < margin["p10"] < margin["p50"] < margin["p90"] < 100,
              f"margin anchors missing or not ordered: {name}")
    check(set(catalogue) == set(commercial["standard_cost"]["target_list_margin_percent_by_category"]),
          "category/margin keys differ")

    shares(ds["customer_segment_counts"], ds["customers"], "customer segment counts")
    line_weights = ds["historical_lines_per_deal_sampling_percent"]
    shares(line_weights, 100, "historical line-count sampling weights")
    check(set(line_weights) == set(range(1, 9)), "historical line-count bins must be 1..8")
    check(abs(sum(n * pct for n, pct in line_weights.items()) / 100 -
              ds["historical_lines_per_deal_target"]) < 1e-8,
          "historical line-count expected mean differs from target")
    bounds = ds["historical_lines_per_deal_achieved_mean_range"]
    check(len(bounds) == 2 and bounds[0] <= ds["historical_lines_per_deal_target"] <= bounds[1],
          "historical achieved mean band must contain target")
    check(0 <= ds["historical_lines_per_deal_bin_tolerance_percentage_points"] <= 100,
          "historical line-count bin tolerance")
    credit = commercial["credit_profiles"]
    shares(credit["risk_rating_exact_counts"], ds["customers"], "risk rating counts")
    shares(credit["credit_status_exact_counts"], ds["customers"], "credit status counts")
    for segment, count in ds["customer_segment_counts"].items():
        shares(credit["default_payment_terms_exact_counts_by_segment"][segment], count,
               f"payment terms for {segment}")
        limits = credit["credit_limit_eur_by_segment"][segment]
        triplet([limits["minimum"], limits["mode"], limits["maximum"]], f"credit limits for {segment}")
    check(credit["maximum_credit_limit_eur"] >=
          max(v["maximum"] for v in credit["credit_limit_eur_by_segment"].values()),
          "credit ceiling below segment maximum")
    shares({k: v["share"] for k, v in commercial["requested_discount"]["historical_line_target_bands"].items()},
           1, "historical discount shares")
    shares(commercial["availability"]["inventory_state_target_share"], 1,
           "stock state shares")
    shares(injected["requested_case_mix_pct"], ds["generated_test_deals"],
           "generated-test case counts")
    check(injected["requested_case_mix_pct"]["clean"] > 0 and
          injected["requested_case_mix_pct"]["multi_flag"] > 0,
          "test mix needs clean and multi-flag cases")

    c = p["component_catalogue"]
    check(sum(c["family_counts"].values()) == c["non_sellable_component_count"] and
          c["total_product_rows_with_120_sellable"] == ds["sellable_products"] + c["non_sellable_component_count"],
          "component count/total product count mismatch")
    check(c.get("component_unit_indivisible") is True and
          c.get("stock_requirement_rule") == "sum_scrap_adjusted_theoretical_demand_across_selected_builds_then_round_up_once_per_component",
          "component stock rounding contract differs from reader")
    b = p["BOMs"]
    check(0 < b["make_to_order_sellable_count"] <= ds["sellable_products"] and
          b["effective_configured_BOM_variants_range"][0] >= b["make_to_order_sellable_count"],
          "BOM variants cannot cover the proposed assembled products")
    triplet(b["mandatory_components_per_BOM"], "components per BOM")
    triplet(p["suppliers"]["component_lead_workdays"], "supplier lead workdays")
    triplet(p["aggregate_inventory"]["component_on_hand_units"], "component stock")
    for key in ("setup_hours_per_batch", "workforce_hours_per_finished_unit", "equipment_hours_per_finished_unit"):
        triplet(p["production_requirements"][key], key)
    capacity = p["production_capacity"]
    for key in ("equipment_daily_available_hours", "workforce_daily_available_hours",
                "existing_allocation_to_available_ratio", "downtime_reduction_fraction"):
        triplet(capacity[key], key)
    check(capacity["existing_allocation_to_available_ratio"][2] <= 1 and
          capacity["downtime_reduction_fraction"][2] <= 1,
          "capacity ratios cannot exceed one")
    check(0 <= capacity["downtime_working_capability_day_share"] <= 1,
          "downtime share must be between zero and one")
    digital = p["digital_capacity"]
    shares(digital["generated_commitment_status_pct"], 100, "digital commitment shares")
    for key in ("user_and_licence_concurrent_total", "instance_concurrent_total",
                "allocated_to_total_ratio", "activation_lead_workdays"):
        triplet(digital[key], key)
    check(set(digital["trusted_provider_evidence_required_fields"]) == PROVIDER_FIELDS,
          "digital proof fields differ from reader's trusted manifest")
    check(p["purchase_orders_and_inbound"]["confirmed_component_receipt_usable_for_production"]
          == "on_expected_date_at_day_precision" and
          not p["purchase_orders_and_inbound"]["intraday_arrival_or_start_time_claimed"],
          "production receipt date convention changed")
    check(config["fulfillment_production_calibration"]["evidence_classification"]
          == "synthetic_operational_assumptions_unless_specific_independent_source_is_profiled",
          "operational parameters must retain synthetic provenance")

    # A planning horizon can be shorter than a supplier lead; this is a
    # coverage limit, never a reason to invent a confirmed production date.
    if capacity["horizon_calendar_days"] < p["suppliers"]["component_lead_workdays"][2] * 7 / 5:
        review.append("30-workday supplier lead can exceed the capacity horizon: label out-of-horizon builds unknown/conditional, or extend the horizon before generation")
    if ds["component_products_target"] is None or ds["total_product_rows_target"] is None:
        review.append("36 components/156 total products are proposals; top-level generation targets remain unset until BOM coverage review")
    review.append("Olist mirror checksums have not been matched to the canonical download; do not call derived rates enterprise statistics")
    review.append("Validate visible catalogue price dates and category/unit comparability before freezing EUR bands")
    return {"errors": errors, "review_before_freeze": review,
            "ready_for_generation": not errors and not review}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("calibration_config.yaml"))
    args = parser.parse_args()
    result = validate(yaml.safe_load(args.config.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
