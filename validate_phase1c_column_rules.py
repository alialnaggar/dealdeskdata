"""Check field-by-field calibration contract against the 24-table SQL schema.

This guards *coverage*, not generated data quality. SQL constraints, cross-row
checks and empirical calibration still need their own execution gates.
"""

from pathlib import Path
import argparse
import json
import re

import yaml


TABLE_RE = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\);", re.S)
COLUMN_RE = re.compile(
    r"^    ([a-z]\w+)\s+"
    r"(TEXT|CHAR\(\d+\)|DATE|TIME|TIMESTAMPTZ|"
    r"NUMERIC\(\d+,\d+\)|INTEGER|BIGINT|UUID|BOOLEAN|JSONB)(.*)$",
    re.M,
)
BASIS = {"SYS", "SYN", "CAT", "CFG", "DER", "SUB"}


def schema_columns(sql):
    result = {}
    for table, body in TABLE_RE.findall(sql):
        if table in result:
            raise ValueError(f"duplicate CREATE TABLE {table}")
        result[table] = {
            name: {
                "sql_type": kind,
                "nullable": "NOT NULL" not in suffix and "PRIMARY KEY" not in suffix,
            }
            for name, kind, suffix in COLUMN_RE.findall(body)
        }
    return result


def validate(sql, contract):
    expected = schema_columns(sql)
    errors = []
    actual = contract.get("tables", {})
    if set(expected) != set(actual):
        errors.append(f"table mismatch: missing={sorted(set(expected)-set(actual))}; "
                      f"extra={sorted(set(actual)-set(expected))}")
    review = []
    for table, columns in expected.items():
        rules = actual.get(table, {})
        if set(columns) != set(rules):
            errors.append(f"{table}: missing={sorted(set(columns)-set(rules))}; "
                          f"extra={sorted(set(rules)-set(columns))}")
        for name, shape in columns.items():
            row = rules.get(name)
            if not isinstance(row, dict):
                continue
            for key, value in shape.items():
                if row.get(key) != value:
                    errors.append(f"{table}.{name}: SQL {key} drift")
            if not set(str(row.get("basis", "")).split("+")) <= BASIS:
                errors.append(f"{table}.{name}: unknown evidence basis")
            for key in ("basis", "generation", "validation"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    errors.append(f"{table}.{name}: missing {key}")
            if row.get("review_before_generation"):
                review.append(f"{table}.{name}: {row['review_before_generation']}")
    return {
        "tables": len(expected),
        "columns": sum(map(len, expected.values())),
        "errors": errors,
        "review_before_generation": review,
        "ready_for_generation": not errors and not review,
    }


def main():
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--schema", type=Path, default=here / "schema.sql")
    parser.add_argument("--contract", type=Path, default=here / "phase1c_column_rules.yaml")
    args = parser.parse_args()
    result = validate(args.schema.read_text(encoding="utf-8"),
                      yaml.safe_load(args.contract.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
