# 01 — Invoice producer
Run in the existing Jupyter Python kernel. The install and topic-creation steps are included here, so no separate installation notebook is required. This notebook starts no Spark application. Messages are keyed by Country; order is partition-local, not global. A stable LineID identifies an immutable invoice line. Application-level re-sends create new Kafka offsets even when the line identity is unchanged.

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

## Install the Python Kafka client here
Run this cell when the pinned client is not already available. `%pip` targets the current kernel. The explicit directory is on the existing notebook volume and avoids an unwritable default home in container exec sessions. No image rebuild or pod restart is required. It installs only Python files; Spark still uses the existing image JARs. Network/package-index access is required, or use the README's offline-wheel option.

```ipython
%pip install --no-deps --target /workspace/.course-python/kafka-python-2.2.15 "kafka-python==2.2.15"
```

## Define the invoice data and producer functions
All code used below is included in this notebook. Run these definition cells before inspecting or sending records.

```python
from copy import deepcopy

from decimal import Decimal

import json

def line(line_id, invoice, stock, quantity, price, customer, country, day):
    return {"LineID": line_id, "InvoiceNo": invoice, "StockCode": stock,
            "Description": {"101": "Keyboard", "102": "Mouse", "103": "Cable"}[stock],
            "Quantity": quantity, "InvoiceDate": f"2026-11-{day:02d} 10:00:00",
            "UnitPrice": price, "CustomerID": customer, "Country": country}

BASE_LINES = [
    line("L001", "1001", "101", 2, "25.00", "1", "IN", 1),
    line("L002", "1001", "102", 1, "15.00", "1", "IN", 1),
    line("L003", "1002", "101", 1, "25.00", "2", "IN", 1),
    line("L004", "1002", "103", 2, "10.00", "2", "IN", 1),
    line("L005", "1003", "102", 2, "15.00", "3", "UK", 2),
    line("L006", "1005", "101", 1, "25.00", "4", "US", 2),
    line("L007", "1005", "103", 1, "10.00", "4", "US", 2),
]

def batch_a():
    # 7 valid identities + a duplicate identity + invalid quantity + malformed JSON.
    return deepcopy(BASE_LINES + [BASE_LINES[0],
        line("BAD001", "1999", "103", 0, "10.00", "1", "IN", 2),
        "{not-valid-json"])

def batch_b():
    return [line("L008", "1007", "101", 2, "25.00", "3", "UK", 3), deepcopy(BASE_LINES[1])]

def encode_record(record):
    if isinstance(record, str):
        return b"invalid", record.encode("utf-8")
    return record["Country"].encode("utf-8"), json.dumps(record, sort_keys=True).encode("utf-8")

def expected_totals(include_b=False):
    records = BASE_LINES + ([batch_b()[0]] if include_b else [])
    result = {}
    for record in records:
        country = record["Country"]
        bucket = result.setdefault(country, {"invoices": set(), "amount": Decimal("0")})
        bucket["invoices"].add(record["InvoiceNo"])
        bucket["amount"] += record["Quantity"] * Decimal(record["UnitPrice"])
    return [(country, len(value["invoices"]), value["amount"]) for country, value in sorted(result.items())]
```

