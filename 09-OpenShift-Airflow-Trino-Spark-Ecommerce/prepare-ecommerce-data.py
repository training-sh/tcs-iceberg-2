"""Prepare or check the lesson ecommerce baseline against the existing services."""
import argparse
import os
from pathlib import Path
import subprocess

ADMIN_SQL = """CREATE DATABASE IF NOT EXISTS trino_ecomm;
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX
ON trino_ecomm.* TO 'team'@'%';
"""
REMOTE_CODE = r"""
MERGES = [
r'''MERGE INTO iceberg_polaris.trino_ecomm_s01.bronze_order_lines t
USING (
    SELECT i.line_id, o.order_id, o.customer_id, i.product_id,
           o.order_date, o.order_status,
           c.customer_name, c.country, p.product_name, p.category,
           i.quantity, i.unit_price,
           CAST(i.quantity * i.unit_price AS DECIMAL(18,2)) AS line_amount
    FROM mysql.trino_ecomm.trino_s01_order_items i
    JOIN mysql.trino_ecomm.trino_s01_orders o ON i.order_id = o.order_id
    JOIN mysql.trino_ecomm.trino_s01_customers c ON o.customer_id = c.customer_id
    JOIN mysql.trino_ecomm.trino_s01_products p ON i.product_id = p.product_id
    WHERE o.order_id = 1007
) s
ON t.line_id = s.line_id
WHEN NOT MATCHED THEN INSERT (
    line_id, order_id, customer_id, product_id, order_date, order_status,
    customer_name, country, product_name, category,
    quantity, unit_price, line_amount
) VALUES (
    s.line_id, s.order_id, s.customer_id, s.product_id, s.order_date, s.order_status,
    s.customer_name, s.country, s.product_name, s.category,
    s.quantity, s.unit_price, s.line_amount
)''',
r'''MERGE INTO iceberg_polaris.trino_ecomm_s01.silver_order_lines t
USING (
    SELECT line_id, order_id, customer_id, product_id, order_date,
           customer_name, country, product_name, category,
           quantity, unit_price, line_amount
    FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines
    WHERE order_status = 'COMPLETED'
      AND line_id IS NOT NULL AND order_id IS NOT NULL
      AND customer_id IS NOT NULL AND product_id IS NOT NULL
      AND order_date IS NOT NULL AND country IS NOT NULL
      AND quantity > 0 AND unit_price >= 0
) s
ON t.line_id = s.line_id
WHEN NOT MATCHED THEN INSERT (
    line_id, order_id, customer_id, product_id, order_date,
    customer_name, country, product_name, category,
    quantity, unit_price, line_amount
) VALUES (
    s.line_id, s.order_id, s.customer_id, s.product_id, s.order_date,
    s.customer_name, s.country, s.product_name, s.category,
    s.quantity, s.unit_price, s.line_amount
)''',
r'''MERGE INTO iceberg_polaris.trino_ecomm_s01.gold_daily_sales t
USING (
    SELECT order_date, country,
           count(DISTINCT order_id) AS completed_orders,
           CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
    FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
    GROUP BY order_date, country
) s
ON t.order_date = s.order_date AND t.country = s.country
WHEN MATCHED AND (
    t.completed_orders IS DISTINCT FROM s.completed_orders
    OR t.revenue IS DISTINCT FROM s.revenue
) THEN UPDATE SET completed_orders = s.completed_orders, revenue = s.revenue
WHEN NOT MATCHED THEN INSERT (order_date, country, completed_orders, revenue)
VALUES (s.order_date, s.country, s.completed_orders, s.revenue)'''
]
import sys
sys.path.insert(0,'/opt/airflow/dags')
from course_airflow_ecomm.trino_http import query
from course_airflow_ecomm import tasks,sql
from course_airflow_ecomm.settings import MYSQL_PREFIX, TRINO_LESSON_SCHEMA
lake=TRINO_LESSON_SCHEMA
bronze=lake+'.bronze_order_lines'
location = 's3://warehouse/iceberg/' + lake.split('.')[-1]
if CHECK_ONLY:
 tasks.preflight()
 report = tasks.verify_report(lake+'.silver_order_lines', lake+'.gold_daily_sales')
 if report['groups'] != 4:
  raise ValueError('Expected four daily/country groups')
 print('ECOMMERCE_DATA_READY: 8 lines / 5 orders / 4 groups / 225.00', flush=True)
 sys.exit(0)

print('PREPARE_ICEBERG_SEED', flush=True)
query(f"CREATE SCHEMA IF NOT EXISTS {lake} WITH (location = '{location}')")
tables = {row[0] for row in query('SHOW TABLES FROM '+lake)}
if 'bronze_order_lines' not in tables:
 query(BRONZE_SEED.format(lake=lake, location=location))
# Preserve an existing lesson seed and validate it before reusing it.
summary=query('SELECT count(*),count(DISTINCT line_id),CAST(sum(line_amount) AS VARCHAR) FROM '+bronze)[0]
if summary not in ([9,9,'220.00'],[10,10,'270.00']):
 raise ValueError('Expected the preceding Iceberg lesson Bronze seed: 9/220.00 or 10/270.00; stop before writing')
for key in ('customer_id','product_id','order_id','line_id'):
 if query('SELECT '+key+' FROM '+bronze+' WHERE '+key+' IS NULL'):
  raise ValueError('Bronze contains null keys')
base=bronze+' WHERE line_id BETWEEN 1 AND 9'
projections={
 'customers': 'SELECT DISTINCT customer_id,CAST(customer_name AS VARCHAR(40)) customer_name,CAST(country AS VARCHAR(2)) country FROM '+base,
 'products': 'SELECT DISTINCT product_id,CAST(product_name AS VARCHAR(40)) product_name,CAST(category AS VARCHAR(20)) category FROM '+base,
 'orders': 'SELECT DISTINCT order_id,customer_id,order_date,CAST(order_status AS VARCHAR(12)) order_status FROM '+base,
 'order_items': 'SELECT line_id,order_id,product_id,quantity,CAST(unit_price AS DECIMAL(12,2)) unit_price FROM '+base,
}
print('PREPARE_MYSQL_SOURCE', flush=True)
existing={r[0] for r in query('SHOW TABLES FROM mysql.trino_ecomm')}
for name,select in projections.items():
 target=MYSQL_PREFIX+name
 if target.split('.')[-1] not in existing:
  query('CREATE TABLE '+target+' AS '+select)
  print('SOURCE_CREATED',target,flush=True)
 else:print('SOURCE_REUSED',target,flush=True)
# Validate original seed rows before appending the stable incremental keys.
for name,key,expected in [('customers','customer_id',4),('products','product_id',3),('orders','order_id',6),('order_items','line_id',9)]:
 target=MYSQL_PREFIX+name
 if query('SELECT '+key+' FROM '+target+' GROUP BY '+key+' HAVING count(*)>1 OR '+key+' IS NULL'):
  raise ValueError('Source key duplicates: '+target)
 select=projections[name]
 where=' WHERE order_id<=1006' if name=='orders' else (' WHERE line_id<=9' if name=='order_items' else '')
 diff='SELECT count(*) FROM ((('+select+') EXCEPT (SELECT * FROM '+target+where+')) UNION ALL ((SELECT * FROM '+target+where+') EXCEPT ('+select+'))) differences'
 if query(diff)!=[[0]]:raise ValueError('Existing source conflicts with Bronze seed: '+target)
 if query('SELECT count(*) FROM ('+select+') seed')!=[[expected]]:raise ValueError('Unexpected seed count: '+name)
day='2026-11-03'
orders=MYSQL_PREFIX+'orders';items=MYSQL_PREFIX+'order_items'
row=query('SELECT order_id,customer_id,CAST(order_date AS VARCHAR),order_status FROM '+orders+' WHERE order_id=1007')
item_row=query('SELECT line_id,order_id,product_id,quantity,CAST(unit_price AS VARCHAR) FROM '+items+' WHERE line_id=10')
if row and row!=[[1007,3,day,'COMPLETED']]:
 raise ValueError('Conflicting order 1007')
if item_row and item_row!=[[10,1007,101,2,'25.00']]:
 raise ValueError('Conflicting line 10')
if not row:
 query("INSERT INTO "+orders+" (order_id, customer_id, order_date, order_status) "
       "VALUES (1007,3,DATE '"+day+"','COMPLETED')")
 print('MYSQL_ORDER_1007_INSERTED', flush=True)
if not item_row:
 query('INSERT INTO '+items+" (line_id, order_id, product_id, quantity, unit_price) "
       "VALUES (10,1007,101,2,DECIMAL '25.00')")
 print('MYSQL_LINE_10_INSERTED', flush=True)
tasks.preflight(include_lesson=False)
print('PREPARE_ICEBERG_LAYERS', flush=True)
for table, columns in (
 ('silver_order_lines', '''line_id BIGINT, order_id BIGINT, customer_id BIGINT,
     product_id BIGINT, order_date DATE, customer_name VARCHAR, country VARCHAR,
     product_name VARCHAR, category VARCHAR, quantity INTEGER,
     unit_price DECIMAL(12,2), line_amount DECIMAL(18,2)'''),
 ('gold_daily_sales', '''order_date DATE, country VARCHAR, completed_orders BIGINT,
     revenue DECIMAL(18,2)'''),
):
 if table not in tables:
  partition = "partitioning = ARRAY['order_date'], " if table == 'silver_order_lines' else ''
  query(f"CREATE TABLE IF NOT EXISTS {lake}.{table} ({columns}) "
        f"WITH (format = 'PARQUET', format_version = 2, {partition}"
        f"location = '{location}/{table}')")
for statement in MERGES:
 query(statement.replace('iceberg_polaris.trino_ecomm_s01',lake).replace('mysql.trino_ecomm.trino_s01_',MYSQL_PREFIX))
 print('LESSON_MERGE_PASS',flush=True)
tasks.preflight()
report=tasks.verify_report(lake+'.silver_order_lines',lake+'.gold_daily_sales')
if report['groups']!=4:raise ValueError('Expected four daily/country groups; inspect the course seed')
print('ECOMMERCE_DATA_READY: 8 lines / 5 orders / 4 groups / 225.00',flush=True)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check readiness without writing")
    args = parser.parse_args()
    seed = Path(__file__).with_name("bronze-seed.sql").read_text(encoding="utf-8")
    os.environ["PATH"] = os.pathsep.join((str(Path.home() / ".crc/bin/oc"), os.environ["PATH"]))
    try:
        if not args.check:
            print("PREPARE_MYSQL_DATABASE", flush=True)
            # Use the existing in-pod credential for scoped database setup.
            subprocess.run(
                ["oc", "exec", "-i", "-n", "bigdata", "mysql-0", "--", "sh", "-ec",
                 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -u root'],
                input=ADMIN_SQL, text=True, check=True,
            )
        subprocess.run(
            ["oc", "exec", "-i", "-n", "bigdata", "airflow-0", "-c", "airflow", "--", "python", "-"],
            input=f"CHECK_ONLY = {args.check!r}\nBRONZE_SEED = {seed!r}\n" + REMOTE_CODE,
            text=True, check=True,
        )
    except subprocess.CalledProcessError as exc:
        parser.exit(exc.returncode, "Ecommerce preparation failed. See the stage and error above.\n")


if __name__ == "__main__":
    main()
