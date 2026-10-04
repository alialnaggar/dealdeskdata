"""Evaluate the compiled synthetic commercial rules for one immutable deal run.

This is a deterministic commercial decision package. It never grants an
approval, reserves supply, or substitutes for configuration/fulfillment agents.
Unknown or partial rule sets fail closed rather than silently approving a deal.
"""

from decimal import Decimal


PREFIXES = {"BASELINE_2026": "BASE", "LENIENT_EXPERIMENT": "LEN", "STRICT_EXPERIMENT": "STRICT"}
ROLES = ("Regional_Manager", "Sales_Director", "Sales_VP", "Finance_Director", "Legal_Compliance")
POLICY_SUFFIXES = {
    "DISCOUNT-CAP", "MARGIN-NONPOSITIVE", "MARGIN-SHORTFALL", "MARGIN-EXCEPTION",
    "PAYMENT-CAP", "PAYMENT-INVALID", "PAYMENT-EXCEPTION", "CREDIT-CAP",
    "CREDIT-EXCEPTION", "CREDIT-ON-HOLD", "ACCOUNT-INACTIVE", "CREDIT-REVIEW", "OVERDUE-AR",
    "CONTRACT-LEGAL", "CONTRACT-PROHIBITED", "CONTRACT-INVALID", "DELIVERY-LATE",
}
APPROVAL_SUFFIXES = {"ROUTINE", "SALES-DIRECTOR", "SALES-VP", "FINANCE", "LEGAL",
                     "VALUE-DIRECTOR", "VALUE-VP"}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("Rule threshold is not numeric")
    return Decimal(str(value))


