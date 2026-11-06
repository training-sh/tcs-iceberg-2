"""Stage Gold through JDBC, validate it, then atomically publish all three MySQL tables."""
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

import uuid

if __name__ == "__main__":
    spark = session("04-mysql")
    connection = None
    try:
        j = spark.sparkContext._jvm
        j.java.lang.Class.forName("com.mysql.cj.jdbc.Driver")
        user, password = os.environ["DB_USER"], os.environ["DB_PASSWORD"]
        base = "jdbc:mysql://mysql:3306/"
        options = "?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC"
        connection = j.java.sql.DriverManager.getConnection(base + options, user, password)
        statement = connection.createStatement()
        database = "movielens_classroom_s01"
        statement.executeUpdate("CREATE DATABASE IF NOT EXISTS " + database)
        url = base + database + options
        props = {"user": user, "password": password, "driver": "com.mysql.cj.jdbc.Driver"}
        suffix = uuid.uuid4().hex[:12]
        names = ("movie_stats", "genre_stats", "daily_ratings")
        renames, backups, staged = [], [], []
        for name in names:
            frame = spark.table("polaris.movielens_classroom_s01_gold." + name).coalesce(1)
            target, staging = database + "." + name, database + "." + name + "__stage_" + suffix
            frame.write.mode("errorifexists").jdbc(url, staging, properties=props)
            staged.append(staging)
            readback = spark.read.jdbc(url, staging, properties=props)
            if frame.count() != readback.count():
                raise ValueError("MySQL staging count mismatch: " + name)
            # Compare all values before publication, tolerating only insignificant JDBC double rounding.
            if name == "daily_ratings": key = "rating_date"
            elif name == "genre_stats": key = "genre"
            else: key = "movieId"
            a, b = frame.alias("a"), readback.alias("b")
            joined = a.join(b, F.col("a." + key) == F.col("b." + key), "full")
            mismatch = F.lit(False)
            for col in frame.columns:
                left, right = F.col("a." + col), F.col("b." + col)
                equal = left.eqNullSafe(right)
                if col == "avg_rating":
                    equal = equal | (F.abs(left-right) <= F.lit(0.00000001))
                mismatch = mismatch | ~F.coalesce(equal, F.lit(False))
            if joined.filter(mismatch).take(1):
                raise ValueError("MySQL staging values differ: " + name)
            statement.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='" + database + "' AND table_name='" + name + "'")
            result = statement.getResultSet()
            exists = result.next()
            result.close()
            if exists:
                backup = target + "__old_" + suffix
                renames.append(target + " TO " + backup)
                backups.append(backup)
            renames.append(staging + " TO " + target)
            print("MYSQL_STAGING_PASS", name, frame.count())
        # One RENAME statement publishes the three verified snapshots together.
        statement.executeUpdate("RENAME TABLE " + ", ".join(renames))
        for backup in backups:
            statement.executeUpdate("DROP TABLE " + backup)
        for name in names:
            count = spark.read.jdbc(url, database + "." + name, properties=props).count()
            print("MYSQL_TABLE_PASS", database + "." + name, count)
        statement.close()
        print("MYSQL_PASS")
    finally:
        if connection is not None:
            connection.close()
        spark.stop()