```python
import json

import time

def create_topic(topic=TOPIC, bootstrap_servers=BOOTSTRAP):
    from kafka.admin import KafkaAdminClient, NewTopic
    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers, request_timeout_ms=15000)
    try:
        if topic in admin.list_topics():
            raise ValueError("Topic exists: inspect it or choose another explicit TOPIC; it was not reset")
        admin.create_topics([NewTopic(topic, num_partitions=2, replication_factor=1)], timeout_ms=15000)
        print("TOPIC_CREATED", topic)
    finally:
        admin.close()

def inspect_topics(topic=TOPIC, bootstrap_servers=BOOTSTRAP):
    from kafka.admin import KafkaAdminClient
    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers, request_timeout_ms=15000)
    try:
        print("TOPIC_PRESENT", topic in admin.list_topics())
    finally:
        admin.close()

def send_records(records, producer_factory=None, topic=TOPIC, bootstrap_servers=BOOTSTRAP):
    if producer_factory is None:
        from kafka import KafkaProducer
        producer_factory = KafkaProducer
    producer = producer_factory(bootstrap_servers=bootstrap_servers, acks="all", retries=3,
                                max_in_flight_requests_per_connection=1,
                                request_timeout_ms=15000, max_block_ms=15000)
    sent = []
    try:
        for record in records:
            key, value = encode_record(record)
            metadata = producer.send(topic, key=key, value=value).get(timeout=20)
            item = (metadata.topic, metadata.partition, metadata.offset)
            sent.append(item)
            print("ACK", item)
        producer.flush(timeout=20)
        return sent
    finally:
        producer.close(timeout=5)
```

```python
import kafka
print("kafka-python:", kafka.__version__)
if kafka.__version__ != "2.2.15":
    raise RuntimeError("Pinned client not active; restart only this kernel after installation, then rerun setup")
inspect_topics(topic=TOPIC, bootstrap_servers=BOOTSTRAP)
```

## Create a fresh exercise topic explicitly
Set CREATE_TOPIC to True only for the first use of a new explicit topic name. The topic uses two partitions and replication factor one on the existing broker. Keep it False on resume. Existing topics are not reset or deleted.

```python
CREATE_TOPIC = False
if CREATE_TOPIC:
    create_topic(topic=TOPIC, bootstrap_servers=BOOTSTRAP)
else:
    print("Topic creation not requested")
```

```python
print("batch A transport records:", len(batch_a()))
print("accepted baseline:", expected_totals())
print("after batch B:", expected_totals(include_b=True))
```

## A. Send the initial batch once
Set SEND_A to True and run this cell once. Ten broker acknowledgements are expected: seven valid unique lines, one duplicate of L001, one zero-quantity record and one malformed JSON record. Prices are decimal strings. An ACK confirms a Kafka delivery, not an Iceberg commit.

```python
SEND_A = False
if SEND_A:
    delivered_a = send_records(batch_a(), topic=TOPIC, bootstrap_servers=BOOTSTRAP)
    print("ACKNOWLEDGED", len(delivered_a))
else:
    print("Set SEND_A=True to send the initial ten records")
```

## B. Later: send the incremental batch
Do this only after the initial Silver and country totals are verified. It adds L008 worth 50.00 and re-sends L002 unchanged. Expected total becomes 225.00, not 240.00. Kafka offsets are new for both deliveries.

```python
SEND_B = False
if SEND_B:
    delivered_b = send_records(batch_b(), topic=TOPIC, bootstrap_servers=BOOTSTRAP)
    print("ACKNOWLEDGED", len(delivered_b))
else:
    print("Batch B not requested")
```

## Optional deliberate replay
Re-publishing batch A creates ten more raw records. Bronze and rejection counts grow, but accepted Silver and country amounts must not grow. This differs from restarting Spark with its existing checkpoint and no new records, which should add nothing.

```python
REPLAY_A = False
if REPLAY_A:
    send_records(batch_a(), topic=TOPIC, bootstrap_servers=BOOTSTRAP)
else:
    print("Deliberate re-publication not requested")
```

Do not use Run All to send successive phases. Run the chosen send cell explicitly. The producer closes its connection after each call. A delivery error can leave ambiguous delivery; inspect before retrying. Stable line IDs protect Silver from identical re-publication, not from all possible business corrections.

## Optional: generate invoices every five seconds

Run the settings, Python client installation/version check, producer-function definitions and topic setup above first. This single cell generates invoices and calls the existing `send_records` function; no additional client or helper file is needed. It uses the existing `TOPIC` and `BOOTSTRAP` settings.

