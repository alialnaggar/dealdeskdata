"""Read-only, run-scoped evidence for the six Deal Desk agents.

Requires psycopg 3. This module returns facts and evidence, never approvals. A
missing or stale source remains visible but cannot become a confirmed promise.
"""

from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_CEILING
from zoneinfo import ZoneInfo
import json

from psycopg.rows import dict_row


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


def _supply_findings(bundle, as_of):
    """Conservative dated supply facts, aggregated across lines sharing a BOM."""
    lines, stock, receipts = bundle["lines"], bundle["inventory"], bundle["inbound_supply"]
    lanes = {x["origin_location_id"]: x for x in bundle["shipping_lanes"]}
    demands = defaultdict(lambda: Decimal(0))
    for line in lines:
        demands[line["product_id"]] += Decimal(line["quantity"])
    by_product = defaultdict(list)
    for row in stock:
        by_product[row["product_id"]].append(row)
    bindings = defaultdict(list)
    for row in receipts:
        if (row["status"] == "Confirmed" and row["confirmed_at"] and row["confirmed_at"] <= as_of
            and (row["valid_until"] is None or row["valid_until"] > as_of)
            and (row["purchase_order_id"] is not None or row["evidence_ref"])
            and (row["purchase_order_id"] is None or
                 (row["po_status"] in ("Confirmed", "Delayed") and row["po_confirmed_at"] <= as_of
                  and row["destination_location_id"] == row["location_id"]))):
            bindings[row["product_id"]].append(row)
    result = {"demand_by_product": dict(demands), "stock": {}, "binding_receipts": {}, "assembly": {}}
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
        options = []
        for row in by_product[product]:
            lane = lanes.get(row["location_id"])
            if not lane:
                continue
            local = row["snapshot_at"].astimezone(ZoneInfo(lane["origin_time_zone"]))
            free_stock = row["quantity_on_hand"] - row["quantity_allocated"] if _fresh(row, as_of) else Decimal(0)
            valid = sorted((x for x in bindings[product] if x["location_id"] == row["location_id"]), key=lambda x: x["expected_date"])
            running = free_stock
            if running >= demand:
                dispatch, arrival = _arrival(local.date(), local.time(), lane)
                options.append({"stock_id": row["inventory_id"], "supply_ids": [], "dispatch": dispatch, "arrival": arrival, "quantity": running})
            for receipt in valid:
                running += receipt["quantity"] - receipt["quantity_allocated"]
                if running >= demand:
                    dispatch, arrival = _arrival(receipt["expected_date"], None, lane)
                    options.append({"stock_id": row["inventory_id"], "supply_ids": [x["supply_id"] for x in valid if x["expected_date"] <= receipt["expected_date"]],
                                    "dispatch": dispatch, "arrival": arrival, "quantity": running})
                    break
        line_fact = next(f for f in bundle["facts"]["lines"] if f["line_id"] == line["deal_line_id"])
        line_fact["shipping_options"] = options
        line_fact["shipping_by_request"] = any(o["arrival"] <= bundle["deal"]["requested_delivery_date"] for o in options) if bundle["deal"]["requested_delivery_date"] else None
        available_now = max((x["quantity_on_hand"] - x["quantity_allocated"] for x in by_product[product] if _fresh(x, as_of)), default=Decimal(0))
        line_fact["available_now_quantity"] = min(demand, available_now)
        line_fact["partial_available_now"] = (bool(bundle["deal"]["terms_json"].get("allow_partial_delivery"))
                                              and 0 < available_now < demand)
        if options:
            line_fact["earliest_full_date"] = min(x["arrival"] for x in options)
            line_fact["fulfillment_status"] = "confirmed_by_date" if line_fact["shipping_by_request"] else "late_alternative"
        elif not by_product[product] and line["fulfillment_mode"] == "make_to_order":
            line_fact["fulfillment_status"] = "pending_production_check"
        elif by_product[product] and not any(_fresh(x, as_of) for x in by_product[product]):
            line_fact["fulfillment_status"] = "unknown"
        else:
            line_fact["fulfillment_status"] = "conditional" if any(x["product_id"] == product for x in bundle["supplier_offers"]) else "infeasible"
        if not options and line["fulfillment_mode"] == "supplier_finished":
            line_fact["supplier_offer_days"] = [x["lead_days_mode"] for x in bundle["supplier_offers"] if x["product_id"] == product]
    for b in bundle["bom"]:
        product = b["finished_product_id"]
        free_finished = sum((x["quantity_on_hand"] - x["quantity_allocated"] for x in by_product[product] if _fresh(x, as_of)), Decimal(0))
        build = max(Decimal(0), demands[product] - free_finished)
        components = {}
        for bl in bundle["bom_lines"]:
            if bl["bom_id"] != b["bom_id"]:
                continue
            units = (build / b["output_quantity"] * bl["required_quantity_per_output"] /
                     (Decimal(1) - bl["scrap_pct"] / 100))
            components[bl["component_product_id"]] = units
        hours = {}
        for req in bundle["requirements"]:
            if req["bom_id"] == b["bom_id"]:
                hours[(req["capability_code"], req["resource_type"])] = (
                    (build / req["batch_size"]).to_integral_value(rounding=ROUND_CEILING) * req["setup_hours"]
                    + build * req["hours_per_unit"])
        fitting = []
        for cap in bundle["production_capacity"]:
            need = hours.get((cap["capability_code"], cap["resource_type"]))
            if need is None or cap["status"] != "active" or not _fresh(cap, as_of):
                continue
            material = all(sum((x["quantity_on_hand"]-x["quantity_allocated"] for x in by_product[component]
                                if x["location_id"] == cap["location_id"] and _fresh(x, as_of)), Decimal(0))
                           + sum((x["quantity"]-x["quantity_allocated"] for x in bindings[component]
                                  if x["location_id"] == cap["location_id"] and x["expected_date"] <= cap["capacity_date"]), Decimal(0)) >= units
                           for component, units in components.items())
            if material and cap["available_capacity_hours"]-cap["allocated_capacity_hours"] >= need:
                fitting.append(cap["capacity_date"])
        result["assembly"][product] = {"bom_id": b["bom_id"], "build_units": build,
            "component_demand": components, "required_hours": hours, "first_fitting_day": min(fitting) if fitting else None}
        if build > 0:
            for fact in bundle["facts"]["lines"]:
                if next(line for line in lines if line["deal_line_id"] == fact["line_id"])["product_id"] == product:
                    fact["production_status"] = "feasible_uncommitted" if fitting else "infeasible_without_replenishment"
    return result