def _compiled_rules(bundle):
    code = bundle["run"]["applied_policy_set_code"]
    if code not in PREFIXES:
        raise ValueError("Unknown policy set")
    prefix = PREFIXES[code]
    groups = bundle["rules"]
    expected = {"pricing_rules": 11, "policy_rules": 17, "approval_rules": 7}
    if any(len(groups[name]) != count for name, count in expected.items()):
        raise ValueError("Incomplete compiled policy profile")
    by_type = {}
    for table, stem in (("pricing_rules", "PR"), ("policy_rules", "PO"), ("approval_rules", "AP")):
        key = {"PR": "pricing_rule_id", "PO": "policy_rule_id", "AP": "approval_rule_id"}[stem]
        indexed = {}
        for rule in groups[table]:
            head = f"{stem}-{prefix}-"
            if rule["policy_set_code"] != code or not rule[key].startswith(head):
                raise ValueError("Rule belongs to another profile")
            suffix = rule[key][len(head):]
            if suffix in indexed:
                raise ValueError("Duplicate compiled rule")
            indexed[suffix] = rule
        by_type[stem] = indexed
    if (set(by_type["PO"]) != POLICY_SUFFIXES or set(by_type["AP"]) != APPROVAL_SUFFIXES
            or set(by_type["PR"]) - {"DIRECTOR", "VP"} != {
                "FLOOR-" + category.upper().replace("_", "-")
                for category in (r["scope_value"] for r in groups["pricing_rules"] if r["rule_type"] == "category_margin_floor")
            } or len([s for s in by_type["PR"] if s.startswith("FLOOR-")]) != 9
            or not {"DIRECTOR", "VP"}.issubset(by_type["PR"])):
        raise ValueError("Unexpected compiled policy rule IDs")
    for suffix, rule in by_type["PR"].items():
        condition, action = rule["condition_json"], rule["action_json"]
        if suffix.startswith("FLOOR-"):
            if (rule["rule_type"] != "category_margin_floor" or rule["scope_type"] != "category"
                    or suffix != "FLOOR-" + rule["scope_value"].upper().replace("_", "-")
                    or set(condition) != {"margin_pct_lt", "basis"} or condition["basis"] != "each_line"
                    or set(action) != {"flag", "max_exception_deviation_points"}
                    or action["flag"] != "margin_below_floor"):
                raise ValueError("Malformed margin floor rule")
            _number(condition["margin_pct_lt"])
            _number(action["max_exception_deviation_points"])
        elif (rule["rule_type"] != "volume_discount" or rule["scope_type"] != "global"
              or set(condition) != {"discount_pct_gt", "basis"}
              or condition["basis"] != "each_line_and_list_weighted_deal"
              or action != {"flag": "director_discount" if suffix == "DIRECTOR" else "vp_discount"}):
            raise ValueError("Malformed discount rule")
        else:
            _number(condition["discount_pct_gt"])
    shapes = {
        "DISCOUNT-CAP": {"discount_pct_gt", "basis"},
        "MARGIN-NONPOSITIVE": {"margin_pct_lte", "basis"},
        "MARGIN-SHORTFALL": {"category_floor_shortfall_points_gt", "basis"},
        "MARGIN-EXCEPTION": {"margin_pct_gt", "category_floor_shortfall_points_gt", "category_floor_shortfall_points_lte", "basis"},
        "PAYMENT-CAP": {"payment_terms_days_gt"}, "PAYMENT-INVALID": {"payment_terms_days_not_in"},
        "PAYMENT-EXCEPTION": {"payment_terms_days_gt", "payment_terms_days_lte"},
        "CREDIT-CAP": {"credit_over_limit_pct_gt"},
        "CREDIT-EXCEPTION": {"credit_over_limit_pct_gt", "credit_over_limit_pct_lte"},
        "CREDIT-ON-HOLD": {"credit_status_eq"}, "ACCOUNT-INACTIVE": {"account_status_in"},
        "CREDIT-REVIEW": {"credit_status_eq"},
        "OVERDUE-AR": {"overdue_ar_eur_gt"}, "CONTRACT-LEGAL": {"contract_clause_eq"},
        "CONTRACT-PROHIBITED": {"contract_clause_eq"},
        "CONTRACT-INVALID": {"contract_clause_not_in"},
        "DELIVERY-LATE": {"delivery_later_than_requested"},
    }
    areas = {"DISCOUNT-CAP": "pricing", "MARGIN-NONPOSITIVE": "margin",
             "MARGIN-SHORTFALL": "margin", "MARGIN-EXCEPTION": "margin",
             "PAYMENT-CAP": "payment", "PAYMENT-INVALID": "payment",
             "PAYMENT-EXCEPTION": "payment", "CREDIT-CAP": "credit",
             "CREDIT-EXCEPTION": "credit", "CREDIT-ON-HOLD": "credit", "ACCOUNT-INACTIVE": "credit",
             "CREDIT-REVIEW": "credit", "OVERDUE-AR": "credit",
             "CONTRACT-LEGAL": "contract", "CONTRACT-PROHIBITED": "contract",
             "CONTRACT-INVALID": "contract", "DELIVERY-LATE": "delivery"}
    blockers = {"DISCOUNT-CAP", "MARGIN-NONPOSITIVE", "MARGIN-SHORTFALL",
                "PAYMENT-CAP", "PAYMENT-INVALID", "CREDIT-CAP", "CREDIT-ON-HOLD", "ACCOUNT-INACTIVE",
                "CONTRACT-PROHIBITED", "CONTRACT-INVALID"}
    for suffix, rule in by_type["PO"].items():
        block = suffix in blockers
        if (rule["scope_type"] != "global" or rule["policy_area"] != areas[suffix]
                or set(rule["condition_json"]) != shapes[suffix]
                or rule["severity"] != ("blocker" if block else "approval_required")
                or rule["required_action"] != ("reject" if block else "escalate")):
            raise ValueError(f"Malformed policy rule: {suffix}")
    if (_number(by_type["PO"]["MARGIN-NONPOSITIVE"]["condition_json"]["margin_pct_lte"]) != 0
            or _number(by_type["PO"]["MARGIN-EXCEPTION"]["condition_json"]["category_floor_shortfall_points_gt"]) != 0
            or _number(by_type["PO"]["MARGIN-SHORTFALL"]["condition_json"]["category_floor_shortfall_points_gt"])
            != _number(by_type["PO"]["MARGIN-EXCEPTION"]["condition_json"]["category_floor_shortfall_points_lte"])):
        raise ValueError("Inconsistent margin exception boundaries")
    for floor in (r for s, r in by_type["PR"].items() if s.startswith("FLOOR-")):
        if (_number(floor["action_json"]["max_exception_deviation_points"]) !=
                _number(by_type["PO"]["MARGIN-SHORTFALL"]["condition_json"]["category_floor_shortfall_points_gt"])):
            raise ValueError("Margin floor and exception disagree")
    approval_shapes = {"ROUTINE": {"highest_sales_role": "Regional_Manager"},
                       "SALES-DIRECTOR": {"highest_sales_role": "Sales_Director"},
                       "SALES-VP": {"highest_sales_role": "Sales_VP"},
                       "FINANCE": {"finance_exception": True}, "LEGAL": {"legal_exception": True}}
    for suffix, rule in by_type["AP"].items():
        expected_condition = approval_shapes.get(suffix)
        expected_role = {"ROUTINE": "Regional_Manager", "SALES-DIRECTOR": "Sales_Director",
                         "SALES-VP": "Sales_VP", "FINANCE": "Finance_Director",
                         "LEGAL": "Legal_Compliance", "VALUE-DIRECTOR": "Sales_Director",
                         "VALUE-VP": "Sales_VP"}[suffix]
        if (rule["required_role"] not in ROLES or rule["approval_sequence"] != ROLES.index(rule["required_role"])
                or rule["required_role"] != expected_role
                or (expected_condition is not None and rule["condition_json"] != expected_condition)
                or (expected_condition is None and set(rule["condition_json"]) != {"deal_commitment_eur_gt"})):
            raise ValueError(f"Malformed approval rule: {suffix}")
    if (_number(by_type["AP"]["VALUE-DIRECTOR"]["condition_json"]["deal_commitment_eur_gt"])
            >= _number(by_type["AP"]["VALUE-VP"]["condition_json"]["deal_commitment_eur_gt"])):
        raise ValueError("Invalid sales value ladder")
    if not (_number(by_type["PR"]["DIRECTOR"]["condition_json"]["discount_pct_gt"])
            < _number(by_type["PR"]["VP"]["condition_json"]["discount_pct_gt"])
            < _number(by_type["PO"]["DISCOUNT-CAP"]["condition_json"]["discount_pct_gt"])):
        raise ValueError("Invalid discount ladder")
    for kind in ("PAYMENT", "CREDIT"):
        cap_key = "payment_terms_days_gt" if kind == "PAYMENT" else "credit_over_limit_pct_gt"
        exception_key = "payment_terms_days_lte" if kind == "PAYMENT" else "credit_over_limit_pct_lte"
        lower_key = "payment_terms_days_gt" if kind == "PAYMENT" else "credit_over_limit_pct_gt"
        if not (_number(by_type["PO"][kind + "-EXCEPTION"]["condition_json"][lower_key])
                < _number(by_type["PO"][kind + "-EXCEPTION"]["condition_json"][exception_key])
                == _number(by_type["PO"][kind + "-CAP"]["condition_json"][cap_key])):
            raise ValueError(f"Invalid {kind.lower()} exception ladder")
    return by_type


