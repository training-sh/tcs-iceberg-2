"""Supplied storage preparation program; no pip install or student development."""
from pathlib import Path
from pyspark.sql import SparkSession
spark=SparkSession.builder.master('local[1]').appName('olist-input-upload').config('spark.eventLog.enabled','false').getOrCreate()
try:
    j=spark._jvm
    fs=j.org.apache.hadoop.fs.FileSystem.get(j.java.net.URI('s3a://warehouse'),spark._jsc.hadoopConfiguration())
    fs.mkdirs(j.org.apache.hadoop.fs.Path('s3a://warehouse/spark-events'))
    for p in sorted(Path('/input').glob('*.csv')):
        # Projected ConfigMap files are symlinks; stream their bytes rather than
        # invoking S3A's local-file relative-path copier on those symlinks.
        output=fs.create(j.org.apache.hadoop.fs.Path('s3a://warehouse/olist/input/'+p.name),True)
        try: output.write(bytearray(p.read_bytes()))
        finally: output.close()
        print('INPUT_UPLOADED '+p.name,flush=True)
finally: spark.stop()
