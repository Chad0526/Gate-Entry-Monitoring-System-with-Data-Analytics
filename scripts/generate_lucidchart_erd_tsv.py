"""
Generate a TSV file for Lucidchart: Insert → Data → Entity relationship →
Import from SQL → "Paste the output as plain text".

Lucidchart expects tab/semicolon/comma-separated rows matching database metadata
(like INFORMATION_SCHEMA query output), NOT CREATE TABLE DDL.

Usage (from project root):
  python scripts/generate_lucidchart_erd_tsv.py
  (writes docs/lucidchart_erd_import.tsv, UTF-8 without BOM)
"""
from __future__ import annotations

import csv
import io
import os
import sys

# Allow running as `python scripts/...` from project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gate_analytics.settings")
django.setup()

from django.apps import apps
from django.contrib.auth.models import User

DBMS = "mysql"
TABLE_CATALOG = "ccb"
TABLE_SCHEMA = "public"


def _sql_type(field) -> str:
    t = field.get_internal_type()
    return {
        "AutoField": "integer",
        "BigAutoField": "bigint",
        "IntegerField": "integer",
        "PositiveIntegerField": "integer",
        "PositiveSmallIntegerField": "smallint",
        "SmallIntegerField": "smallint",
        "CharField": "varchar",
        "TextField": "text",
        "BooleanField": "boolean",
        "DateField": "date",
        "DateTimeField": "datetime",
        "TimeField": "time",
        "EmailField": "varchar",
        "GenericIPAddressField": "varchar",
        "DecimalField": "decimal",
        "FloatField": "double",
        "ForeignKey": "integer",
        "OneToOneField": "integer",
    }.get(t, "text")


def _max_len(field) -> str:
    if getattr(field, "max_length", None) is not None:
        return str(field.max_length)
    return ""


def rows_for_model(model) -> list[list[str]]:
    out: list[list[str]] = []
    table = model._meta.db_table
    for pos, field in enumerate(model._meta.fields, start=1):
        col = field.column
        dtype = _sql_type(field)
        maxlen = _max_len(field)
        constraint = ""
        ref_s = ""
        ref_t = ""
        ref_c = ""
        if field.primary_key:
            constraint = "PRIMARY KEY"
        elif getattr(field, "is_relation", False) and getattr(field, "many_to_many", False) is False:
            rel = getattr(field, "remote_field", None)
            if rel and getattr(rel, "model", None) is not None:
                constraint = "FOREIGN KEY"
                ref_s = TABLE_SCHEMA
                ref_t = field.remote_field.model._meta.db_table
                ref_c = field.remote_field.model._meta.pk.column
        out.append(
            [
                DBMS,
                TABLE_CATALOG,
                TABLE_SCHEMA,
                table,
                col,
                str(pos),
                dtype,
                maxlen,
                constraint,
                ref_s,
                ref_t,
                ref_c,
            ]
        )
    return out


def main() -> None:
    all_rows: list[list[str]] = []
    # Django auth user (FK target for many gate models)
    all_rows.extend(rows_for_model(User))
    gate_config = apps.get_app_config("gate")
    for model in sorted(gate_config.get_models(), key=lambda m: m._meta.db_table):
        all_rows.extend(rows_for_model(model))

    header = [
        "dbms",
        "table_catalog",
        "table_schema",
        "table_name",
        "column_name",
        "ordinal_position",
        "data_type",
        "character_maximum_length",
        "constraint_type",
        "referenced_table_schema",
        "referenced_table_name",
        "referenced_column_name",
    ]

    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    w.writerow(header)
    w.writerows(all_rows)
    out_path = os.path.join(_ROOT, "docs", "lucidchart_erd_import.tsv")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
    print(f"Wrote {out_path} ({len(all_rows)} data rows + header)", file=sys.stderr)


if __name__ == "__main__":
    main()
