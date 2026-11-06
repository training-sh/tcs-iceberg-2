"""Read Bronze CSVs, validate/clean them, and replace only course Silver tables."""
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

from pyspark.sql.window import Window

if __name__ == "__main__":
    spark = session("02-silver")
    try:
        raw = "s3a://movielens-classroom-raw/ml-latest-small/"
        movies = spark.read.options(header=True, mode="FAILFAST").schema("movieId INT,title STRING,genres STRING").csv(raw + "movies.csv")
        ratings = spark.read.options(header=True, mode="FAILFAST").schema("userId INT,movieId INT,rating DOUBLE,timestamp LONG").csv(raw + "ratings.csv")
        counts = (movies.count(), ratings.count())
        if counts != (9742, 100836):
            raise ValueError("This lesson expects MovieLens small: 9742 movies and 100836 ratings; got " + str(counts))
        good_movies = movies.filter("movieId > 0 AND title IS NOT NULL AND length(trim(title)) > 0 AND genres IS NOT NULL")
        good_ratings = ratings.filter("userId > 0 AND movieId > 0 AND timestamp >= 0 AND rating >= 0.5 AND rating <= 5.0").filter(~F.isnan("rating"))
        if good_movies.count() != counts[0] or good_ratings.count() != counts[1]:
            raise ValueError("Invalid source records; inspect before continuing")
        movies = (good_movies.withColumn("rn", F.row_number().over(Window.partitionBy("movieId").orderBy("title", "genres")))
                  .filter("rn=1").drop("rn").withColumn("title", F.trim("title"))
                  .withColumn("release_year", F.regexp_extract("title", r"\((\d{4})\)$", 1).cast("int")))
        ratings = (good_ratings.withColumn("rn", F.row_number().over(Window.partitionBy("userId", "movieId", "timestamp").orderBy(F.desc("rating"))))
                   .filter("rn=1").drop("rn")
                   .withColumn("rated_at", F.to_timestamp(F.from_unixtime("timestamp")))
                   .withColumn("rating_date", F.to_date("rated_at")))
        if ratings.join(movies, "movieId", "left_anti").take(1):
            raise ValueError("Ratings reference unknown movies")
        namespace = "polaris.movielens_classroom_s01_silver"
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace} LOCATION 's3://warehouse/iceberg/movielens_classroom_s01_silver'")
        for name, frame in (("movies", movies), ("ratings", ratings)):
            table = namespace + "." + name
            frame.writeTo(table).using("iceberg").tableProperty("format-version", "2").createOrReplace()
            count = spark.table(table).count()
            if count != frame.count():
                raise ValueError("Silver count mismatch")
            print("SILVER_TABLE_PASS", table, count)
        print("SILVER_PASS")
    finally:
        spark.stop()
