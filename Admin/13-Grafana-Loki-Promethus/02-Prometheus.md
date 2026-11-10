# Prometheus and OpenShift metrics

Prometheus stores numeric samples as time series and queries them using PromQL. A series has a metric name and labels such as namespace, pod and container. Counters usually increase until a restart; gauges can rise or fall. Use `rate()` for a counter's per-second change.

Platform Prometheus monitors OpenShift. User-workload Prometheus scrapes application endpoints selected by ServiceMonitors. The `bigdata-metrics` exporter reads application health through JMX, REST and TCP checks. TCP reachability cannot prove that a SQL query is correct.

## Check discovery

```bash
oc -n openshift-monitoring get pods,svc
oc -n openshift-user-workload-monitoring get pods,svc
oc -n bigdata get servicemonitors
oc -n bigdata get servicemonitor training-bigdata-metrics -o yaml
oc -n bigdata get svc bigdata-metrics --show-labels
oc -n bigdata get endpoints bigdata-metrics
```

The existing ServiceMonitor matches Services labeled `app: bigdata-metrics`, then scrapes their named `http` port at `/metrics` every 30 seconds. The Service selects exporter pods. See [the ServiceMonitor definitions](../observability/30-servicemonitors.yaml).

## Read raw metrics

Keep this running in another terminal:

```bash
oc -n bigdata port-forward svc/bigdata-metrics 18000:8000
```

```bash
curl -fsS http://127.0.0.1:18000/metrics
oc adm top nodes
oc adm top pods -n bigdata
```

`oc adm top` gives recent resource usage. Prometheus provides historical series. Allow several scrape intervals after startup.

## Query in Grafana Explore

Complete the [README startup](README.md). Select **OpenShift Prometheus** in Explore, switch to code mode and run:

```promql
up{namespace="bigdata"}
```

`1` means the scrape succeeded; `0` means it failed. It does not establish full application correctness. An absent series can mean the endpoint was never discovered or its samples expired.

CPU cores used per pod:

```promql
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bigdata",container!="",container!="POD"}[5m]))
```

A value of `0.5` means about half a CPU core over that window. Memory working set in MiB:

```promql
sum by (pod) (container_memory_working_set_bytes{namespace="bigdata",container!="",container!="POD"}) / 1024 / 1024
```

Application examples:

```promql
bigdata_service_up
bigdata_spark_workers
bigdata_hdfs_live_datanodes
bigdata_hdfs_used_bytes
```

Use the forwarded API too:

```bash
curl -fsS -G http://127.0.0.1:19090/api/v1/query \
  --data-urlencode 'query=bigdata_service_up'
```

A response with `status: success` and an empty result means no matching samples. Start the corresponding application before interpreting missing metrics. The proxy exposes queries, not a targets web dashboard. Inspect ServiceMonitors, endpoints and exporter logs to troubleshoot scraping.

Use the OpenShift console **Observe → Metrics** for authorized platform queries. The project's proxy remains scoped to `bigdata`. Supplied retention is 12 hours for each native Prometheus tier, with separate size limits.

Background: [OpenShift Cluster Monitoring Operator](https://github.com/openshift/cluster-monitoring-operator).
