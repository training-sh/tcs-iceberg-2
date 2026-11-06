"""Create/reuse S3 buckets and upload the original local MovieLens files."""
import os
from pyspark.sql import SparkSession, functions as F

# Each script is self-contained. Credentials come from the existing Job Secret wiring.
def session(name):
    b = (SparkSession.builder.appName("movielens-classroom-" + name)
         .config("spark.cores.max", "1")
         .config("spark.executor.cores", "1")
         .config("spark.executor.memory", "512m")
         .config("spark.sql.shuffle.partitions", "2")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.redaction.regex", "(?i)secret|password|token|access.?key|credential"))
    endpoint = os.environ.get("S3_ENDPOINT", "http://seaweedfs:8333")
    uri = os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog").rstrip("/")
    conf = {
        "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        "spark.hadoop.fs.s3a.endpoint": endpoint,
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        "spark.hadoop.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        "spark.hadoop.fs.s3a.access.key": os.environ["AWS_ACCESS_KEY_ID"],
        "spark.hadoop.fs.s3a.secret.key": os.environ["AWS_SECRET_ACCESS_KEY"],
        "spark.sql.catalog.polaris": "org.apache.iceberg.spark.SparkCatalog",
        "spark.sql.catalog.polaris.type": "rest",
        "spark.sql.catalog.polaris.uri": uri,
        "spark.sql.catalog.polaris.warehouse": "training",
        "spark.sql.catalog.polaris.rest.auth.type": "oauth2",
        "spark.sql.catalog.polaris.oauth2-server-uri": uri + "/v1/oauth/tokens",
        "spark.sql.catalog.polaris.credential": os.environ["POLARIS_CLIENT_ID"] + ":" + os.environ["POLARIS_CLIENT_SECRET"],
        "spark.sql.catalog.polaris.scope": "PRINCIPAL_ROLE:ALL",
        "spark.sql.catalog.polaris.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
        "spark.sql.catalog.polaris.s3.endpoint": endpoint,
        "spark.sql.catalog.polaris.s3.path-style-access": "true",
        "spark.sql.catalog.polaris.s3.access-key-id": os.environ["AWS_ACCESS_KEY_ID"],
        "spark.sql.catalog.polaris.s3.secret-access-key": os.environ["AWS_SECRET_ACCESS_KEY"],
        "spark.sql.catalog.polaris.client.region": "us-east-1",
    }
    for key, value in conf.items():
        b = b.config(key, value)
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark

from pathlib import Path
import hashlib
import json

if __name__ == "__main__":
    spark = session("01-upload")
    client = None
    try:
        j = spark.sparkContext._jvm
        credentials = j.com.amazonaws.auth.BasicAWSCredentials(os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
        endpoint = j.com.amazonaws.client.builder.AwsClientBuilder.EndpointConfiguration(os.environ.get("S3_ENDPOINT", "http://seaweedfs:8333"), "us-east-1")
        client = (j.com.amazonaws.services.s3.AmazonS3ClientBuilder.standard()
                  .withEndpointConfiguration(endpoint).withPathStyleAccessEnabled(True)
                  .withCredentials(j.com.amazonaws.auth.AWSStaticCredentialsProvider(credentials)).build())
        for bucket in ("movielens-classroom-raw", "warehouse"):
            if not client.doesBucketExistV2(bucket):
                client.createBucket(bucket)
                print("BUCKET_CREATED", bucket)
            else:
                print("BUCKET_REUSED", bucket)
        source = Path("/workspace/movielens-classroom/source")
        manifest = {"dataset": "ml-latest-small", "files": {}}
        for name in ("movies.csv", "ratings.csv", "tags.csv", "links.csv", "README.txt"):
            file = source / name
            payload = file.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            key = "ml-latest-small/" + name
            if client.doesObjectExist("movielens-classroom-raw", key):
                obj = client.getObject("movielens-classroom-raw", key)
                stream = obj.getObjectContent()
                try:
                    old = bytes(j.org.apache.commons.io.IOUtils.toByteArray(stream))
                finally:
                    stream.close()
                if hashlib.sha256(old).hexdigest() != digest:
                    raise ValueError("Raw object differs; do not overwrite: " + key)
            else:
                client.putObject("movielens-classroom-raw", key, j.java.io.File(str(file)))
            manifest["files"][name] = {"bytes": len(payload), "sha256": digest}
            print("BRONZE_FILE_PASS", name, len(payload), digest)
        client.putObject("movielens-classroom-raw", "ml-latest-small/manifest.json", json.dumps(manifest, sort_keys=True, indent=2))
        print("UPLOAD_PASS", "s3://movielens-classroom-raw/ml-latest-small/")
    finally:
        if client is not None:
            client.shutdown()
        spark.stop()
