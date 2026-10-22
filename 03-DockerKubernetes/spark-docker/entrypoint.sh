#!/usr/bin/env bash
set -euo pipefail

# Run Spark in the foreground so the container follows its lifetime.
case "${1:-master}" in
  master)
    exec "$SPARK_HOME/bin/spark-class" org.apache.spark.deploy.master.Master \
      --host "${SPARK_MASTER_HOST:-spark-master}" \
      --port 7077 --webui-port 8080
    ;;
  worker)
    exec "$SPARK_HOME/bin/spark-class" org.apache.spark.deploy.worker.Worker \
      --host "${SPARK_WORKER_HOST:-$(hostname)}" \
      --port 7078 --webui-port 8081 \
      --cores "${SPARK_WORKER_CORES:-2}" \
      --memory "${SPARK_WORKER_MEMORY:-2g}" \
      "${SPARK_MASTER_URL:-spark://spark-master:7077}"
    ;;
  *)
    # Also supports: docker run --rm IMAGE java -version
    exec "$@"
    ;;
esac
