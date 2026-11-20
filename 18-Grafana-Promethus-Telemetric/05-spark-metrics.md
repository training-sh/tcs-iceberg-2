# Spark metrics in Prometheus

Open **Observe → Metrics** in the OpenShift Administrator console. Paste one expression at a time and select **Run queries**. Use **Last 30 minutes** for graphs. A metric key is its Prometheus name. Labels such as `pod`, `container`, and `component` identify the series under that key. In the inventory queries, each result label `__name__` is a metric key and the numeric value counts matching series.

## Available keys by source

Snapshot verified against the lab on 20 November 2026. These catalogs list the keys that matched at query time. Kubernetes state and recording rules can add or remove keys as containers restart or change state.

| Exporter key | Meaning |
| --- | --- |
| `bigdata_service_up{component="spark"}` | Whether the exporter reached the Spark master endpoint |
| `bigdata_spark_workers` | Workers marked alive by the Spark master |
| `bigdata_spark_active_applications` | Active applications reported by the master |
| `bigdata_spark_cores` | Total cores registered by alive workers |
| `bigdata_spark_cores_used` | Cores in use across alive workers |

The exporter derives these gauges from the Spark master JSON endpoint. They describe the Spark cluster. For individual workers, use OpenShift pod metrics with `pod=~"spark-worker-.*"` and `container="spark-worker"`. The master pod also contains sidecars. Filter `container="spark-master"` when you need the master process alone.

<details>
<summary>Spark master pod series (50 metric names)</summary>

```text
cluster:namespace:pod_cpu:active:kube_pod_container_resource_limits
cluster:namespace:pod_cpu:active:kube_pod_container_resource_requests
cluster:namespace:pod_memory:active:kube_pod_container_resource_limits
cluster:namespace:pod_memory:active:kube_pod_container_resource_requests
container_cpu_cfs_periods_total
container_cpu_cfs_throttled_periods_total
container_cpu_usage_seconds_total
container_fs_reads_bytes_total
container_fs_reads_total
container_fs_usage_bytes
container_fs_writes_bytes_total
container_fs_writes_total
container_memory_cache
container_memory_rss
container_memory_swap
container_memory_usage_bytes
container_memory_working_set_bytes
container_network_receive_bytes_total
container_network_receive_packets_dropped_total
container_network_receive_packets_total
container_network_transmit_bytes_total
container_network_transmit_packets_dropped_total
container_network_transmit_packets_total
container_spec_cpu_shares
kube_pod_container_resource_limits
kube_pod_container_resource_requests
kube_pod_container_status_last_terminated_reason
kube_pod_container_status_restarts_total
kube_pod_container_status_waiting_reason
kube_pod_info
kube_pod_labels
kube_pod_owner
kube_pod_resource_limit
kube_pod_resource_request
kube_pod_status_phase
kube_pod_status_ready
kube_running_pod_ready
namespace_workload_pod:kube_pod_owner:relabel
node_namespace_pod:kube_pod_info:
node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate
node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m
node_namespace_pod_container:container_memory_cache
node_namespace_pod_container:container_memory_rss
node_namespace_pod_container:container_memory_swap
node_namespace_pod_container:container_memory_working_set_bytes
pod:container_cpu_usage:sum
pod:container_fs_usage_bytes:sum
pod_interface_network:container_network_receive_bytes:irate5m
pod_interface_network:container_network_transmit_bytes_total:irate5m
pod_network_name_info
```

</details>

<details>
<summary>Spark worker pod series (48 metric names)</summary>

```text
cluster:namespace:pod_cpu:active:kube_pod_container_resource_limits
cluster:namespace:pod_cpu:active:kube_pod_container_resource_requests
cluster:namespace:pod_memory:active:kube_pod_container_resource_limits
cluster:namespace:pod_memory:active:kube_pod_container_resource_requests
container_cpu_cfs_periods_total
container_cpu_cfs_throttled_periods_total
container_cpu_usage_seconds_total
container_fs_reads_bytes_total
container_fs_reads_total
container_fs_usage_bytes
container_fs_writes_bytes_total
container_fs_writes_total
container_memory_cache
container_memory_rss
container_memory_swap
container_memory_usage_bytes
container_memory_working_set_bytes
container_network_receive_bytes_total
container_network_receive_packets_dropped_total
container_network_receive_packets_total
container_network_transmit_bytes_total
container_network_transmit_packets_dropped_total
container_network_transmit_packets_total
container_spec_cpu_shares
kube_pod_container_resource_limits
kube_pod_container_resource_requests
kube_pod_container_status_restarts_total
kube_pod_info
kube_pod_labels
kube_pod_owner
kube_pod_resource_limit
kube_pod_resource_request
kube_pod_status_phase
kube_pod_status_ready
kube_running_pod_ready
namespace_workload_pod:kube_pod_owner:relabel
node_namespace_pod:kube_pod_info:
node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate
node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m
node_namespace_pod_container:container_memory_cache
node_namespace_pod_container:container_memory_rss
node_namespace_pod_container:container_memory_swap
node_namespace_pod_container:container_memory_working_set_bytes
pod:container_cpu_usage:sum
pod:container_fs_usage_bytes:sum
pod_interface_network:container_network_receive_bytes:irate5m
pod_interface_network:container_network_transmit_bytes_total:irate5m
pod_network_name_info
```

</details>

## List the keys and labels in the UI

List the four Spark application metric keys exposed by the exporter.

```promql
count by (__name__) ({namespace="bigdata",job="bigdata-metrics",__name__=~"bigdata_spark_.*"})
```

List the Spark pod and container labels that currently have working-set memory samples.

```promql
count by (pod, container) (container_memory_working_set_bytes{namespace="bigdata",pod=~"spark-(master|worker)-.*",container!="",container!="POD"})
```

List every currently available key carrying the master or worker pod label. Run these separately.

```promql
count by (__name__) ({namespace="bigdata",pod=~"spark-master-.*"})
```

```promql
count by (__name__) ({namespace="bigdata",pod=~"spark-worker-.*"})
```

## Query single metrics

Check whether the exporter reached Spark. A value of 1 confirms endpoint reachability.

```promql
bigdata_service_up{namespace="bigdata",component="spark"}
```

Check how many workers are registered and alive.

```promql
bigdata_spark_workers{namespace="bigdata"}
```

Read the number of active Spark applications.

```promql
bigdata_spark_active_applications{namespace="bigdata"}
```

Read the working-set memory of each worker container in MiB.

```promql
container_memory_working_set_bytes{namespace="bigdata",pod=~"spark-worker-.*",container="spark-worker"} / 1024^2
```

## Aggregate metrics

Compare master and worker CPU by pod, in cores averaged over five minutes. The container filter excludes sidecars.

```promql
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bigdata",pod=~"spark-(master|worker)-.*",container=~"spark-master|spark-worker"}[5m]))
```

Calculate the percentage of registered Spark cores in use. If no cores are registered, the denominator is floored at one to avoid division by zero.

```promql
100 * sum(bigdata_spark_cores_used{namespace="bigdata"}) / clamp_min(sum(bigdata_spark_cores{namespace="bigdata"}), 1)
```

Sum restart counters by pod across all containers, including sidecars.

```promql
sum by (pod) (kube_pod_container_status_restarts_total{namespace="bigdata",pod=~"spark-(master|worker)-.*"})
```

All examples and inventory queries were checked as instant and range requests against the lab Prometheus query backend.