def read_run(conn, run_id):
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
            matching = [r for r in compatibility if r["rule_type"] == "installation_eligibility" and r["source_product_id"] in (None, line["product_id"])
                        and r["condition_json"].get("country_code") in (None, deal["destination_country_code"])
                        and r["condition_json"].get("region") in (None, deal["destination_region"])]
            fact["installation"] = "unknown" if not matching else ("ineligible" if any(r["condition_json"].get("eligible") is False for r in matching) else "eligible")
            fact["installation_evidence"] = [r["compatibility_rule_id"] for r in matching]
        if line["fulfillment_mode"] == "digital_activation":
            months = deal["terms_json"].get("contract_months")
            per_period = line["configuration_json"].get("units_per_period")
            if not months or not per_period or line["quantity"] != months * per_period:
                fact["digital"] = {"status": "invalid_quantity"}
            else:
                term = f"{months}m"
                pools = [p for p in digital if p["product_id"] == line["product_id"] and p["configuration_signature_json"] == line["attributes_json"]
                         and p["region_code"] == deal["destination_country_code"] and p["term_code"] == term]
                selected = []
                for p in pools:
                    fresh = _fresh(p, as_of)
                    binding = (p["commitment_status"] == "binding" and p["confirmed_at"] <= as_of < p["valid_until"] and bool(p["evidence_ref"]))
                    selected.append({"id": p["digital_capacity_id"], "free": p["capacity_total"] - p["quantity_allocated"], "fresh": fresh,
                                     "binding": binding, "activation_lead_days": p["activation_lead_days"]})
                if any(p["fresh"] and p["binding"] and p["free"] >= per_period for p in selected):
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

    bundle = {"run": run, "deal": deal, "lines": lines, "credit": credit, "receivables": ar, "payments": payments,
            "rules": rules, "compatibility": compatibility, "bom": bom, "bom_lines": bom_lines, "requirements": requirements,
            "inventory": inventory, "inbound_supply": supply, "supplier_offers": offers,
            "production_capacity": capacities, "digital_capacity": digital, "shipping_lanes": lanes, "facts": facts}
    facts["supply"] = _supply_findings(bundle, as_of)
    return bundle
