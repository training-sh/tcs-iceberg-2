"""Explicit SQL scoped to the exercise objects."""
from .settings import LAKE_SCHEMA, MYSQL_PREFIX, STORAGE_ROOT, TRINO_LESSON_SCHEMA


def source_lines():
    return f"""
SELECT i.line_id, o.order_id, o.order_date, c.country,
       CAST(i.quantity * i.unit_price AS DECIMAL(18,2)) AS line_amount
FROM {MYSQL_PREFIX}order_items i
JOIN {MYSQL_PREFIX}orders o ON i.order_id = o.order_id
JOIN {MYSQL_PREFIX}customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'COMPLETED'
  AND i.line_id IS NOT NULL AND o.order_id IS NOT NULL
  AND o.order_date IS NOT NULL AND c.country IS NOT NULL
  AND i.quantity > 0 AND i.unit_price >= 0
"""


SOURCE_TOTALS = f"""
SELECT count(*), count(DISTINCT order_id), CAST(sum(line_amount) AS VARCHAR)
FROM ({source_lines()}) accepted
"""
LESSON_TOTALS = f"""
SELECT count(*), count(DISTINCT order_id), CAST(sum(line_amount) AS VARCHAR)
FROM {TRINO_LESSON_SCHEMA}.silver_order_lines
"""
CREATE_SCHEMA = f"""
CREATE SCHEMA IF NOT EXISTS {LAKE_SCHEMA}
WITH (location = '{STORAGE_ROOT}')
"""
CREATE_INPUT = f"""
CREATE TABLE IF NOT EXISTS {LAKE_SCHEMA}.sales_input (
    line_id BIGINT, order_id BIGINT, order_date DATE,
    country VARCHAR, line_amount DECIMAL(18,2)
)
WITH (format = 'PARQUET', format_version = 2,
      location = '{STORAGE_ROOT}/sales_input')
"""
MERGE_INPUT = f"""
MERGE INTO {LAKE_SCHEMA}.sales_input t
USING ({source_lines()}) s ON t.line_id = s.line_id
WHEN NOT MATCHED THEN INSERT (line_id, order_id, order_date, country, line_amount)
VALUES (s.line_id, s.order_id, s.order_date, s.country, s.line_amount)
"""


def expected_groups(source):
    return f"""
SELECT order_date, country, count(DISTINCT order_id) AS completed_orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM {source} GROUP BY order_date, country
"""


def report(table):
    return f"""
SELECT CAST(order_date AS VARCHAR), country, completed_orders,
       CAST(revenue AS VARCHAR)
FROM {table} ORDER BY order_date, country
"""


def difference_count(source, target):
    return f"""
WITH expected AS ({expected_groups(source)}),
actual AS (SELECT order_date, country, completed_orders, revenue FROM {target})
SELECT count(*) FROM (
    (SELECT * FROM expected EXCEPT SELECT * FROM actual)
    UNION ALL
    (SELECT * FROM actual EXCEPT SELECT * FROM expected)
) differences
"""