Each invoice has 3–10 item lines with the same invoice number, customer, country and timestamp. Each line has its own `LineID`. Timestamps use the pipeline's `yyyy-MM-dd HH:mm:ss` format, identifiers are strings and prices are decimal strings. Country is the Kafka key, as in the earlier producer.

The default is 20 invoices, with a five-second pause between invoices. Set `SAMPLES = None` to continue until **Interrupt Kernel** (the square stop button), or choose a larger finite count. The pause follows acknowledgement of all lines, so delivery time adds to the interval. This cell starts no Spark application and does not create or alter a topic.

Use a new explicit `RUN_LABEL` for each new generated run, or set `START_INVOICE` to the next unused number. Do not reuse a generated LineID with different random content: notebook 03 deliberately rejects conflicting immutable lines. The printed next number is useful after a clean run, but interrupted delivery can be ambiguous; use a new label after interruption or delivery failure.

**Run this after completing the fixed A/B acceptance checks.** Generated input changes the expected Bronze/Silver counts and country totals; 175.00/225.00 are no longer the expected totals. Start this cell in its own producer kernel while inspecting arrivals with notebook 02 or notebook 03's optional live mode. Keep Spark applications sequential as before. Stop the producer before draining the stream; with finite ingestion, rerun AvailableNow after production finishes.

```python
# Generate complete invoices using the existing producer function.
import random
import time
from datetime import datetime, timezone

SAMPLES = 20            # Number of invoices; None = run until Interrupt Kernel.
DELAY = 5               # Seconds to pause between acknowledged invoices.
RUN_LABEL = "live01"    # Change explicitly for a new run; no random topic/run IDs.
START_INVOICE = 10000   # First unused invoice number within this RUN_LABEL.

countries = [
    "USA", "CA", "IN", "AT", "BE", "BG", "HR", "CY",
    "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL",
    "PT", "RO", "SK", "SI", "ES", "SE",
]
stock_codes = ["85123A", "71053", "84406B", "84406G", "84406E"]
customer_codes = ["17850", "13047", "12583"]

if SAMPLES is not None and (not isinstance(SAMPLES, int) or SAMPLES <= 0):
    raise ValueError("SAMPLES must be a positive integer or None")
if DELAY < 0 or START_INVOICE < 0 or not RUN_LABEL.strip():
    raise ValueError("Use a nonnegative delay/start number and a nonblank RUN_LABEL")

invoices_sent = 0
lines_sent = 0
try:
    while SAMPLES is None or invoices_sent < SAMPLES:
        invoice_number = START_INVOICE + invoices_sent
        invoice_no = f"LIVE-{RUN_LABEL}-{invoice_number}"
        country = random.choice(countries)
        customer = random.choice(customer_codes)
        invoice_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        number_of_items = random.randint(3, 10)
        records = []
        for item_number in range(1, number_of_items + 1):
            stock_code = random.choice(stock_codes)
            records.append({
                "LineID": f"{invoice_no}-{item_number:02d}",
                "InvoiceNo": invoice_no,
                "StockCode": stock_code,
                "Quantity": random.randint(1, 10),
                "Description": f"Product {stock_code}",
                "InvoiceDate": invoice_date,
                "UnitPrice": f"{random.randint(1, 5)}.00",
                "CustomerID": customer,
                "Country": country,
            })

        acknowledged = send_records(records, topic=TOPIC, bootstrap_servers=BOOTSTRAP)
        invoices_sent += 1
        lines_sent += len(acknowledged)
        print("INVOICE_SENT", invoice_no, "country", country,
              "lines", len(acknowledged), "total_lines", lines_sent)
        if SAMPLES is None or invoices_sent < SAMPLES:
            time.sleep(DELAY)
except KeyboardInterrupt:
    print("Producer interrupted. Use a new RUN_LABEL before another generated run.")
finally:
    # send_records closes its Kafka producer in finally, including interruption.
    print("Completed invoices:", invoices_sent, "acknowledged lines:", lines_sent)
    print("Next invoice number after completed invoices:", START_INVOICE + invoices_sent)

```
