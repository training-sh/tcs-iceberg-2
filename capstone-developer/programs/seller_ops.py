"""Read Olist inputs, calculate seller operations, publish both catalogs and verify them."""
import csv
import json
import os
import re
import socket
import time
import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from pyspark.sql import SparkSession, functions as F


FILES = {'sellers':'olist_sellers_dataset.csv','items':'olist_order_items_dataset.csv','orders':'olist_orders_dataset.csv'}

REQUIRED = {'sellers':{'seller_id','seller_state'}, 'items':{'order_id','order_item_id','seller_id','price','shipping_limit_date'}, 'orders':{'order_id','order_status','order_delivered_carrier_date'}}

def load(root):
    data = {}
    for key,name in FILES.items():
        with (Path(root)/name).open(encoding='utf-8-sig',newline='') as f:
            reader = csv.DictReader(f)
            if not REQUIRED[key] <= set(reader.fieldnames or []): raise ValueError('Missing columns: '+name)
            data[key] = list(reader)
    return data

def calculate(data):
    sellers = {r['seller_id']:r for r in data['sellers']}
    orders = {r['order_id']:r for r in data['orders']}
    assert len(sellers)==len(data['sellers']) and len(orders)==len(data['orders']), 'Duplicate primary key'
    assert len({(r['order_id'],r['order_item_id']) for r in data['items']})==len(data['items'])
    groups = defaultdict(list)
    for r in data['items']:
        assert r['seller_id'] in sellers and r['order_id'] in orders, 'Orphan item'
        assert r['shipping_limit_date'], 'Missing shipping deadline'
        groups[r['seller_id']].append(r)
    activity = []
    for sid,seller in sorted(sellers.items()):
        items = groups[sid]
        statuses = Counter(orders[oid]['order_status'] for oid in {x['order_id'] for x in items})
        shipping = Counter()
        for item in items:
            stamp = orders[item['order_id']]['order_delivered_carrier_date']
            shipping['missing_handoff_items' if not stamp else 'on_time_items' if stamp <= item['shipping_limit_date'] else 'late_items'] += 1
        activity.append(dict(seller_id=sid,seller_state=seller['seller_state'],distinct_orders=sum(statuses.values()),item_rows=len(items),
            merchandise_value=format(sum((Decimal(x['price']) for x in items),Decimal('0')),'.2f'),
            delivered_orders=statuses['delivered'],canceled_orders=statuses['canceled'],
            other_orders=sum(v for k,v in statuses.items() if k not in ('delivered','canceled')),
            **{k:shipping[k] for k in ('on_time_items','late_items','missing_handoff_items')}))
    geography = []
    for state in sorted({r['seller_state'] for r in activity}):
        rows = [r for r in activity if r['seller_state']==state]
        geography.append(dict(seller_state=state,seller_count=len(rows),item_rows=sum(r['item_rows'] for r in rows)))
    return {'seller_activity':activity,'seller_geography':geography}

def transform(sellers,items,orders):
    joined=items.join(orders,'order_id').withColumn('money',F.col('price').cast('decimal(18,2)'))
    stamp=F.to_timestamp('order_delivered_carrier_date'); deadline=F.to_timestamp('shipping_limit_date')
    joined=joined.withColumn('handoff',F.when(stamp.isNull(),'missing').when(stamp<=deadline,'on_time').otherwise('late'))
    agg=joined.groupBy('seller_id').agg(F.countDistinct('order_id').alias('distinct_orders'),F.count('*').alias('item_rows'),F.sum('money').alias('merchandise_value'),
        *[F.countDistinct(F.when(F.col('order_status')==status,F.col('order_id'))).alias(status+'_orders') for status in ('delivered','canceled')],
        F.countDistinct(F.when(~F.col('order_status').isin('delivered','canceled'),F.col('order_id'))).alias('other_orders'),
        *[F.sum(F.when(F.col('handoff')==status,1).otherwise(0)).alias(col) for status,col in [('on_time','on_time_items'),('late','late_items'),('missing','missing_handoff_items')]])
    activity=sellers.select('seller_id','seller_state').join(agg,'seller_id','left').fillna(0)
    geography=activity.groupBy('seller_state').agg(F.count('*').alias('seller_count'),F.sum('item_rows').alias('item_rows'))
    return {'seller_activity':activity,'seller_geography':geography}

