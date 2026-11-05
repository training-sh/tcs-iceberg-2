# Consumer groups and offsets

The examples use `invoices-lake` and observer group `invoice-observer`. Use the exact names listed in the notebooks' first settings cells. Jupyter connects internally through `kafka:9092`; host commands below execute the existing Kafka tools inside the broker pod.

```bash
export PATH="$HOME/.crc/bin/oc:$PATH"
oc exec -n bigdata kafka-0 -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic invoices-lake
oc exec -n bigdata kafka-0 -- /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --list
oc exec -n bigdata kafka-0 -- /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group invoice-observer
```

`CURRENT-OFFSET` is the group's committed next read position for a partition. `LOG-END-OFFSET` is that partition's end position, and lag is their difference when both are known. Values are partition-local; do not sum raw offset numbers as invoice counts. A group might not appear before it has joined/committed.

Use the manual-commit cells in `02-invoice-consumer.ipynb` to inspect a record, commit its offset + 1 and observe the next read. The consumer function defined in notebook 02 commits only the processed record's partition/position, not unprocessed prefetched positions. The pinned kafka-python client requires the leader-epoch field; the example uses -1 for an unknown epoch.

Committing an observer position does not remove records and does not advance Spark. Spark uses its own query/checkpoint offsets; do not set `kafka.group.id` to the observer group in Spark. `earliest` is the fallback for a new group/query, not a reset instruction for an existing checkpoint.

Do not reset groups, delete topics or remove Spark checkpoints to replay this exercise. Re-run with the existing checkpoint for recovery, deliberately re-publish the same LineIDs to test business deduplication, or choose another fixed topic/lake/checkpoint set for an independent dataset.
