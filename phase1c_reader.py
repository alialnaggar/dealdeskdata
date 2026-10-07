"""Read-only, run-scoped evidence for the six Deal Desk agents.

Requires psycopg 3. This module returns facts and evidence, never approvals. A
missing or stale source remains visible but cannot become a confirmed promise.
"""

from collections import defaultdict
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from phase1c_component_units import whole_component_requirements
from phase1c_digital_units import digital_demand, digital_signature
from phase1c_bom_selection import select_bom_components
from phase1c_compatibility import evaluate_compatibility
from phase1c_horizon import (
    classify_unscheduled_build,
    components_waiting_beyond_capacity_horizon,
    has_fresh_capacity_evidence,
)
from zoneinfo import ZoneInfo
import json
from pathlib import Path

from psycopg.rows import dict_row

from phase1c_policy_decision import evaluate_compiled_policy


def _rows(conn, query, args=()):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, args)
        return cur.fetchall()


def _one(conn, query, args=()):
    rows = _rows(conn, query, args)
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one run/deal, found {len(rows)}")
    return rows[0]


def _latest(rows, key, as_of, timestamp="snapshot_at"):
    found = {}
    for row in rows:
        if row[timestamp] <= as_of:
            k = tuple(json.dumps(row[x], sort_keys=True) if isinstance(row[x], (dict, list)) else row[x] for x in key)
            if k not in found or row[timestamp] > found[k][timestamp]:
                found[k] = row
    return list(found.values())


def _fresh(row, as_of, hours=24, field="snapshot_at"):
    return row[field] <= as_of and as_of - row[field] <= timedelta(hours=hours)


def _workday(start, weekdays):
    day = start
    while day.isoweekday() not in weekdays:
        day += timedelta(days=1)
    return day


def _arrival(ready_date, ready_time, lane):
    weekdays = set(lane["dispatch_weekdays_json"])
    if not weekdays:
        return None, None
    day = ready_date
    if ready_time is None or ready_time >= lane["cutoff_local_time"]:
        day += timedelta(days=1)
    dispatch = _workday(day, weekdays)
    arrival = dispatch
    for _ in range(lane["transit_workdays"]):
        arrival = _workday(arrival + timedelta(days=1), weekdays)
    return dispatch, arrival


def _add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, monthrange(year, month)[1]))


def _digital_proof(pool, line, deal, as_of, resolver):
    """Validate a trusted provider record, never a deal-supplied reference string."""
    if resolver is None or not pool["evidence_ref"]:
        return False
    proof = resolver(pool["evidence_ref"])
    if not isinstance(proof, dict):
        return False
    activation = line["requested_activation_date"]
    if activation is None:
        return False
    months = deal["terms_json"]["contract_months"]
    end = _add_months(activation, months)
    expected = {
        "evidence_ref": pool["evidence_ref"],
        "product_id": pool["product_id"],
        "provider_id": pool["provider_id"],
        "configuration_signature_json": pool["configuration_signature_json"],
        "region_code": pool["region_code"],
        "term_code": pool["term_code"],
        "capacity_unit": pool["capacity_unit"],
        "commitment_status": "binding",
    }
    if any(proof.get(key) != value for key, value in expected.items()):
        return False
    try:
        return (proof["verified_at"] <= as_of
                and as_of - proof["verified_at"] <= timedelta(days=7)
                and proof["capacity_total"] == pool["capacity_total"]
                and proof["quantity_allocated"] == pool["quantity_allocated"]
                and proof["covers_from"] <= activation
                and proof["covers_until"] >= end)
    except (KeyError, TypeError):
        return False


