"""Compile the three reviewed synthetic policy profiles into auditable SQL rows.

The JSON conditions are an explicit contract for the future decision engine.
They are not executable SQL predicates, and loading these rows does not make
the bounded Phase 1C reader a complete policy evaluator.
"""

import argparse
import json
from pathlib import Path

import yaml


PROFILE_CODES = ("BASELINE_2026", "LENIENT_EXPERIMENT", "STRICT_EXPERIMENT")
PREFIX = {"BASELINE_2026": "BASE", "LENIENT_EXPERIMENT": "LEN", "STRICT_EXPERIMENT": "STRICT"}
ROLE_ORDER = ("Regional_Manager", "Sales_Director", "Sales_VP", "Finance_Director", "Legal_Compliance")
TABLE_COLUMNS = {
    "pricing_rules": ("pricing_rule_id", "policy_set_code", "rule_name", "rule_type", "scope_type",
                      "scope_value", "condition_json", "action_json", "priority", "is_stackable"),
    "policy_rules": ("policy_rule_id", "policy_set_code", "rule_name", "policy_area", "scope_type",
                     "scope_value", "condition_json", "severity", "required_action",
                     "explanation_template", "priority"),
    "approval_rules": ("approval_rule_id", "policy_set_code", "rule_name", "condition_json",
                       "required_role", "approval_sequence", "priority"),
}


def validate(config):
    governance = config["governance"]
    profiles = governance["profiles"]
    if set(profiles) != set(PROFILE_CODES) or tuple(governance["approval_logic"]["role_order"]) != ROLE_ORDER:
        raise ValueError("Unexpected policy profiles or approval role order")
    categories = set(profiles["BASELINE_2026"]["pricing"]["category_margin_floor_pct"])
    if not categories:
        raise ValueError("Missing category floors")
    for code, profile in profiles.items():
        pricing, policy, approvals = (profile[x] for x in ("pricing", "policy", "approvals"))
        if set(pricing["category_margin_floor_pct"]) != categories:
            raise ValueError(f"Category coverage differs in {code}")
        d = [pricing[k] for k in ("routine_discount_max_pct", "discount_requires_sales_director_above_pct",
                                  "discount_requires_sales_vp_above_pct", "hard_discount_cap_pct")]
        if not (0 <= d[0] == d[1] < d[2] < d[3] < 100):
            raise ValueError(f"Invalid discount ladder in {code}")
        if not (0 < policy["standard_payment_terms_max_days"] == policy["extended_terms_require_finance_above_days"]
                < policy["hard_payment_terms_cap_days"]):
            raise ValueError(f"Invalid payment ladder in {code}")
        if not (policy["credit_exposure_tolerance_pct"] == 0
                < policy["credit_exception_max_over_limit_pct"]):
            raise ValueError(f"Invalid credit ladder in {code}")
        if not (0 < approvals["high_value_deal_above_eur"] < approvals["strategic_high_value_above_eur"]):
            raise ValueError(f"Invalid value ladder in {code}")
        if (approvals["routine_approver"], approvals["high_value_approver"],
                approvals["strategic_high_value_approver"]) != ROLE_ORDER[:3]:
            raise ValueError(f"Unexpected sales roles in {code}")
        if policy["contract_clause_actions"] != {"standard": "continue", "preapproved_variant": "continue",
                                                 "legal_review": "Legal_Compliance", "prohibited": "hard_block"}:
            raise ValueError(f"Unexpected contract clause behavior in {code}")
        if any(not 0 < value < 100 for value in pricing["category_margin_floor_pct"].values()):
            raise ValueError(f"Invalid category floor in {code}")
    strict, base, lenient = (profiles[x] for x in ("STRICT_EXPERIMENT", "BASELINE_2026", "LENIENT_EXPERIMENT"))
    for section, key in (("pricing", "routine_discount_max_pct"), ("pricing", "discount_requires_sales_vp_above_pct"),
                         ("pricing", "hard_discount_cap_pct"), ("policy", "standard_payment_terms_max_days"),
                         ("policy", "hard_payment_terms_cap_days"), ("policy", "credit_exception_max_over_limit_pct"),
                         ("approvals", "high_value_deal_above_eur"),
                         ("approvals", "strategic_high_value_above_eur")):
        if not strict[section][key] <= base[section][key] <= lenient[section][key]:
            raise ValueError(f"Nonmonotonic {section}.{key}")
    for category in categories:
        if not (strict["pricing"]["category_margin_floor_pct"][category]
                >= base["pricing"]["category_margin_floor_pct"][category]
                >= lenient["pricing"]["category_margin_floor_pct"][category]):
            raise ValueError(f"Nonmonotonic margin floor: {category}")


