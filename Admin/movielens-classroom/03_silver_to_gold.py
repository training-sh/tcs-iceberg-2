"""Build movie, genre and daily analytics from persisted Silver Iceberg tables."""
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


if __name__ == "__main__":
    spark = session("03-gold")
    try:
        silver = "polaris.movielens_classroom_s01_silver"
        gold = "polaris.movielens_classroom_s01_gold"
        spark.table(silver + ".movies").createOrReplaceTempView("movies")
        spark.table(silver + ".ratings").createOrReplaceTempView("ratings")
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {gold} LOCATION 's3://warehouse/iceberg/movielens_classroom_s01_gold'")
        queries = {
            "movie_stats": """SELECT m.movieId,m.title,m.release_year,m.genres,
                count(r.userId) rating_count,round(avg(r.rating),6) avg_rating,
                count(DISTINCT r.userId) distinct_users
                FROM movies m LEFT JOIN ratings r ON m.movieId=r.movieId
                GROUP BY m.movieId,m.title,m.release_year,m.genres""",
            "genre_stats": """WITH expanded AS (
                SELECT movieId,explode(split(genres,'[|]')) genre FROM movies)
                SELECT e.genre,count(*) rating_count,count(DISTINCT r.movieId) rated_movies,
                round(avg(r.rating),6) avg_rating
                FROM expanded e JOIN ratings r ON e.movieId=r.movieId GROUP BY e.genre""",
            "daily_ratings": """SELECT rating_date,count(*) rating_count,
                count(DISTINCT userId) active_users,round(avg(rating),6) avg_rating
                FROM ratings GROUP BY rating_date""",
        }
        for name, query in queries.items():
            spark.sql(query).writeTo(gold + "." + name).using("iceberg").tableProperty("format-version", "2").createOrReplace()
            print("GOLD_TABLE_PASS", gold + "." + name, spark.table(gold + "." + name).count())
        expected = spark.table(silver + ".ratings").count()
        for name in ("movie_stats", "daily_ratings"):
            total = spark.table(gold + "." + name).agg(F.sum("rating_count")).first()[0]
            if total != expected:
                raise ValueError("Gold rating reconciliation failed: " + name)
        if spark.table(gold + ".movie_stats").count() != spark.table(silver + ".movies").count():
            raise ValueError("Gold must retain unrated movies")
        print("GOLD_PASS", "ratings=" + str(expected))
        spark.sql(f"SELECT title,rating_count,avg_rating FROM {gold}.movie_stats WHERE rating_count>=100 ORDER BY avg_rating DESC,rating_count DESC,title LIMIT 10").show(truncate=False)
    finally:
        spark.stop()
