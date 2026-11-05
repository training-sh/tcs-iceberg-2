# 02 — Invoice consumer and manual offsets
Use the producer's existing topic. This bounded observer reads and prints metadata; it is not the lakehouse ingestion service. It starts no Spark application. Its consumer group is separate from Spark's checkpoint tracking.

```python
# Fixed names: keep this cell consistent across all four notebooks.
BOOTSTRAP = "kafka:9092"
TOPIC = "invoices-lake"
CONSUMER_GROUP = "invoice-observer"
DATALAKE = "polaris.invoice_lake"
LOCATION_ROOT = "s3://warehouse/iceberg/invoice_lake"
INGEST_CHECKPOINT = "s3a://warehouse/invoice-lake/checkpoints/kafka_to_lake"
GOLD_CHECKPOINT = "s3a://warehouse/invoice-lake/checkpoints/silver_to_country"
BRONZE = DATALAKE + ".bronze"
SILVER = DATALAKE + ".silver"
REJECTS = DATALAKE + ".rejects"
GOLD = DATALAKE + ".country_totals"
```

```python
import sys
CLIENT_DIR = "/workspace/.course-python/kafka-python-2.2.15"
if CLIENT_DIR not in sys.path:
    sys.path.insert(0, CLIENT_DIR)
print({"topic": TOPIC, "datalake": DATALAKE})
```

## Define the bounded consumer
This notebook includes its own consumer code. Run notebook 01 first to install the Python client and publish data.

```python
import json

import time

def observe(limit=10, seconds=20, commit=False, consumer_factory=None,
            topic=TOPIC, bootstrap_servers=BOOTSTRAP, group_id=CONSUMER_GROUP):
    from kafka import KafkaConsumer, TopicPartition
    from kafka.structs import OffsetAndMetadata
    factory = consumer_factory or KafkaConsumer
    consumer = factory(topic, bootstrap_servers=bootstrap_servers, group_id=group_id,
                       auto_offset_reset="earliest", enable_auto_commit=False,
                       request_timeout_ms=15000, session_timeout_ms=10000)
    deadline = time.monotonic() + seconds
    count = 0
    try:
        while count < limit and time.monotonic() < deadline:
            polled = consumer.poll(timeout_ms=1000, max_records=min(10, limit - count))
            for messages in polled.values():
                for message in messages:
                    try:
                        invoice = json.loads(message.value.decode("utf-8"))
                        summary = {k: invoice.get(k) for k in ["LineID", "InvoiceNo", "Country"]}
                    except (ValueError, UnicodeDecodeError, AttributeError, TypeError):
                        summary = {"parse": "invalid JSON/tombstone"}
                    tp = TopicPartition(message.topic, message.partition)
                    before = consumer.committed(tp)
                    print("OBSERVED", {"partition": message.partition, "offset": message.offset,
                                       "record": summary, "committed_before": before})
                    if commit:
                        # Commit only this inspected record, not unprocessed fetched records.
                        consumer.commit({tp: OffsetAndMetadata(message.offset + 1, "", -1)})
                        print("COMMITTED_NEXT_OFFSET", consumer.committed(tp))
                    count += 1
                    if count >= limit:
                        return count
        return count
    finally:
        consumer.close(autocommit=False)
```

```python
print("observer group:", CONSUMER_GROUP)
```

## Read without committing
Run after batch A. Stop after ten records or twenty seconds. With no previous committed offsets, the earliest available records are read. Repeating without commits can show them again. A smaller result is possible if the topic is empty, a group was previously advanced or assignment took too long.

```python
observed = observe(limit=10, seconds=20, commit=False, topic=TOPIC, bootstrap_servers=BOOTSTRAP, group_id=CONSUMER_GROUP)
print("OBSERVED_COUNT", observed)
```

## Read and commit inspected records
This commits exactly offset + 1 for each inspected message's partition, not all fetched positions. A committed offset is the next position to read. Printing and committing is an offset demonstration, not durable business processing. Invalid JSON is displayed as such and can still be acknowledged by this observer.

```python
COMMIT_OBSERVED = False
if COMMIT_OBSERVED:
    print("OBSERVED_COUNT", observe(limit=10, seconds=20, commit=True, topic=TOPIC, bootstrap_servers=BOOTSTRAP, group_id=CONSUMER_GROUP))
else:
    print("Manual commit demonstration not requested")
```

Run the read cell again after committing to see remaining/new data. `earliest` applies only when the group has no valid committed position. It does not override existing commits. Consuming does not delete Kafka records. Spark still reads the original topic independently through its own checkpoint, even after this group commits.

Every call closes its consumer in finally. Do not reset offsets or delete the topic for this exercise. Use new explicit topic/lake/checkpoint names for a separate dataset.