def execute():
    started=time.monotonic(); run=os.environ.get('RUN_ID','ops_'+uuid.uuid4().hex[:12])
    if not re.fullmatch(r'ops_[a-z0-9_]{1,45}',run): raise ValueError('Use a fresh lowercase ops_ run ID')
    b=(SparkSession.builder.appName('olist-'+run).master('spark://spark-master:7077')
       .config('spark.driver.host',os.environ.get('POD_IP',socket.gethostbyname(socket.gethostname())))
       .config('spark.driver.bindAddress','0.0.0.0').config('spark.cores.max','1')
       .config('spark.executor.cores','1').config('spark.executor.memory','512m')
       .config('spark.sql.shuffle.partitions','2').config('spark.sql.session.timeZone','UTC')
       .config('spark.hadoop.fs.s3a.threads.max','4').config('spark.hadoop.fs.s3a.connection.maximum','16')
       .config('spark.redaction.regex','(?i)secret|password|token|credential|access.?key')
       .config('spark.hadoop.hive.metastore.uris','thrift://hive-metastore:9083')
       .config('spark.sql.warehouse.dir','hdfs://namenode:9000/user/hive/warehouse')
       .config('spark.sql.catalog.polaris','org.apache.iceberg.spark.SparkCatalog')
       .config('spark.sql.catalog.polaris.type','rest')
       .config('spark.sql.catalog.polaris.uri','http://polaris:8181/api/catalog')
       .config('spark.sql.catalog.polaris.warehouse','training')
       .config('spark.sql.catalog.polaris.credential',os.environ['POLARIS_CLIENT_ID']+':'+os.environ['POLARIS_CLIENT_SECRET'])
       .config('spark.sql.catalog.polaris.scope','PRINCIPAL_ROLE:ALL')
       .config('spark.sql.catalog.polaris.oauth2-server-uri','http://polaris:8181/api/catalog/v1/oauth/tokens')
       .config('spark.sql.catalog.polaris.io-impl','org.apache.iceberg.aws.s3.S3FileIO')
       .config('spark.sql.catalog.polaris.s3.endpoint',os.environ['S3_ENDPOINT'])
       .config('spark.sql.catalog.polaris.s3.path-style-access','true')
       .config('spark.sql.catalog.polaris.s3.access-key-id',os.environ['AWS_ACCESS_KEY_ID'])
       .config('spark.sql.catalog.polaris.s3.secret-access-key',os.environ['AWS_SECRET_ACCESS_KEY'])
       .config('spark.sql.catalog.polaris.client.region','us-east-1'))
    spark=b.enableHiveSupport().getOrCreate(); spark.sparkContext.setLogLevel('WARN')
    try:
        jvm=spark._jvm
        fs=jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI('s3a://warehouse'),spark._jsc.hadoopConfiguration())
        Path('/tmp/input').mkdir(exist_ok=True)
        for name in ('olist_sellers_dataset.csv','olist_order_items_dataset.csv','olist_orders_dataset.csv'):
            fs.copyToLocalFile(False,jvm.org.apache.hadoop.fs.Path('s3a://warehouse/olist/input/'+name),jvm.org.apache.hadoop.fs.Path('/tmp/input/'+name),True)
        expected=calculate(load('/tmp/input'))
        frames={}
        for key,filename in [('sellers','olist_sellers_dataset.csv'),('items','olist_order_items_dataset.csv'),('orders','olist_orders_dataset.csv')]:
            frame=spark.read.option('header',True).option('mode','FAILFAST').csv('s3a://warehouse/olist/input/'+filename)
            if not REQUIRED[key]<=set(frame.columns): raise ValueError('Missing columns: '+key)
            frames[key]=frame; print('INPUT_COUNT '+key+'='+str(frame.count()),flush=True)
        sellers,items,orders=(frames[k] for k in ('sellers','items','orders'))
        outputs=transform(sellers,items,orders)
        spark.sql(f"CREATE DATABASE {run} LOCATION 'hdfs://namenode:9000/olist/{run}'")
        spark.sql(f'CREATE NAMESPACE polaris.{run}')
        result={'run_id':run,'outputs':{}}
        for name,frame in outputs.items():
            actual=[]
            for row in frame.collect():
                d=row.asDict()
                if 'merchandise_value' in d: d['merchandise_value']=format(d['merchandise_value'],'.2f')
                actual.append(d)
            key='seller_id' if name=='seller_activity' else 'seller_state'
            assert sorted(actual,key=lambda r:r[key])==expected[name], 'Spark/reference mismatch: '+name
            frame.coalesce(1).write.mode('error').format('parquet').saveAsTable(f'{run}.{name}')
            frame.coalesce(1).writeTo(f'polaris.{run}.{name}').using('iceberg').create()
            result['outputs'][name]=len(actual); print('OUTPUT_VERIFIED '+name+'='+str(len(actual)),flush=True)
        result.update(status='COMPUTED',seconds=round(time.monotonic()-started,2),input_items=items.count())
        spark.createDataFrame([(result['seconds'],result['input_items'])],'compute_seconds double, input_items long').writeTo(f'polaris.{run}.processing_metrics').using('iceberg').create()
        body=json.dumps(result)
        stream=fs.create(jvm.org.apache.hadoop.fs.Path('s3a://warehouse/olist/reports/'+run+'.json'),False)
        try: stream.write(bytearray(body.encode()))
        finally: stream.close()
        print('SELLER_COMPUTE_PASS '+body,flush=True)
    finally: spark.stop()

if __name__=='__main__': execute()
