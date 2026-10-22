#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

case "${1:-}" in
  ""|--with-s3) ;;
  *) echo "Usage: bash download-jars.sh [--with-s3]" >&2; exit 2 ;;
esac
mkdir -p jars
base=https://repo.maven.apache.org/maven2

fetch() {
  local path="$1"
  local file="jars/${path##*/}"
  echo "Downloading ${file##*/}"
  curl --fail --location --retry 3 --connect-timeout 20 \
    --output "$file.part" "$base/$path"
  mv "$file.part" "$file"
}

# Spark connectors match Spark 3.5.9 and Scala 2.12.
fetch io/delta/delta-spark_2.12/3.3.2/delta-spark_2.12-3.3.2.jar
fetch io/delta/delta-storage/3.3.2/delta-storage-3.3.2.jar
fetch org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0/iceberg-spark-runtime-3.5_2.12-1.10.0.jar
fetch org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.9/spark-sql-kafka-0-10_2.12-3.5.9.jar
fetch org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.9/spark-token-provider-kafka-0-10_2.12-3.5.9.jar
fetch org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
fetch org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar
fetch org/apache/spark/spark-avro_2.12/3.5.9/spark-avro_2.12-3.5.9.jar
fetch com/mysql/mysql-connector-j/8.4.0/mysql-connector-j-8.4.0.jar
fetch org/postgresql/postgresql/42.7.8/postgresql-42.7.8.jar

# Optional large bundles: Iceberg S3FileIO and Hadoop S3A.
if [[ "${1:-}" == "--with-s3" ]]; then
  fetch org/apache/iceberg/iceberg-aws-bundle/1.10.0/iceberg-aws-bundle-1.10.0.jar
  fetch org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
  fetch com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
fi

echo "JARs ready in $(pwd)/jars. Rebuild the image after changing JARs."
