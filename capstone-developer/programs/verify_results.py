"""Check both catalogs against the supplied Olist bytes and publish the final run status."""
import csv
import json
import os
import re
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import requests

def expected_results():
    def read(name):
        with (Path('/input')/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    sellers=read('olist_sellers_dataset.csv')
    orders={r['order_id']:r for r in read('olist_orders_dataset.csv')}
    grouped=defaultdict(list)
    for item in read('olist_order_items_dataset.csv'):grouped[item['seller_id']].append(item)
    activity=[]
    for seller in sellers:
        sid=seller['seller_id'];items=grouped[sid]
        statuses=Counter(orders[oid]['order_status'] for oid in {r['order_id'] for r in items})
        shipping=Counter()
        for item in items:
            stamp=orders[item['order_id']]['order_delivered_carrier_date']
            shipping['missing_handoff_items' if not stamp else 'on_time_items' if stamp<=item['shipping_limit_date'] else 'late_items']+=1
        activity.append(dict(seller_id=sid,seller_state=seller['seller_state'],distinct_orders=sum(statuses.values()),item_rows=len(items),
            merchandise_value=format(sum((Decimal(r['price']) for r in items),Decimal('0')),'.2f'),
            delivered_orders=statuses['delivered'],canceled_orders=statuses['canceled'],other_orders=sum(v for k,v in statuses.items() if k not in ('delivered','canceled')),
            **{k:shipping[k] for k in ('on_time_items','late_items','missing_handoff_items')}))
    geography=[]
    for state in sorted({r['seller_state'] for r in activity}):
        rows=[r for r in activity if r['seller_state']==state]
        geography.append(dict(seller_state=state,seller_count=len(rows),item_rows=sum(r['item_rows'] for r in rows)))
    return {'seller_activity':activity,'seller_geography':geography}

def query(sql):
    r=requests.post(os.environ.get('TRINO_URL','http://trino:8080')+'/v1/statement',data=sql.encode(),headers={'X-Trino-User':'team'},timeout=30)
    rows=[];deadline=time.monotonic()+300
    while True:
        r.raise_for_status();page=r.json()
        if 'error' in page:raise RuntimeError(page['error']['message'])
        rows.extend(page.get('data',[]))
        if 'nextUri' not in page:return rows
        if time.monotonic()>deadline:
            requests.delete(page['nextUri'],timeout=10);raise TimeoutError('Trino query timed out')
        r=requests.get(page['nextUri'],timeout=30)

def main():
    run=os.environ['RUN_ID']
    if not re.fullmatch(r'ops_[a-z0-9_]{1,45}',run):raise ValueError('Set RUN_ID to the successful compute run ID')
    started=time.monotonic();result={'run_id':run,'outputs':{}}
    for name,expected in expected_results().items():
        key='seller_id' if name=='seller_activity' else 'seller_state'
        columns=sorted(expected[0]);sqlcols=','.join(columns)
        wanted=[[r[c] for c in columns] for r in sorted(expected,key=lambda r:r[key])]
        hive=query(f'SELECT {sqlcols} FROM hive.{run}.{name} ORDER BY {key}')
        iceberg=query(f'SELECT {sqlcols} FROM iceberg_polaris.{run}.{name} ORDER BY {key}')
        assert hive==iceberg==wanted,'Catalog/oracle mismatch: '+name
        result['outputs'][name]=len(wanted);print('TRINO_VERIFIED '+name+'='+str(len(wanted)),flush=True)
    seconds,items=query(f'SELECT compute_seconds,input_items FROM iceberg_polaris.{run}.processing_metrics')[0]
    result.update(status='PASS',seconds=round(float(seconds)+time.monotonic()-started,2),input_items=int(items))
    query(f"CREATE TABLE iceberg_polaris.{run}.verification AS SELECT 'PASS' AS status, {int(items)} AS input_items, {result['seconds']} AS processing_seconds")
    requests.post('http://ops-metrics:8000/report',json=result,timeout=15).raise_for_status()
    print('SELLER_OPS_PASS '+json.dumps(result),flush=True)

if __name__=='__main__':main()