def compile_rows(config):
    validate(config)
    rows = {table: [] for table in TABLE_COLUMNS}
    ids = set()

    def add(table, code, suffix, **values):
        prefix = {"pricing_rules": "PR", "policy_rules": "PO", "approval_rules": "AP"}[table]
        rule_id = f"{prefix}-{PREFIX[code]}-{suffix}"
        if rule_id in ids:
            raise ValueError(f"Duplicate rule ID: {rule_id}")
        ids.add(rule_id)
        id_key = TABLE_COLUMNS[table][0]
        rows[table].append({id_key: rule_id, "policy_set_code": code, **values})

    for code in PROFILE_CODES:
        profile = config["governance"]["profiles"][code]
        price, policy, approval = (profile[x] for x in ("pricing", "policy", "approvals"))
        for suffix, threshold, flag, priority in (
            ("DIRECTOR", price["discount_requires_sales_director_above_pct"], "director_discount", 20),
            ("VP", price["discount_requires_sales_vp_above_pct"], "vp_discount", 10),
        ):
            add("pricing_rules", code, suffix, rule_name=f"Discount above {threshold}%", rule_type="volume_discount",
                scope_type="global", scope_value=None, condition_json={"discount_pct_gt": threshold,
                "basis": "each_line_and_list_weighted_deal"}, action_json={"flag": flag}, priority=priority,
                is_stackable=False)
        for category, floor in sorted(price["category_margin_floor_pct"].items()):
            add("pricing_rules", code, "FLOOR-" + category.upper().replace("_", "-"),
                rule_name=f"{category} margin floor", rule_type="category_margin_floor", scope_type="category",
                scope_value=category, condition_json={"margin_pct_lt": floor, "basis": "each_line"},
                action_json={"flag": "margin_below_floor", "max_exception_deviation_points":
                             price["margin_floor_exception_max_deviation_percentage_points"]},
                priority=30, is_stackable=False)
        def pol(suffix, name, area, condition, severity, action, priority):
            add("policy_rules", code, suffix, rule_name=name, policy_area=area, scope_type="global", scope_value=None,
                condition_json=condition, severity=severity, required_action=action,
                explanation_template=name, priority=priority)
        pol("DISCOUNT-CAP", "Discount exceeds hard cap", "pricing",
            {"discount_pct_gt": price["hard_discount_cap_pct"], "basis": "each_line_or_list_weighted_deal"},
            "blocker", "reject", 1)
        pol("MARGIN-NONPOSITIVE", "Line or deal margin is nonpositive", "margin",
            {"margin_pct_lte": 0, "basis": "each_line_or_revenue_weighted_deal"}, "blocker", "reject", 1)
        pol("MARGIN-SHORTFALL", "Category margin shortfall exceeds exception", "margin",
            {"category_floor_shortfall_points_gt": price["margin_floor_exception_max_deviation_percentage_points"],
             "basis": "each_line"}, "blocker", "reject", 2)
        pol("MARGIN-EXCEPTION", "Positive margin within floor exception", "margin",
            {"margin_pct_gt": 0, "category_floor_shortfall_points_gt": 0,
             "category_floor_shortfall_points_lte": price["margin_floor_exception_max_deviation_percentage_points"],
             "basis": "each_line"}, "approval_required", "escalate", 10)
        pol("PAYMENT-CAP", "Payment terms exceed hard cap", "payment",
            {"payment_terms_days_gt": policy["hard_payment_terms_cap_days"]}, "blocker", "reject", 1)
        pol("PAYMENT-INVALID", "Payment terms are not allowed", "payment",
            {"payment_terms_days_not_in": config["dataset"]["payment_terms_days"]}, "blocker", "reject", 1)
        pol("PAYMENT-EXCEPTION", "Payment terms need Finance review", "payment",
            {"payment_terms_days_gt": policy["standard_payment_terms_max_days"],
             "payment_terms_days_lte": policy["hard_payment_terms_cap_days"]},
            "approval_required", "escalate", 10)
        pol("CREDIT-CAP", "Credit exposure exceeds exception cap", "credit",
            {"credit_over_limit_pct_gt": policy["credit_exception_max_over_limit_pct"]}, "blocker", "reject", 1)
        pol("CREDIT-EXCEPTION", "Credit exposure needs Finance review", "credit",
            {"credit_over_limit_pct_gt": 0,
             "credit_over_limit_pct_lte": policy["credit_exception_max_over_limit_pct"]},
            "approval_required", "escalate", 10)
        pol("CREDIT-ON-HOLD", "Customer credit is on hold", "credit",
            {"credit_status_eq": "On-Hold"}, "blocker", "reject", 1)
        pol("ACCOUNT-INACTIVE", "Customer account is not active", "credit",
            {"account_status_in": ["Inactive", "Suspended", "Blocked"]}, "blocker", "reject", 1)
        pol("CREDIT-REVIEW", "Customer credit status needs review", "credit",
            {"credit_status_eq": "Review"}, "approval_required", "escalate", 10)
        pol("OVERDUE-AR", "Positive overdue AR needs Finance review", "credit",
            {"overdue_ar_eur_gt": 0}, "approval_required", "escalate", 10)
        pol("CONTRACT-LEGAL", "Contract clause needs Legal review", "contract",
            {"contract_clause_eq": "legal_review"}, "approval_required", "escalate", 10)
        pol("CONTRACT-PROHIBITED", "Prohibited contract clause", "contract",
            {"contract_clause_eq": "prohibited"}, "blocker", "reject", 1)
        pol("CONTRACT-INVALID", "Contract clause is not allowed", "contract",
            {"contract_clause_not_in": config["dataset"]["contract_clause_codes"]}, "blocker", "reject", 1)
        pol("DELIVERY-LATE", "Delivery later than requested", "delivery",
            {"delivery_later_than_requested": True}, "approval_required", "escalate", 10)
        def route(suffix, name, condition, role, priority):
            add("approval_rules", code, suffix, rule_name=name, condition_json=condition,
                required_role=role, approval_sequence=ROLE_ORDER.index(role), priority=priority)
        route("ROUTINE", "Routine sales approval", {"highest_sales_role": "Regional_Manager"},
              "Regional_Manager", 30)
        route("SALES-DIRECTOR", "Sales Director escalation", {"highest_sales_role": "Sales_Director"},
              "Sales_Director", 20)
        route("SALES-VP", "Sales VP escalation", {"highest_sales_role": "Sales_VP"}, "Sales_VP", 10)
        route("FINANCE", "Finance exception", {"finance_exception": True}, "Finance_Director", 10)
        route("LEGAL", "Legal exception", {"legal_exception": True}, "Legal_Compliance", 10)
        # Value thresholds enter the same highest-sales-role calculation as discount and margin.
        route("VALUE-DIRECTOR", "High value sales band", {"deal_commitment_eur_gt":
              approval["high_value_deal_above_eur"]}, "Sales_Director", 20)
        route("VALUE-VP", "Strategic high value sales band", {"deal_commitment_eur_gt":
              approval["strategic_high_value_above_eur"]}, "Sales_VP", 10)
    return rows


def _sql_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return "'" + value.replace("'", "''") + "'::jsonb"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def render_sql(rows):
    lines = ["-- Generated by compile_phase1c_policy.py from calibration_config.yaml.",
             "-- Synthetic simulation rules; the reader currently interprets only its bounded test grammar.",
             "BEGIN;"]
    codes = ",".join(_sql_value(x) for x in PROFILE_CODES)
    for table in ("approval_rules", "policy_rules", "pricing_rules"):
        lines.append(f"DELETE FROM deal_desk.{table} WHERE policy_set_code IN ({codes});")
    for table, columns in TABLE_COLUMNS.items():
        for row in rows[table]:
            values = ", ".join(_sql_value(row[col]) for col in columns)
            lines.append(f"INSERT INTO deal_desk.{table} ({', '.join(columns)}) VALUES ({values});")
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("calibration_config.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = compile_rows(yaml.safe_load(args.config.read_text(encoding="utf-8")))
    args.output.write_text(render_sql(rows), encoding="utf-8")
    print("Compiled " + ", ".join(f"{len(items)} {table}" for table, items in rows.items()))


if __name__ == "__main__":
    main()
