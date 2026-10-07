"""Render provisional non-buildable sellable products after the buildable master.

Price draws test schema and reader paths only. They are not source-calibrated
market prices; the final generator must rerun after the price evidence freeze.
"""

import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import random

import yaml

from validate_phase1c_data_contract import validate_payload


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "phase1c_sellable_catalogue.sql"


def quote(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "'" + str(value).replace("'", "''") + "'"


def product_rows(portfolio, costs, config, contract):
    rng = random.Random(config["random_seed"])
    by_id = {p["product_id"]: p for p in costs["products"]}
    rows = []
    for product in sorted(portfolio["products"], key=lambda p: p["product_id"]):
        if not product["is_sellable"] or product["product_id"] in by_id:
            continue
        product_id = product["product_id"]
        mode = product["fulfillment_mode"]
        attrs = product["attributes_json"]
        category = attrs["category"]
        if mode not in {"stocked_finished", "supplier_finished", "digital_activation", "scheduled_service"}:
            raise ValueError(f"unpriced buildable product {product_id}")
        attribute_mode = "digital_activation" if mode == "digital_activation" else (
            "scheduled_service" if mode == "scheduled_service" else "physical")
        errors = validate_payload("product_attributes", attrs, contract, mode=attribute_mode)
        if errors:
            raise ValueError(f"{product_id}: {errors}")
        band = config["product_catalogue"]["categories"][category]["price_eur"]
        price = Decimal(str(rng.triangular(band["p10"], band["p90"], band["p50"])))
        increment = Decimal("10") if price >= 100 else Decimal("1")
        price = (price / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment
        margin = Decimal(str(config["commercial_supply"]["standard_cost"]
                             ["target_list_margin_percent_by_category"][category]["p50"]))
        cost = (price * (1 - margin / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product_type = product["product_type"]
        if mode in ("stocked_finished", "supplier_finished"):
            billing, unit, stock_unit = "one_time", "device", "each"
        elif mode == "scheduled_service":
            billing, unit, stock_unit = "fixed_service_fee", "service_package", "not_applicable"
        else:
            billing, stock_unit = "recurring", "not_applicable"
            unit = "service_month" if category == "cloud_services_and_subscriptions" else (
                "device_year" if category in {"networking_and_connectivity", "cybersecurity"}
                else "licence_year" if category == "enterprise_software_and_licensing"
                else "coverage_year")
        if mode == "scheduled_service" and product_type != "service":
            raise ValueError(f"scheduled service type mismatch {product_id}")
        rows.append((product_id, product_id, portfolio["catalog_version"],
                     f"Synthetic fixture {product_id}", category, product_type, attrs,
                     price, cost, billing, unit, True, mode, stock_unit))
    if len(rows) != 102 or len(by_id) != 18:
        raise ValueError(f"expected 102 non-buildable sellable rows plus 18 buildable, got {len(rows)}")
    return rows


def render(rows):
    fields = ("product_id", "product_code", "catalog_version", "product_name", "category",
              "product_type", "attributes_json", "list_price", "standard_cost", "billing_model",
              "unit_of_measure", "is_sellable", "fulfillment_mode", "stock_uom")
    values = ",\n".join("  (" + ", ".join(map(quote, row)) + ")" for row in rows)
    return ("-- Provisional 102 sellable products; apply after phase1c_buildable_master.sql.\n"
            "-- Disposable PostgreSQL fixture; commercial values await sourcing and freeze.\n"
            "SET search_path TO deal_desk, public;\n"
            f"INSERT INTO products ({', '.join(fields)}) VALUES\n{values};\n"
            "DO $catalogue$\nBEGIN\n"
            "  IF (SELECT count(*) FROM products) <> 156 OR\n"
            "     (SELECT count(*) FROM products WHERE is_sellable) <> 120 OR\n"
            "     (SELECT count(*) FROM products WHERE fulfillment_mode = 'component') <> 36 OR\n"
            "     (SELECT count(DISTINCT fulfillment_mode) FROM products WHERE is_sellable) <> 5\n"
            "  THEN RAISE EXCEPTION 'Provisional catalogue coverage differs'; END IF;\n"
            "END\n$catalogue$;\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    costs = json.loads((HERE / "phase1c_build_cost_draft.json").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    output = render(product_rows(portfolio, costs, config, contract))
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != output:
            raise SystemExit("phase1c_sellable_catalogue.sql differs from generator")
    else:
        OUTPUT.write_text(output)
    print("provisional non-buildable sellable products: 102")


if __name__ == "__main__":
    main()
