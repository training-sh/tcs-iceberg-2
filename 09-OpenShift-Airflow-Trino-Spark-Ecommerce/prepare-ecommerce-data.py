"""Prepare the missing ecommerce source from the preceding Iceberg seed, then reconcile it."""
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
import sys,json,datetime
sys.path.insert(0,'/opt/airflow/dags')
from course_airflow_ecomm.trino_http import query
from course_airflow_ecomm import tasks,sql
from course_airflow_ecomm.settings import MYSQL_PREFIX,TRINO_LESSON_SCHEMA,RUN_SUFFIX
lake=TRINO_LESSON_SCHEMA
bronze=lake+'.bronze_order_lines'
# The initial Iceberg lesson supplies the seed. Never drop or overwrite it.
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
day=query('SELECT CAST(max(order_date) AS VARCHAR) FROM '+bronze)[0][0]
datetime.date.fromisoformat(day)
orders=MYSQL_PREFIX+'orders';items=MYSQL_PREFIX+'order_items'
row=query('SELECT order_id,customer_id,CAST(order_date AS VARCHAR),order_status FROM '+orders+' WHERE order_id=1007')
if not row:
 query("INSERT INTO "+orders+" VALUES (1007,3,DATE '"+day+"','COMPLETED')")
elif row!=[[1007,3,day,'COMPLETED']]:raise ValueError('Conflicting order 1007')
row=query('SELECT line_id,order_id,product_id,quantity,CAST(unit_price AS VARCHAR) FROM '+items+' WHERE line_id=10')
if not row:query('INSERT INTO '+items+" VALUES (10,1007,101,2,DECIMAL '25.00')")
elif row!=[[10,1007,101,2,'25.00']]:raise ValueError('Conflicting line 10')
tasks.preflight(include_lesson=False)
for statement in MERGES:
 query(statement.replace('iceberg_polaris.trino_ecomm_s01',lake).replace('mysql.trino_ecomm.trino_s01_',MYSQL_PREFIX))
 print('LESSON_MERGE_PASS',flush=True)
tasks.preflight()
report=tasks.verify_report(lake+'.silver_order_lines',lake+'.gold_daily_sales')
if report['groups']!=4:raise ValueError('Expected four daily/country groups; inspect the course seed')
print('ECOMMERCE_DATA_READY: 8 lines / 5 orders / 4 groups / 225.00',flush=True)
"""


def main():
    # Use existing administrative wiring; no credential is printed or added to source.
    subprocess.run(["oc","exec","-i","-n","bigdata","mysql-0","--","sh","-ec",
                    'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -u root'],
                   input=ADMIN_SQL,text=True,check=True)
    subprocess.run(["oc","exec","-i","-n","bigdata","airflow-0","-c","airflow","--","python","-"],
                   input=REMOTE_CODE,text=True,check=True)


if __name__ == "__main__":
    main()
