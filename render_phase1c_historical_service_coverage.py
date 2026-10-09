"""Provisional synthetic service eligibility, independent of deal submissions.

Three countries are explicitly covered. One region in each covered country is
explicitly ineligible, and countries without a coverage record remain unknown.
Eligibility never represents an appointment or a committed service slot.
"""

import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "phase1c_historical_service_coverage.sql"
COVERED = ("DE", "NL", "BE")
UNSUPPORTED = {"DE": "DE-BY", "NL": "NL-NB", "BE": "BE-WAL"}


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def build(portfolio, contract, config):
    products = sorted((p for p in portfolio["products"]
                       if p["fulfillment_mode"] == "scheduled_service"),
                      key=lambda p: p["product_id"])
    if len(products) != 22:
        raise ValueError("scheduled service catalogue drift")
    target = config["fulfillment_production_calibration"]["proposed_parameters"][
        "installation_eligibility"]["service_countries_supported_of_five"]
    if len(COVERED) != target:
        raise ValueError("configured service country count drift")
    regions = contract["controlled_vocabularies"]["destination_regions"]
    if set(COVERED) - set(regions) or any(UNSUPPORTED[country] not in regions[country]
                                          for country in COVERED):
        raise ValueError("service region vocabulary drift")
    rows = []
    for product in products:
        for country in COVERED:
            for region in regions[country]:
                eligible = region != UNSUPPORTED[country]
                condition = json.dumps({"country_code": country, "region": region,
                                        "eligible": eligible}, sort_keys=True)
                rid = f"HIST-SERVICE-{product['product_id']}-{region}"
                rows.append("(" + ", ".join((
                    quote(rid), quote(portfolio["catalog_version"]),
                    quote("Synthetic service coverage " + region),
                    quote("installation_eligibility"), quote("line"),
                    quote(product["product_id"]), quote(condition) + "::jsonb",
                    quote("blocker"), quote("Service coverage or exclusion"), "100", "TRUE"
                )) + ")")
    return ("-- Provisional synthetic eligibility; no service appointments are represented.\n"
            "SET search_path TO deal_desk, public;\n"
            "INSERT INTO compatibility_rules (compatibility_rule_id, catalog_version, rule_name, "
            "rule_type, scope_type, source_product_id, condition_json, severity, message, "
            "priority, is_active) VALUES\n" + ",\n".join(rows) + ";\n")


def main():
    portfolio = json.loads((HERE / "phase1c_portfolio_draft.json").read_text())
    contract = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
    config = yaml.safe_load((HERE / "calibration_config.yaml").read_text())
    sql = build(portfolio, contract, config)
    OUTPUT.write_text(sql)
    print("Rendered provisional service coverage rules")


if __name__ == "__main__":
    main()
