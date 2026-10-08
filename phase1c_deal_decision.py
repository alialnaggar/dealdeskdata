"""Assemble a conservative, read-only decision package for one Phase 1C run.

The reader owns source selection and calculations; compiled rules own commercial
thresholds. This module attributes their findings to specialists and gates the
final route. It does not run LLM agents, record approvals, or reserve supply.
"""

from phase1c_policy_decision import evaluate_compiled_policy


PHYSICAL_MODES = {"stocked_finished", "supplier_finished", "make_to_order"}


def assemble_deal_decision(bundle):
    """Return specialist findings and a final gate for a compiled-policy run.

    ``bundle`` is the output of ``read_run(..., commercial_rule_mode="compiled")``.
    Any missing essential result is a visible evidence gap, never an approval.
    """
    commercial = evaluate_compiled_policy(bundle)
    lines = bundle["lines"]
    facts = bundle["facts"]["lines"]
    if len(lines) != len(facts) or not lines:
        raise ValueError("Missing or misaligned line findings")

    configuration = []
    fulfillment = []
    config_blocks = []
    revisions = []
    evidence_gaps = list(commercial["evidence_gaps"])
    commitments = []

    for line, fact in zip(lines, facts):
        line_id = line["deal_line_id"]
        if fact["line_id"] != line_id:
            raise ValueError("Misaligned line finding")
        config_reasons = []
        if not line["is_active"] or not line["is_sellable"]:
            config_reasons.append("product_inactive_or_not_sellable")
        if line["fulfillment_mode"] == "make_to_order":
            matching = [b for b in bundle["bom"] if b["finished_product_id"] == line["product_id"]
                        and b["configuration_signature_json"] == line["configuration_json"]]
            if len(matching) != 1:
                config_reasons.append("configured_bom_missing_or_ambiguous")
        elif line["fulfillment_mode"] == "digital_activation":
            if fact.get("digital", {}).get("status") == "invalid_quantity":
                config_reasons.append("digital_billable_quantity_invalid")
        elif line["fulfillment_mode"] == "scheduled_service":
            pass  # Coverage and an uncommitted slot are evaluated below.
        elif line["fulfillment_mode"] not in PHYSICAL_MODES:
            config_reasons.append("unsupported_fulfillment_mode")
        for reason in config_reasons:
            config_blocks.append({"line_id": line_id, "code": reason})
        configuration.append({"line_id": line_id, "status": "invalid" if config_reasons else "valid",
                              "codes": config_reasons,
                              "bom_ids": [b["bom_id"] for b in bundle["bom"]
                                          if b["finished_product_id"] == line["product_id"] and
                                          b["configuration_signature_json"] == line["configuration_json"]]})

        if line["fulfillment_mode"] == "digital_activation":
            status = fact.get("digital", {}).get("status", "unknown")
            source_ids = [p["id"] for p in fact.get("digital", {}).get("pools", [])]
            date = line["requested_activation_date"] if status == "confirmed_by_date" else None
            if status in ("binding_candidate", "unknown"):
                evidence_gaps.append(f"digital_confirmation_missing:{line_id}")
            elif status == "conditional":
                commitments.append({"line_id": line_id, "code": "digital_offer_not_binding"})
        elif line["fulfillment_mode"] == "scheduled_service":
            service = fact.get("service", {})
            status = service.get("status", "unknown")
            source_ids = service.get("coverage_rule_ids", [])
            date = None  # Coverage does not establish an available service slot.
            if status == "infeasible":
                revisions.append({"line_id": line_id, "code": "service_coverage_or_date_unsupported"})
            elif status == "conditional":
                commitments.append({"line_id": line_id, "code": "service_slot_uncommitted"})
            else:
                evidence_gaps.append(f"service_coverage_missing:{line_id}")
        else:
            status = fact.get("fulfillment_status", "unknown")
            source_ids = [s for option in fact.get("shipping_options", [])
                          for s in ([option["stock_id"]] if option.get("stock_id") else [])
                          + option.get("supply_ids", [])]
            if fact.get("selected_bom_id"):
                source_ids.append(fact["selected_bom_id"])
                plan = bundle["facts"]["supply"].get("assembly_by_bom", {}).get(
                    fact["selected_bom_id"], {})
                source_ids.extend(plan.get("candidate_evidence_ids", []))
            date = fact.get("earliest_full_date")
            if status == "late_alternative" or (status == "feasible_uncommitted"
                                                 and fact.get("shipping_by_request") is False):
                revisions.append({"line_id": line_id, "code": "requested_date_not_supported"})
            elif status == "infeasible" or fact.get("production_status") == "infeasible_without_replenishment":
                revisions.append({"line_id": line_id, "code": "supply_or_capacity_shortfall"})
            elif status in ("unknown", "pending_production_check"):
                evidence_gaps.append(f"fulfillment_evidence_missing:{line_id}")
            elif status in ("conditional", "feasible_uncommitted"):
                commitments.append({"line_id": line_id, "code": "supply_or_production_not_committed"})
            elif status != "confirmed_by_date":
                evidence_gaps.append(f"fulfillment_status_unsupported:{line_id}")
        installation = fact.get("installation") if line["installation_requested"] else "not_requested"
        if installation == "ineligible":
            config_blocks.append({"line_id": line_id, "code": "installation_ineligible"})
        elif installation == "unknown":
            evidence_gaps.append(f"installation_eligibility_missing:{line_id}")
        fulfillment.append({"line_id": line_id, "mode": line["fulfillment_mode"], "status": status,
                            "requested_quantity": line["quantity"],
                            "quantity_by_requested_date": fact.get("quantity_by_requested_date")
                            if line["fulfillment_mode"] in PHYSICAL_MODES else None,
                            "earliest_full_date": date, "installation": installation,
                            "source_ids": sorted(set(source_ids)),
                            "tentative": status == "feasible_uncommitted"})

    for finding in bundle["facts"].get("compatibility", []):
        if finding["status"] in ("fail", "unsupported"):
            if finding["severity"] == "blocker":
                config_blocks.append({"code": "compatibility_rule_failed",
                                      "rule_id": finding["compatibility_rule_id"],
                                      "detail": finding["detail"]})
            else:
                evidence_gaps.append(f"compatibility_rule_failed:{finding['compatibility_rule_id']}")
        elif finding["status"] == "unknown":
            evidence_gaps.append(f"compatibility_rule_unknown:{finding['compatibility_rule_id']}")

    rollup_gaps = []
    supply = bundle["facts"]["supply"]
    cost_plans = supply.get("assembly_by_bom") or supply["assembly"]
    for key, plan in cost_plans.items():
        rollup = plan.get("cost_rollup")
        if rollup and not rollup["within_5_pct"]:
            rollup_gaps.append(f"assembly_cost_disagreement:{key}")
    evidence_gaps.extend(rollup_gaps)
    blockers = list(commercial["hard_blocks"]) + config_blocks
    if blockers:
        status = "blocked"
    elif revisions:
        status = "needs_revision"
    elif evidence_gaps:
        status = "needs_evidence"
    elif commitments:
        status = "needs_commitment"
    else:
        status = "approval_required"

    rule_hits = commercial["rule_hits"]
    specialists = {
        "configuration": configuration,
        "compatibility": bundle["facts"].get("compatibility", []),
        "pricing": {"deal_discount_pct": commercial["deal_discount_pct"],
                    "deal_margin_pct": commercial["deal_margin_pct"],
                    "rule_hits": [h for h in rule_hits if h["area"] == "pricing"],
                    "cost_evidence_gaps": rollup_gaps},
        "availability": fulfillment,
        "credit": {"credit_exposure": bundle["facts"]["credit_exposure"],
                   "credit_over_limit_pct": bundle["facts"]["credit_over_limit_pct"],
                   "rule_hits": [h for h in rule_hits if h["area"] == "credit"],
                   "commitments_fresh": bundle["facts"]["credit_commitments_fresh"]},
        "policy": {"rule_hits": [h for h in rule_hits if h["area"] == "policy"],
                   "hard_blocks": commercial["hard_blocks"]},
        "approval_routing": {"required_roles": commercial["required_approvals"] if status == "approval_required" else [],
                             "route_withheld": status != "approval_required"},
    }
    return {"run_id": bundle["run"]["run_id"], "deal_id": bundle["deal"]["deal_id"],
            "as_of_at": bundle["run"]["as_of_at"],
            "policy_set_code": bundle["run"]["applied_policy_set_code"],
            "catalog_version": bundle["run"]["catalog_version_used"],
            "status": status, "specialists": specialists, "blocks": blockers,
            "revision_reasons": revisions, "evidence_gaps": sorted(set(evidence_gaps)),
            "uncommitted_paths": commitments,
            "required_approvals": specialists["approval_routing"]["required_roles"],
            "commercial_rule_hits": rule_hits,
            "note": "A required role is a review route, not an actual approval; no supply is reserved."}
