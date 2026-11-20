# Telemetry and OpenTelemetry

Telemetry is data collected from a running system to understand its behavior. In this lab it helps answer questions such as when a Spark pod's memory rose, how many queries Trino completed, and what a container logged when it restarted.

| Signal | What it records | Example |
| --- | --- | --- |
| Metrics | Numeric samples over time, identified by a name and labels | Spark workers registered with the master |
| Logs | Timestamped records of individual events | A container reporting an exception |
| Traces | Related spans that describe the steps of a request | An API call that spends time waiting on a database |

Applications emit or expose signals. Scrapers and collectors gather them and attach context such as project, pod or container. Backends retain the data and answer queries. A UI displays the results over a selected time range.

OpenTelemetry (OTel) provides instrumentation APIs, SDKs, conventions, a collector and the OTLP transport. For example, an instrumented application can send spans to an OTel Collector for processing and export to a trace backend. The exercises here use the following paths for application metrics and logs. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

| Data | Path |
| --- | --- |
| Spark and Trino metrics | Application HTTP endpoint → `bigdata-metrics` exporter → OpenShift user-workload Prometheus → Thanos → OpenShift console or Grafana |
| Pod CPU and memory | Kubelet → OpenShift platform Prometheus → Thanos → OpenShift console or Grafana |
| Container logs | OpenShift pod log API → Grafana Alloy → Loki → Grafana |

OpenShift Telemetry is Red Hat's term for remote cluster health reporting. The table describes local observability in this lab.

Start with [Prometheus](00-Promethus.md) to find when resource use changed. Then use [Loki](04-grafana-loki.md) to inspect what the same pods logged during that interval.