def evaluate_compiled_policy(bundle):
    """Use stored rule conditions, preserving separate Pricing/Credit/Policy hits."""
    rules = _compiled_rules(bundle)
    pricing, policy, approval = (rules[x] for x in ("PR", "PO", "AP"))
    lines = bundle["lines"]
    facts = bundle["facts"]
    if not lines or len(lines) != len(facts["lines"]):
        raise ValueError("Missing line facts")
    hits, gaps = [], []
    sales_rank = 0
    finance = legal = False

    def hit(rule, area, scope="deal"):
        rule_id = next(rule[k] for k in ("pricing_rule_id", "policy_rule_id", "approval_rule_id") if k in rule)
        item = {"rule_id": rule_id, "area": area, "severity": rule.get("severity", "finding"), "scope": scope}
        if item not in hits:
            hits.append(item)

    def threshold(rule, key):
        return _number(rule["condition_json"][key])

    total = facts["deal_total"]
    listed = sum((line["list_price"] * line["quantity"] for line in lines), Decimal(0))
    if listed <= 0 or total <= 0:
        raise ValueError("Invalid deal price")
    deal_discount = (listed - total) * 100 / listed
    deal_margin = sum(((line["quoted_unit_price"] - line["standard_cost"]) * line["quantity"]
                       for line in lines), Decimal(0)) * 100 / total
    scopes = [("deal", deal_discount, deal_margin)] + [
        (line["deal_line_id"], fact["discount_pct"], fact["margin_pct"])
        for line, fact in zip(lines, facts["lines"])]
    for scope, discount, margin in scopes:
        for suffix, rank in (("DIRECTOR", 1), ("VP", 2)):
            rule = pricing[suffix]
            if discount > threshold(rule, "discount_pct_gt"):
                hit(rule, "pricing", scope)
                sales_rank = max(sales_rank, rank)
        if discount > threshold(policy["DISCOUNT-CAP"], "discount_pct_gt"):
            hit(policy["DISCOUNT-CAP"], "policy", scope)
        if margin <= threshold(policy["MARGIN-NONPOSITIVE"], "margin_pct_lte"):
            hit(policy["MARGIN-NONPOSITIVE"], "pricing", scope)
    floors = {r["scope_value"]: r for s, r in pricing.items() if s.startswith("FLOOR-")}
    for line, fact in zip(lines, facts["lines"]):
        if line["category"] not in floors:
            raise ValueError("Missing margin floor for a line category")
        floor = floors[line["category"]]
        shortfall = threshold(floor, "margin_pct_lt") - fact["margin_pct"]
        if shortfall > 0:
            scope = line["deal_line_id"]
            hit(floor, "pricing", scope)
            if shortfall > threshold(policy["MARGIN-SHORTFALL"], "category_floor_shortfall_points_gt"):
                hit(policy["MARGIN-SHORTFALL"], "policy", scope)
            elif fact["margin_pct"] > threshold(policy["MARGIN-EXCEPTION"], "margin_pct_gt"):
                hit(policy["MARGIN-EXCEPTION"], "policy", scope)
                sales_rank = 2

    terms = bundle["deal"]["terms_json"]
    days = terms.get("payment_terms_days")
    allowed_days = policy["PAYMENT-INVALID"]["condition_json"]["payment_terms_days_not_in"]
    if type(days) is not int or days not in allowed_days:
        hit(policy["PAYMENT-INVALID"], "policy")
    else:
        if days > threshold(policy["PAYMENT-CAP"], "payment_terms_days_gt"):
            hit(policy["PAYMENT-CAP"], "policy")
        elif (days > threshold(policy["PAYMENT-EXCEPTION"], "payment_terms_days_gt")
              and days <= threshold(policy["PAYMENT-EXCEPTION"], "payment_terms_days_lte")):
            hit(policy["PAYMENT-EXCEPTION"], "policy")
            finance = True
    clauses = terms.get("contract_clause_codes")
    allowed_clauses = policy["CONTRACT-INVALID"]["condition_json"]["contract_clause_not_in"]
    if not isinstance(clauses, list) or not clauses or any(code not in allowed_clauses for code in clauses):
        hit(policy["CONTRACT-INVALID"], "policy")
    else:
        for code in set(clauses):
            for suffix in ("CONTRACT-PROHIBITED", "CONTRACT-LEGAL"):
                rule = policy[suffix]
                if code == rule["condition_json"]["contract_clause_eq"]:
                    hit(rule, "policy")
                    if suffix == "CONTRACT-LEGAL":
                        legal = True

    credit = bundle["credit"]
    if bundle["customer"]["account_status"] in policy["ACCOUNT-INACTIVE"]["condition_json"]["account_status_in"]:
        hit(policy["ACCOUNT-INACTIVE"], "credit")
    if credit["credit_status"] == policy["CREDIT-ON-HOLD"]["condition_json"]["credit_status_eq"]:
        hit(policy["CREDIT-ON-HOLD"], "credit")
    elif credit["credit_status"] == policy["CREDIT-REVIEW"]["condition_json"]["credit_status_eq"]:
        hit(policy["CREDIT-REVIEW"], "credit")
        finance = True
    if facts["credit_commitments_fresh"]:
        over = facts["credit_over_limit_pct"]
        if over > threshold(policy["CREDIT-CAP"], "credit_over_limit_pct_gt"):
            hit(policy["CREDIT-CAP"], "credit")
        elif (over > threshold(policy["CREDIT-EXCEPTION"], "credit_over_limit_pct_gt")
              and over <= threshold(policy["CREDIT-EXCEPTION"], "credit_over_limit_pct_lte")):
            hit(policy["CREDIT-EXCEPTION"], "credit")
            finance = True
    else:
        gaps.append("credit_commitments_stale")
    as_of_date = bundle["run"]["as_of_at"].date()
    overdue = sum((row["outstanding_amount"] for row in bundle["receivables"]
                   if row["due_date"] < as_of_date), Decimal(0))
    if overdue > threshold(policy["OVERDUE-AR"], "overdue_ar_eur_gt"):
        hit(policy["OVERDUE-AR"], "credit")
        finance = True
    requested = bundle["deal"]["requested_delivery_date"]
    if requested:
        for line, fact in zip(lines, facts["lines"]):
            if line["fulfillment_mode"] == "digital_activation":
                continue
            earliest = fact.get("earliest_full_date")
            if earliest and earliest > requested:
                hit(policy["DELIVERY-LATE"], "policy", line["deal_line_id"])
                sales_rank = max(sales_rank, 1)
            elif earliest is None:
                gaps.append("delivery_evidence_missing:" + line["deal_line_id"])

    for suffix, rank in (("VALUE-DIRECTOR", 1), ("VALUE-VP", 2)):
        rule = approval[suffix]
        if total > threshold(rule, "deal_commitment_eur_gt"):
            hit(rule, "approval")
            sales_rank = max(sales_rank, rank)
    blocked = [item for item in hits if item["severity"] == "blocker"]
    approvals = []
    if not blocked and not gaps:
        sales_suffix = ("ROUTINE", "SALES-DIRECTOR", "SALES-VP")[sales_rank]
        for suffix, selected in ((sales_suffix, True), ("FINANCE", finance), ("LEGAL", legal)):
            if selected:
                rule = approval[suffix]
                approvals.append({"role": rule["required_role"], "sequence": rule["approval_sequence"],
                                  "rule_id": rule["approval_rule_id"]})
        approvals.sort(key=lambda x: x["sequence"])
    return {
        "status": "blocked" if blocked else "needs_evidence" if gaps else "approval_required",
        "deal_discount_pct": deal_discount, "deal_margin_pct": deal_margin,
        "overdue_ar_eur": overdue, "rule_hits": hits, "hard_blocks": blocked,
        "evidence_gaps": gaps, "required_approvals": approvals,
        "policy_set_code": bundle["run"]["applied_policy_set_code"],
    }
