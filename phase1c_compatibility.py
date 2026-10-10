"""Small, auditable compatibility predicate evaluator for reader findings."""


SUPPORTED_ATTRIBUTE_OPERATORS = {"equals", "not_equals", "in", "contains", "exists"}


def _path_value(value, path):
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def _line_scope(lines, rule):
    source = rule.get("source_product_id")
    source_lines = [line for line in lines if source is None or line["product_id"] == source]
    if rule["scope_type"] == "line":
        return [[line] for line in source_lines]
    if rule["scope_type"] == "configured_group":
        grouped = {}
        for line in source_lines:
            key = line.get("fulfillment_group_code") or line["deal_line_id"]
            grouped.setdefault(key, [])
        for line in lines:
            key = line.get("fulfillment_group_code") or line["deal_line_id"]
            if key in grouped:
                grouped[key].append(line)
        return list(grouped.values())
    return [list(lines)] if lines else []


def _attribute_matches(value, exists, operator, expected):
    if operator == "exists":
        return exists is bool(expected)
    if not exists:
        return False
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "in":
        return isinstance(expected, list) and value in expected
    if operator == "contains":
        return isinstance(value, (list, str, dict)) and expected in value
    return None


def evaluate_compatibility(lines, deal, rules):
    """Evaluate generic rules and return findings without making a decision.

    Installation eligibility has a separate reader helper because its legacy
    fixture grammar carries destination region directly. This function handles
    the other four typed predicate families.
    """
    findings = []
    for rule in rules:
        rule_type = rule["rule_type"]
        if rule_type == "installation_eligibility":
            continue
        condition = rule["condition_json"]
        status = "unknown"
        detail = "predicate could not be evaluated"
        scopes = _line_scope(lines, rule)
        if rule_type in {"requires_product", "excludes_product"}:
            if condition.get("operator") != "present":
                status, detail = "unsupported", "product predicate operator is unsupported"
            else:
                source = rule.get("source_product_id")
                target = rule.get("target_product_id")
                relevant_scopes = [scope for scope in scopes
                                   if any(line["product_id"] == source for line in scope)]
                if not relevant_scopes:
                    status, detail = "not_applicable", "source product is not in the deal"
                elif rule_type == "requires_product":
                    status = ("pass" if all(any(line["product_id"] == target for line in scope)
                                            for scope in relevant_scopes) else "fail")
                    detail = "required product is present" if status == "pass" else "required product is missing"
                else:
                    status = ("fail" if any(any(line["product_id"] == target for line in scope)
                                           for scope in relevant_scopes) else "pass")
                    detail = "excluded product is present" if status == "fail" else "excluded product is absent"
        elif rule_type == "attribute_constraint":
            attribute = condition.get("attribute")
            operator = condition.get("operator")
            if not isinstance(attribute, str) or operator not in SUPPORTED_ATTRIBUTE_OPERATORS:
                status, detail = "unsupported", "attribute predicate operator or path is unsupported"
            else:
                checks = []
                for scope in scopes:
                    source_lines = [line for line in scope if rule.get("source_product_id") is None
                                    or line["product_id"] == rule["source_product_id"]]
                    for line in source_lines:
                        product_attrs = line.get("attributes_json") or {}
                        config_attrs = line.get("configuration_json") or {}
                        merged = {**product_attrs, **config_attrs}
                        value, exists = _path_value(merged, attribute)
                        checks.append(_attribute_matches(value, exists, operator, condition.get("expected")))
                if checks:
                    status = "pass" if all(check is True for check in checks) else "fail"
                    detail = "attribute constraint matched" if status == "pass" else "attribute constraint failed"
                else:
                    status, detail = "not_applicable", "source product is not in the deal"
        elif rule_type == "required_deal_field":
            field = condition.get("field")
            value, exists = _path_value(deal, field) if isinstance(field, str) else (None, False)
            present = exists and value is not None and value != "" and value != []
            status = "pass" if present else "fail"
            detail = "required deal field is present" if present else "required deal field is missing"
        else:
            status, detail = "unsupported", "compatibility rule type is unsupported"
        findings.append({
            "compatibility_rule_id": rule["compatibility_rule_id"],
            "rule_type": rule_type,
            "scope_type": rule["scope_type"],
            "severity": rule["severity"],
            "status": status,
            "message": rule["message"],
            "detail": detail,
        })
    return findings
