"""Render a rollback-only PostgreSQL fixture from the structural/cost drafts.

The three products are examples, not a generated catalogue or calibrated prices.
"""

from pathlib import Path
import argparse
import json

from validate_phase1c_variant_cost_pilot import evaluate_build_cost_draft
import yaml


HERE = Path(__file__).resolve().parent
SELECTED_CATEGORIES = (
    "end_user_computing_and_digital_workplace",
    "servers_and_compute_infrastructure",
    "storage_and_data_protection",
)


def sql(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "'" + str(value).replace("'", "''") + "'"


def insert(table, columns, rows):
    return (f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n" +
            ",\n".join(" (" + ", ".join(sql(row[col]) for col in columns) + ")" for row in rows) + ";\n")


def render(portfolio, costs, config):
    result = evaluate_build_cost_draft(portfolio, costs, config)
    if result["errors"]:
        raise ValueError("cost draft must pass before rendering: " + "; ".join(result["errors"]))
    chosen = [next(row for row in portfolio["products"]
                   if row["fulfillment_mode"] == "make_to_order" and
                   row["attributes_json"]["category"] == category)
              for category in SELECTED_CATEGORIES]
    selected_ids = {row["product_id"] for row in chosen}
    headers = [row for row in portfolio["bom_headers"] if row["finished_product_id"] in selected_ids]
    bom_ids = {row["bom_id"] for row in headers}
    lines = [row for row in portfolio["bom_lines"] if row["bom_id"] in bom_ids]
    requirements = [row for row in portfolio["production_requirements"] if row["bom_id"] in bom_ids]
    component_ids = {row["component_product_id"] for row in lines}
    components = [row for row in portfolio["products"] if row["product_id"] in component_ids]
    price_by_id = {row["product_id"]: row for row in costs["products"]}
    product_rows = []
    for row in chosen + components:
        pid = row["product_id"]
        priced = price_by_id.get(pid)
        product_rows.append(dict(row, product_code=pid, product_name="Synthetic fixture " + pid,
                                 category=row["attributes_json"].get("category", "components"),
                                 list_price=priced["product_list_price_eur"] if priced else 0,
                                 standard_cost=priced["product_standard_cost_eur"] if priced else
                                 costs["component_standard_costs_eur"][pid],
                                 billing_model="one_time" if priced else "not_applicable",
                                 unit_of_measure="device" if priced else "component_unit",
                                 stock_uom="each" if priced else "component_unit"))
    header_rows = [dict(row, bom_version="V1") for row in headers]
    statements = ["-- Rendered from the Phase 1C structural and synthetic cost drafts.\n",
                  "-- Disposable fixture: never a production catalogue.\n",
                  "\\set ON_ERROR_STOP on\nBEGIN;\nSET search_path TO deal_desk, public;\n"]
    statements.append(insert("products", ("product_id", "product_code", "catalog_version",
                     "product_name", "category", "product_type", "attributes_json",
                     "list_price", "standard_cost", "billing_model", "unit_of_measure",
                     "is_sellable", "fulfillment_mode", "stock_uom"), product_rows))
    statements.append(insert("bom_headers", ("bom_id", "finished_product_id", "catalog_version",
                     "bom_version", "configuration_signature_json", "output_quantity",
                     "effective_from", "effective_to", "status"), header_rows))
    statements.append(insert("bom_lines", ("bom_line_id", "bom_id", "component_product_id",
                     "required_quantity_per_output", "scrap_pct", "substitute_group_code",
                     "priority", "is_mandatory"), lines))
    statements.append(insert("production_requirements", ("requirement_id", "bom_id", "operation_seq",
                     "capability_code", "resource_type", "setup_hours", "hours_per_unit",
                     "batch_size", "status"), requirements))
    statements.append("""
DO $fixture$
DECLARE
    product_count INTEGER;
    bom_count INTEGER;
    component_count INTEGER;
    bad_count INTEGER;
BEGIN
    SELECT count(*) INTO product_count FROM products WHERE fulfillment_mode = 'make_to_order';
    SELECT count(*) INTO bom_count FROM bom_headers;
    SELECT count(*) INTO component_count FROM products WHERE fulfillment_mode = 'component';
    IF product_count <> 3 OR bom_count <> 5 OR component_count <> COMPONENT_COUNT THEN
        RAISE EXCEPTION 'representative master slice counts differ: %, %, %',
            product_count, bom_count, component_count;
    END IF;

    SELECT count(*) INTO bad_count
    FROM bom_lines l JOIN bom_headers h USING (bom_id)
      JOIN products part ON part.product_id = l.component_product_id
      JOIN products finished ON finished.product_id = h.finished_product_id
    WHERE NOT (part.attributes_json->'supported_platforms' ?
               (finished.attributes_json->>'build_platform'));
    IF bad_count <> 0 THEN
        RAISE EXCEPTION 'component platform mismatch in master slice';
    END IF;

    WITH selected_material AS (
        SELECT h.bom_id, h.finished_product_id,
               sum(l.required_quantity_per_output / h.output_quantity /
                   (1 - l.scrap_pct / 100) * part.standard_cost) AS material
        FROM bom_headers h JOIN bom_lines l USING (bom_id)
          JOIN products part ON part.product_id = l.component_product_id
        WHERE l.substitute_group_code IS NULL
           OR (h.bom_id = 'BOM-001' AND l.component_product_id = 'COMP-NETWORK_AND_POWER-001')
        GROUP BY h.bom_id, h.finished_product_id
    ), labor AS (
        SELECT bom_id, sum(setup_hours + hours_per_unit) * 30 AS labor_cost
        FROM production_requirements
        WHERE resource_type = 'workforce' AND status = 'active'
        GROUP BY bom_id
    ), rolled AS (
        SELECT m.bom_id, m.finished_product_id, finished.standard_cost,
               (m.material + labor.labor_cost) * 1.1 AS rollup
        FROM selected_material m JOIN labor USING (bom_id)
          JOIN products finished ON finished.product_id = m.finished_product_id
    )
    SELECT count(*) FILTER (WHERE abs(standard_cost - rollup) / rollup > 0.05)
           + count(*) FILTER (WHERE standard_cost < rollup)
           + CASE WHEN count(*) = 5 THEN 0 ELSE 1 END INTO bad_count FROM rolled;
    IF bad_count <> 0 THEN
        RAISE EXCEPTION 'BOM rollup or shared conservative cost failed in PostgreSQL';
    END IF;
END
$fixture$;
ROLLBACK;
""".replace("COMPONENT_COUNT", str(len(components))))
    return "\n".join(statements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in SQL is stale")
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    output = HERE / "phase1c_master_slice.sql"
    result = render(portfolio, costs, config)
    if args.check:
        if not output.exists() or output.read_text() != result:
            raise SystemExit("representative master SQL is stale; rerun render_phase1c_master_slice.py")
    else:
        output.write_text(result)


if __name__ == "__main__":
    main()
