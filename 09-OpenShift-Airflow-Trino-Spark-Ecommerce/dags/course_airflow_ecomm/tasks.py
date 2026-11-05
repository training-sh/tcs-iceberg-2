"""Task bodies: no network or database work happens while a DAG is parsed."""
from decimal import Decimal
from . import sql
from .settings import (EXPECTED_LINES, EXPECTED_ORDERS, EXPECTED_REVENUE,
                       LAKE_SCHEMA, MYSQL_PREFIX)
from .trino_http import query


def require_totals(rows):
    if len(rows) != 1 or len(rows[0]) != 3:
        raise ValueError("Expected one totals row")
    lines, orders, amount = rows[0]
    if (lines != EXPECTED_LINES or orders != EXPECTED_ORDERS
            or amount is None or Decimal(str(amount)) != Decimal(EXPECTED_REVENUE)):
        raise ValueError("Course baseline differs; inspect source counts and settings.py")


def preflight(include_lesson=True):
    if query("SELECT 1") != [[1]]:
        raise ValueError("Trino health query failed")
    for name, key in [("customers", "customer_id"), ("orders", "order_id"),
                      ("order_items", "line_id")]:
        if query(f"SELECT {key} FROM {MYSQL_PREFIX}{name} "
                 f"GROUP BY {key} HAVING count(*) > 1 OR {key} IS NULL"):
            raise ValueError(f"Invalid source key in {name}; do not continue")
    require_totals(query(sql.SOURCE_TOTALS))
    if include_lesson:
        require_totals(query(sql.LESSON_TOTALS))
    print("PREFLIGHT_PASS: source keys and expected totals")


def prepare_schema():
    query(sql.CREATE_SCHEMA)


def prepare_input():
    prepare_schema()
    query(sql.CREATE_INPUT)
    query(sql.MERGE_INPUT)
    require_totals(query(f"SELECT count(*), count(DISTINCT order_id), "
                         f"CAST(sum(line_amount) AS VARCHAR) FROM {LAKE_SCHEMA}.sales_input"))
    if query(f"SELECT line_id FROM {LAKE_SCHEMA}.sales_input "
             "GROUP BY line_id HAVING count(*) > 1"):
        raise ValueError("Duplicate staged line keys")
    print("INPUT_MERGE_PASS")


def verify_report(source, target):
    if query(sql.difference_count(source, target)) != [[0]]:
        raise ValueError("Spark report differs from independently aggregated Trino results")
    if query(f"SELECT order_date, country FROM {target} "
             "GROUP BY order_date, country HAVING count(*) > 1"):
        raise ValueError("Duplicate daily report keys")
    rows = query(sql.report(target))
    total = sum((Decimal(str(r[3])) for r in rows), Decimal("0"))
    if total != Decimal(EXPECTED_REVENUE):
        raise ValueError("Report revenue differs from the course baseline")
    print("REPORT_PASS", {"groups": len(rows), "revenue": str(total)})
    # Small JSON-compatible XCom only; never put the dataset or secrets here.
    return {"groups": len(rows), "revenue": str(total)}