def load_provider_evidence(path):
    """Load a controlled provider manifest, outside salesperson deal input.

    The caller chooses this trusted file during deployment. The reader never
    accepts a manifest path or proof record from a deal or agent prompt.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(payload) != {"schema_version", "records"} or payload["schema_version"] != 1:
        raise ValueError("Unsupported provider evidence manifest")
    records = {}
    required = {"evidence_ref", "product_id", "provider_id", "configuration_signature_json", "region_code",
                "term_code", "capacity_unit", "capacity_total", "quantity_allocated",
                "commitment_status", "verified_at", "covers_from", "covers_until"}
    for raw in payload["records"]:
        if set(raw) != required or not isinstance(raw["configuration_signature_json"], dict):
            raise ValueError("Malformed provider evidence record")
        ref = raw["evidence_ref"]
        if not isinstance(ref, str) or not ref or ref in records:
            raise ValueError("Duplicate or missing provider evidence reference")
        record = dict(raw)
        record["capacity_total"] = Decimal(str(raw["capacity_total"]))
        record["quantity_allocated"] = Decimal(str(raw["quantity_allocated"]))
        record["verified_at"] = datetime.fromisoformat(raw["verified_at"].replace("Z", "+00:00"))
        record["covers_from"] = datetime.fromisoformat(raw["covers_from"]).date()
        record["covers_until"] = datetime.fromisoformat(raw["covers_until"]).date()
        if (record["verified_at"].tzinfo is None or record["covers_until"] < record["covers_from"]
                or record["quantity_allocated"] < 0 or record["capacity_total"] < record["quantity_allocated"]
                or record["commitment_status"] != "binding"):
            raise ValueError("Invalid provider evidence values")
        records[ref] = record
    return records.get


def _installation(line, deal, rules):
    matches = []
    for rule in rules:
        condition = rule["condition_json"]
        if (rule["rule_type"] != "installation_eligibility" or rule["scope_type"] != "line"
                or rule["source_product_id"] != line["product_id"]
                or set(condition) != {"country_code", "region", "eligible"}
                or not isinstance(condition["eligible"], bool)):
            continue
        if (condition["country_code"] == deal["destination_country_code"]
                and condition["region"] == deal["destination_region"]):
            matches.append(rule)
    values = {r["condition_json"]["eligible"] for r in matches}
    status = ("unknown" if len(values) != 1 else
              "eligible" if True in values else "ineligible")
    return status, [r["compatibility_rule_id"] for r in matches]


def _commercial_findings(bundle):
    """Interpret only the reviewed, small rule grammar; missing rules stay unknown."""
    rules = bundle["rules"]
    facts = bundle["facts"]
    flags = set()
    applied = []
    unsupported = []
    for line, fact in zip(bundle["lines"], facts["lines"]):
        for rule in rules["pricing_rules"]:
            if rule["scope_type"] not in ("global", "category"):
                unsupported.append(rule["pricing_rule_id"])
                continue
            if rule["scope_type"] == "category" and rule["scope_value"] != line["category"]:
                continue
            condition, action = rule["condition_json"], rule["action_json"]
            if (rule["rule_type"] != "volume_discount" or set(condition) != {"discount_pct_gt"}
                    or set(action) != {"flag"} or action["flag"] != "director_discount"):
                unsupported.append(rule["pricing_rule_id"])
                continue
            if fact["discount_pct"] > Decimal(str(condition["discount_pct_gt"])):
                flags.add(action["flag"])
                applied.append(rule["pricing_rule_id"])
    credit_exception = False
    for rule in rules["policy_rules"]:
        condition = rule["condition_json"]
        if (rule["policy_area"] != "credit" or rule["scope_type"] != "global"
                or set(condition) != {"credit_over_limit_pct_gt", "credit_over_limit_pct_lte"}
                or rule["severity"] != "approval_required"):
            unsupported.append(rule["policy_rule_id"])
            continue
        over = facts["credit_over_limit_pct"]
        if (facts["credit_commitments_fresh"] and
                Decimal(str(condition["credit_over_limit_pct_gt"])) < over <=
                Decimal(str(condition["credit_over_limit_pct_lte"]))):
            credit_exception = True
            applied.append(rule["policy_rule_id"])
    approvals = []
    for rule in rules["approval_rules"]:
        condition = rule["condition_json"]
        if condition == {"pricing_flag": "director_discount"}:
            matches = "director_discount" in flags
        elif condition == {"credit_exception": True}:
            matches = credit_exception
        else:
            unsupported.append(rule["approval_rule_id"])
            continue
        if matches:
            approvals.append({"role": rule["required_role"], "sequence": rule["approval_sequence"],
                              "rule_id": rule["approval_rule_id"]})
    approvals.sort(key=lambda x: (x["sequence"], x["rule_id"]))
    return {"pricing_status": ("unconfigured" if not rules["pricing_rules"] or unsupported else
                               "exception" if flags else "routine"),
            "credit_status": ("unknown" if not facts["credit_commitments_fresh"] else
                              "exception" if credit_exception else "unconfigured" if not rules["policy_rules"]
                              or facts["credit_over_limit_pct"] > 0 or unsupported
                              else "within_policy"),
            "flags": sorted(flags), "credit_exception": credit_exception,
            "required_approvals": approvals, "applied_rule_ids": applied,
            "unsupported_rule_ids": sorted(set(unsupported))}


def _supply_findings(bundle, as_of):
    """Conservative dated supply facts, aggregated across lines sharing a BOM."""
    lines, stock, receipts = bundle["lines"], bundle["inventory"], bundle["inbound_supply"]
    lanes = {x["origin_location_id"]: x for x in bundle["shipping_lanes"]}
    demands = defaultdict(lambda: Decimal(0))
    for line in lines:
        demands[line["product_id"]] += Decimal(line["quantity"])
    selected_boms_by_product = defaultdict(list)
    for bom in bundle["bom"]:
        selected_boms_by_product[bom["finished_product_id"]].append(bom)
    by_product = defaultdict(list)
    for row in stock:
        by_product[row["product_id"]].append(row)
    bindings = defaultdict(list)
    for row in receipts:
        if (row["status"] == "Confirmed" and row["confirmed_at"] and row["confirmed_at"] <= as_of
            and (row["valid_until"] is None or row["valid_until"] > as_of)
            and (row["purchase_order_id"] is not None or row["evidence_ref"])
            and (row["purchase_order_id"] is None or
                 (row["po_status"] == "Confirmed" and row["po_confirmed_at"] <= as_of
                  and row["destination_location_id"] == row["location_id"]))):
            bindings[row["product_id"]].append(row)
    result = {"demand_by_product": dict(demands), "stock": {}, "binding_receipts": {},
              "assembly": {}, "assembly_by_bom": {},
              "production_receipt_convention": "confirmed_receipt_usable_on_expected_date"}
    for product in set(demands) | {x["component_product_id"] for x in bundle["bom_lines"]}:
        result["stock"][product] = [{"id": x["inventory_id"], "location": x["location_id"],
            "free": x["quantity_on_hand"] - x["quantity_allocated"], "fresh": _fresh(x, as_of)} for x in by_product[product]]
        result["binding_receipts"][product] = [{"id": x["supply_id"], "location": x["location_id"],
            "free": x["quantity"] - x["quantity_allocated"], "expected_date": x["expected_date"]} for x in bindings[product]]
    for line in lines:
        if line["fulfillment_mode"] not in ("stocked_finished", "supplier_finished", "make_to_order"):
            continue
        product = line["product_id"]
        demand = demands[product]
        # Finished inventory has no configuration key. It cannot confirm either
        # variant when this deal selects multiple BOMs for the same product.
        unbound_finished = (line["fulfillment_mode"] == "make_to_order" and
                            len(selected_boms_by_product[product]) > 1)
        options = []
        locations = set() if unbound_finished else {
            x["location_id"] for x in by_product[product] + bindings[product]}
        for location in locations:
            lane = lanes.get(location)
            if not lane:
                continue
            row = next((x for x in by_product[product] if x["location_id"] == location), None)
            local = as_of.astimezone(ZoneInfo(lane["origin_time_zone"]))
            free_stock = (row["quantity_on_hand"] - row["quantity_allocated"]
                          if row and _fresh(row, as_of) else Decimal(0))
            valid = sorted((x for x in bindings[product] if x["location_id"] == location), key=lambda x: x["expected_date"])
            running = free_stock
            if running > 0:
                dispatch, arrival = _arrival(local.date(), local.time(), lane)
                options.append({"stock_id": row["inventory_id"] if row else None, "supply_ids": [],
                                "location": location, "dispatch": dispatch, "arrival": arrival,
                                "quantity": min(demand, running)})
            used = []
            for receipt in valid:
                running += receipt["quantity"] - receipt["quantity_allocated"]
                used.append(receipt["supply_id"])
                if running > 0:
                    dispatch, arrival = _arrival(max(receipt["expected_date"], local.date()), None, lane)
                    options.append({"stock_id": row["inventory_id"] if row else None,
                                    "supply_ids": used.copy(), "location": location,
                                    "dispatch": dispatch, "arrival": arrival, "quantity": min(demand, running)})
                if running >= demand:
                    break
        line_fact = next(f for f in bundle["facts"]["lines"] if f["line_id"] == line["deal_line_id"])
        if unbound_finished:
            line_fact["finished_stock_configuration_unbound"] = True
        line_fact["shipping_options"] = options
        full_options = [o for o in options if o["quantity"] >= demand]
        requested = bundle["deal"]["requested_delivery_date"]
        line_fact["shipping_by_request"] = any(o["arrival"] <= requested for o in full_options) if requested else None
        line_fact["quantity_by_requested_date"] = max((o["quantity"] for o in options if requested and o["arrival"] <= requested), default=Decimal(0))
        available_now = (Decimal(0) if unbound_finished else max(
            (x["quantity_on_hand"] - x["quantity_allocated"] for x in by_product[product] if _fresh(x, as_of)),
            default=Decimal(0)))
        line_fact["available_now_quantity"] = min(demand, available_now)
        line_fact["partial_available_now"] = (bool(bundle["deal"]["terms_json"].get("allow_partial_delivery"))
                                              and 0 < available_now < demand)
        if full_options:
            line_fact["earliest_full_date"] = min(x["arrival"] for x in full_options)
            line_fact["fulfillment_status"] = "confirmed_by_date" if line_fact["shipping_by_request"] else "late_alternative"
        elif (not by_product[product] or unbound_finished) and line["fulfillment_mode"] == "make_to_order":
            line_fact["fulfillment_status"] = "pending_production_check"
        elif by_product[product] and not any(_fresh(x, as_of) for x in by_product[product]):
            line_fact["fulfillment_status"] = "unknown"
        else:
            line_fact["fulfillment_status"] = "conditional" if any(x["product_id"] == product for x in bundle["supplier_offers"]) else "infeasible"
        if not options and line["fulfillment_mode"] == "supplier_finished":
            line_fact["supplier_offer_days"] = [x["lead_days_mode"] for x in bundle["supplier_offers"] if x["product_id"] == product]
    plans = []
    aggregate_components = defaultdict(lambda: Decimal(0))
    for b in bundle["bom"]:
        product = b["finished_product_id"]
        matching_lines = [line for line in lines if line["product_id"] == product and
                          line["configuration_json"] == b["configuration_signature_json"]]
        if not matching_lines:
            continue
        requested_build = sum((Decimal(line["quantity"]) for line in matching_lines), Decimal(0))
        free_finished = (Decimal(0) if len(selected_boms_by_product[product]) > 1 else max(
            (x["quantity_on_hand"] - x["quantity_allocated"]
             for x in by_product[product] if _fresh(x, as_of)), default=Decimal(0)))
        build = max(Decimal(0), requested_build - free_finished)
        selected_lines, substitution_groups = select_bom_components(
            b, bundle["bom_lines"], build, bundle, as_of)
        components = defaultdict(lambda: Decimal(0))
        material_cost = Decimal(0)
        for bl in selected_lines:
            per_unit = (bl["required_quantity_per_output"] / b["output_quantity"] /
                        (Decimal(1) - bl["scrap_pct"] / 100))
            components[bl["component_product_id"]] += build * per_unit
            material_cost += per_unit * bl["standard_cost"]
        for component, units in components.items():
            aggregate_components[component] += units
        steps = defaultdict(list)
        hours = defaultdict(lambda: Decimal(0))
        labor_per_unit = Decimal(0)
        for req in bundle["requirements"]:
            if req["bom_id"] != b["bom_id"]:
                continue
            need = ((build / req["batch_size"]).to_integral_value(rounding=ROUND_CEILING) * req["setup_hours"]
                    + build * req["hours_per_unit"])
            steps[req["operation_seq"]].append((req, need))
            hours[(req["capability_code"], req["resource_type"])] += need
            if req["resource_type"] == "workforce":
                labor_per_unit += req["setup_hours"] + req["hours_per_unit"]
        plan = {"bom": b, "product": product, "build": build,
                "line_ids": {line["deal_line_id"] for line in matching_lines}, "components": dict(components),
                "hours": dict(hours), "steps": steps, "material_cost_per_unit": material_cost,
                "labor_hours_for_one_unit": labor_per_unit,
                "substitution_groups": substitution_groups}
        plans.append(plan)

    # These initial physical component SKUs are indivisible. Combine demand
    # across the deal's selected builds before rounding each component once.
    stock_required = whole_component_requirements(aggregate_components)
    result["aggregate_component_stock_required"] = stock_required
    reserved_hours = defaultdict(lambda: Decimal(0))
    for plan in plans:
        product, b, build = plan["product"], plan["bom"], plan["build"]
        fitting = []
        horizon_limited = {}
        has_material_evidence = all(by_product[c] or bindings[c] for c in plan["components"])
        required_capacity_keys = {
            (req["capability_code"], req["resource_type"])
            for requirements in plan["steps"].values()
            for req, _need in requirements
        }
        has_capacity_window = has_fresh_capacity_evidence(
            required_capacity_keys,
            [dict(row, is_fresh=_fresh(row, as_of)) for row in bundle["production_capacity"]])
        for location in sorted({x["location_id"] for x in bundle["production_capacity"]}):
            caps = {(x["capability_code"], x["resource_type"], x["capacity_date"]): x
                    for x in bundle["production_capacity"] if x["location_id"] == location}
            dates = sorted({x["capacity_date"] for x in caps.values() if x["capacity_date"] >= as_of.date()})
            if dates:
                late_components = components_waiting_beyond_capacity_horizon(
                    plan["components"], stock_required,
                    [dict(row, is_fresh=_fresh(row, as_of)) for row in bundle["inventory"]],
                    [receipt for component in plan["components"] for receipt in bindings[component]],
                    location, dates[-1])
                if late_components:
                    horizon_limited[location] = late_components
            if not plan["steps"]:
                continue
            first_day = None
            last_day = None
            scheduled = []
            next_day = as_of.date()
            for seq in sorted(plan["steps"]):
                chosen = None
                for day in dates:
                    if day < next_day or day.isoweekday() > 5:
                        continue
                    if first_day is None:
                        material = all(
                            sum((x["quantity_on_hand"] - x["quantity_allocated"] for x in by_product[c]
                                 if x["location_id"] == location and _fresh(x, as_of)), Decimal(0))
                            + sum((x["quantity"] - x["quantity_allocated"] for x in bindings[c]
                                   if x["location_id"] == location and x["expected_date"] <= day), Decimal(0))
                            >= units for c, units in stock_required.items())
                        if not material:
                            continue
                    matching = []
                    for req, need in plan["steps"][seq]:
                        key = (req["capability_code"], req["resource_type"], day)
                        cap = caps.get(key)
                        if (cap is None or cap["status"] != "active" or not _fresh(cap, as_of)
                                or cap["available_capacity_hours"] - cap["allocated_capacity_hours"]
                                - reserved_hours[(location, *key)] < need):
                            break
                        matching.append((key, need))
                    else:
                        chosen = (day, matching)
                        break
                if chosen is None:
                    scheduled = []
                    break
                day, matching = chosen
                first_day = first_day or day
                last_day = day
                scheduled.extend(matching)
                next_day = _workday(day + timedelta(days=1), {1, 2, 3, 4, 5})
            if scheduled and len(scheduled) == sum(map(len, plan["steps"].values())):
                fitting.append((last_day, location, scheduled))
        best = min(fitting, key=lambda x: x[0]) if fitting else None
        if best:
            for key, need in best[2]:
                reserved_hours[(best[1], *key)] += need
        evidence_ids = set()
        if best:
            location = best[1]
            first_operation_day = min(key[2] for key, _ in best[2])
            for component in plan["components"]:
                evidence_ids.update(x["inventory_id"] for x in by_product[component]
                                    if x["location_id"] == location and _fresh(x, as_of)
                                    and x["quantity_on_hand"] > x["quantity_allocated"])
                for receipt in bindings[component]:
                    if (receipt["location_id"] == location and
                            receipt["expected_date"] <= first_operation_day and
                            receipt["quantity"] > receipt["quantity_allocated"]):
                        evidence_ids.add(receipt["supply_id"])
                        if receipt["purchase_order_id"]:
                            evidence_ids.add(receipt["purchase_order_id"])
            scheduled_keys = {key for key, _ in best[2]}
            evidence_ids.update(c["capacity_id"] for c in bundle["production_capacity"]
                                if c["location_id"] == location and _fresh(c, as_of) and
                                (c["capability_code"], c["resource_type"], c["capacity_date"])
                                in scheduled_keys)
        record = {"bom_id": b["bom_id"], "product_id": product, "line_ids": sorted(plan["line_ids"]),
            "build_units": build,
            "component_demand": plan["components"], "component_stock_required": stock_required,
            "substitution_groups": plan["substitution_groups"],
            "required_hours": plan["hours"],
            "operation_days": [key[2] for key, _ in best[2]] if best else [],
            "candidate_evidence_ids": sorted(evidence_ids),
            "first_fitting_day": best[0] if best else None,
            "capacity_horizon_limited_components": horizon_limited,
            "material_cost_per_unit": plan["material_cost_per_unit"],
            "labor_hours_for_one_unit": plan["labor_hours_for_one_unit"]}
        result["assembly_by_bom"][b["bom_id"]] = record
        if len(selected_boms_by_product[product]) == 1:
            result["assembly"][product] = record
        params = bundle.get("cost_parameters")
        if params:
            labor = plan["labor_hours_for_one_unit"] * Decimal(str(params["workforce_cost_eur_per_hour"]))
            overhead = (plan["material_cost_per_unit"] + labor) * Decimal(str(params["overhead_fraction"]))
            rollup = plan["material_cost_per_unit"] + labor + overhead
            standard = next(x["standard_cost"] for x in lines if x["product_id"] == product)
            record["cost_rollup"] = {"material": plan["material_cost_per_unit"],
                "labor": labor, "overhead": overhead, "total": rollup,
                "within_5_pct": abs(rollup - standard) <= standard * Decimal("0.05")}
        if build > 0:
            for line, fact in zip(lines, bundle["facts"]["lines"]):
                if line["deal_line_id"] not in plan["line_ids"]:
                    continue
                fact["selected_bom_id"] = b["bom_id"]
                if best:
                    fact["production_status"] = "feasible_uncommitted"
                else:
                    status, unknown_reason = classify_unscheduled_build(
                        has_material_evidence, bool(plan["steps"]), horizon_limited,
                        has_capacity_window)
                    fact["production_status"] = status
                    if unknown_reason:
                        fact["production_unknown_reason"] = unknown_reason
                        fact["fulfillment_status"] = "unknown"
                if best:
                    fact["fulfillment_status"] = "feasible_uncommitted"
                    lane = lanes.get(best[1])
                    if lane:
                        dispatch, arrival = _arrival(best[0], None, lane)
                        fact["production_shipping"] = {"dispatch": dispatch, "arrival": arrival,
                                                        "lane_id": lane["lane_id"]}
                        fact["earliest_full_date"] = arrival
                        requested = bundle["deal"]["requested_delivery_date"]
                        fact["shipping_by_request"] = arrival <= requested if requested else None
    return result


def read_run(conn, run_id, *, digital_evidence_resolver=None, cost_parameters=None,
             commercial_rule_mode="auto"):
    """Return run context, selected evidence and derived facts. No writes.

    Call inside a REPEATABLE READ READ ONLY transaction for a stable DB snapshot.
    ``as_of_at`` is the historical cutoff, independent of the transaction time.
    """
    run = _one(conn, "SELECT * FROM deal_desk.deal_runs WHERE run_id=%s", (run_id,))
    deal = _one(conn, "SELECT * FROM deal_desk.agent_visible_deals WHERE deal_id=%s", (run["deal_id"],))
    if (deal["policy_set_code"] != run["original_policy_set_code"] or
            deal["catalog_version"] != run["catalog_version_used"]):
        raise ValueError("Run context differs from submitted deal")
    as_of = run["as_of_at"]
    lines = _rows(conn, """SELECT l.*, p.product_code, p.category, p.list_price,
        p.standard_cost, p.fulfillment_mode, p.billing_model, p.unit_of_measure,
        p.attributes_json, p.catalog_version, p.is_active, p.is_sellable
        FROM deal_desk.deal_lines l JOIN deal_desk.products p USING(product_id)
        WHERE l.deal_id=%s ORDER BY l.line_number""", (deal["deal_id"],))
    if not lines or any(x["catalog_version"] != run["catalog_version_used"] for x in lines):
        raise ValueError("Missing lines or mismatched catalogue version")
    products = [x["product_id"] for x in lines]
    customer = _one(conn, "SELECT * FROM deal_desk.customers WHERE customer_id=%s", (deal["customer_id"],))
    credit = _one(conn, "SELECT * FROM deal_desk.customer_credit_profiles WHERE customer_id=%s", (deal["customer_id"],))
    ar = _latest(_rows(conn, "SELECT * FROM deal_desk.accounts_receivable WHERE customer_id=%s AND as_of_date<=%s::date", (deal["customer_id"], as_of)), ("invoice_number",), as_of.date(), "as_of_date")
    payments = _rows(conn, "SELECT * FROM deal_desk.payment_history WHERE customer_id=%s AND paid_date<=%s::date", (deal["customer_id"], as_of))
    rules = {}
    for table in ("pricing_rules", "policy_rules", "approval_rules"):
        rules[table] = _rows(conn, f"SELECT * FROM deal_desk.{table} WHERE policy_set_code=%s AND is_active ORDER BY priority, {table[:-1]}_id", (run["applied_policy_set_code"],))
    compatibility = _rows(conn, "SELECT * FROM deal_desk.compatibility_rules WHERE catalog_version=%s AND is_active ORDER BY priority, compatibility_rule_id", (run["catalog_version_used"],))
    bom = _rows(conn, """SELECT * FROM deal_desk.bom_headers WHERE finished_product_id=ANY(%s)
        AND catalog_version=%s AND status='active' AND effective_from<=%s
        AND (effective_to IS NULL OR effective_to>%s)""", (products, run["catalog_version_used"], as_of, as_of))
    bom = [b for b in bom if any(l["product_id"] == b["finished_product_id"] and l["configuration_json"] == b["configuration_signature_json"] for l in lines)]
    bom_ids = [b["bom_id"] for b in bom]
    bom_lines = _rows(conn, """SELECT bl.*, p.standard_cost FROM deal_desk.bom_lines bl
        JOIN deal_desk.products p ON p.product_id=bl.component_product_id
        WHERE bl.bom_id=ANY(%s)""", (bom_ids,))
    requirements = _rows(conn, "SELECT * FROM deal_desk.production_requirements WHERE bom_id=ANY(%s) AND status='active' ORDER BY operation_seq", (bom_ids,))
    stock_products = list(set(products + [b["component_product_id"] for b in bom_lines]))
    inventory = _latest(_rows(conn, "SELECT * FROM deal_desk.inventory WHERE product_id=ANY(%s) AND snapshot_at<=%s", (stock_products, as_of)), ("product_id", "location_id"), as_of)
    supply = _rows(conn, """SELECT s.*, po.status AS po_status, po.confirmed_at AS po_confirmed_at,
        po.destination_location_id FROM deal_desk.inbound_supply s
        LEFT JOIN deal_desk.purchase_orders po USING(purchase_order_id)
        WHERE s.product_id=ANY(%s) AND (s.confirmed_at IS NULL OR s.confirmed_at<=%s)""", (stock_products, as_of))
    offers = _rows(conn, """SELECT si.* FROM deal_desk.supplier_items si JOIN deal_desk.suppliers s USING(supplier_id)
        WHERE si.product_id=ANY(%s) AND si.is_active AND s.status='active'
        AND si.valid_from<=%s::date AND (si.valid_to IS NULL OR si.valid_to>=%s::date)""", (stock_products, as_of, as_of))
    capacities = _latest(_rows(conn, "SELECT * FROM deal_desk.production_capacity WHERE snapshot_at<=%s AND capacity_date>=%s::date", (as_of, as_of)), ("location_id", "capability_code", "resource_type", "capacity_date"), as_of)
    digital = _latest(_rows(conn, "SELECT * FROM deal_desk.digital_capacity WHERE product_id=ANY(%s) AND snapshot_at<=%s", (products, as_of)), ("product_id", "configuration_signature_json", "provider_id", "region_code", "term_code", "capacity_unit"), as_of)
    lanes = _rows(conn, """SELECT * FROM deal_desk.shipping_lanes WHERE is_active AND
        destination_country_code=%s AND destination_region=%s AND shipping_service_code=%s""", (deal["destination_country_code"], deal["destination_region"], deal["shipping_service_code"])) if deal["shipping_service_code"] else []

    total = sum((x["quantity"] * x["quoted_unit_price"] for x in lines), Decimal(0))
    exposure = credit["unbilled_committed_amount"] + sum((x["outstanding_amount"] for x in ar), Decimal(0)) + total
    facts = {"deal_total": total, "credit_exposure": exposure,
             "credit_over_limit_pct": max(Decimal(0), (exposure / credit["credit_limit"] - 1) * 100),
             "credit_commitments_fresh": _fresh(credit, as_of, field="commitments_as_of_at"), "lines": []}
    for line in lines:
        fact = {"line_id": line["deal_line_id"], "discount_pct": (line["list_price"] - line["quoted_unit_price"]) * 100 / line["list_price"],
                "margin_pct": (line["quoted_unit_price"] - line["standard_cost"]) * 100 / line["quoted_unit_price"]}
        if line["installation_requested"]:
            fact["installation"], fact["installation_evidence"] = _installation(line, deal, compatibility)
        if line["fulfillment_mode"] == "digital_activation":
            months = deal["terms_json"].get("contract_months")
            per_period = line["configuration_json"].get("units_per_period")
            valid, billed, unit = digital_demand(line["unit_of_measure"], months, per_period)
            if not valid or line["quantity"] != billed:
                fact["digital"] = {"status": "invalid_quantity"}
            else:
                term = f"{months}m"
                signature = digital_signature(line["attributes_json"], line["configuration_json"])
                pools = [p for p in digital if p["product_id"] == line["product_id"] and p["configuration_signature_json"] == signature
                         and p["region_code"] == deal["destination_country_code"] and p["term_code"] == term
                         and p["capacity_unit"] == unit]
                selected = []
                for p in pools:
                    fresh = _fresh(p, as_of)
                    binding = (p["commitment_status"] == "binding" and p["confirmed_at"] <= as_of < p["valid_until"] and bool(p["evidence_ref"]))
                    proof = binding and fresh and _digital_proof(p, line, deal, as_of, digital_evidence_resolver)
                    activation = line["requested_activation_date"]
                    ready = _workday(as_of.date(), {1, 2, 3, 4, 5})
                    for _ in range(p["activation_lead_days"]):
                        ready = _workday(ready + timedelta(days=1), {1, 2, 3, 4, 5})
                    selected.append({"id": p["digital_capacity_id"], "free": p["capacity_total"] - p["quantity_allocated"], "fresh": fresh,
                                     "binding": binding, "full_term_verified": proof, "earliest_activation_date": ready,
                                     "activation_by_request": activation is not None and ready <= activation,
                                     "activation_lead_days": p["activation_lead_days"]})
                if any(p["full_term_verified"] and p["free"] >= per_period and p["activation_by_request"] for p in selected):
                    status = "confirmed_by_date"
                elif any(p["fresh"] and p["binding"] and p["free"] >= per_period for p in selected):
                    status = "binding_candidate"
                elif any(not p["fresh"] for p in selected):
                    status = "unknown"
                elif selected:
                    status = "conditional"
                else:
                    status = "unknown"
                # A reference string does not prove full-term coverage or activation.
                # A separate evidence validator must promote a candidate to confirmed.
                fact["digital"] = {"concurrent_demand": per_period, "pools": selected, "status": status}
        facts["lines"].append(fact)

    bundle = {"run": run, "deal": deal, "lines": lines, "customer": customer, "credit": credit, "receivables": ar, "payments": payments,
            "rules": rules, "compatibility": compatibility, "bom": bom, "bom_lines": bom_lines, "requirements": requirements,
            "inventory": inventory, "inbound_supply": supply, "supplier_offers": offers,
            "production_capacity": capacities, "digital_capacity": digital, "shipping_lanes": lanes,
            "cost_parameters": cost_parameters, "facts": facts}
    facts["compatibility"] = evaluate_compatibility(lines, deal, compatibility)
    facts["supply"] = _supply_findings(bundle, as_of)
    if commercial_rule_mode not in ("auto", "reference", "compiled"):
        raise ValueError("Unknown commercial rule mode")
    compiled = (commercial_rule_mode == "compiled" or
                commercial_rule_mode == "auto" and any(
                    r["rule_type"] == "category_margin_floor" for r in rules["pricing_rules"]))
    facts["commercial"] = evaluate_compiled_policy(bundle) if compiled else _commercial_findings(bundle)
    return bundle
