# Grafana

Grafana queries backends and presents results in dashboards. A datasource defines the backend connection. A dashboard contains panels; Explore lets you investigate queries before saving a panel.

## Open and check

Follow the [README](README.md) to start Grafana and open `http://127.0.0.1:13000` or its HTTP route. Use the configured lab account.

```bash
oc -n bigdata get pod grafana-0
oc -n bigdata describe pod grafana-0
oc -n bigdata get svc grafana prometheus loki
curl -fsS http://127.0.0.1:13000/api/health
```

| Datasource | Server-side connection | Query language |
|---|---|---|
| OpenShift Prometheus | `http://127.0.0.1:9090` inside the Grafana pod, served by its sidecar | PromQL |
| Loki | `http://loki:3100` inside the namespace | LogQL |

The browser connects to Grafana, and Grafana connects to the backends. The datasource loopback address is inside the pod, separate from the VM's forwarded browser port. Datasources are provisioned by configuration.

## Explore and compare

1. Open Explore, choose OpenShift Prometheus and run `bigdata_service_up` in code mode.
2. Set the range to the last 15 minutes.
3. Choose Loki and run `{namespace="bigdata"} |~ "(?i)error|exception|failed"`.
4. Compare logs and pod CPU/memory over the same time range.

Open **Dashboards → Training** for provisioned dashboards. Component-specific dashboards require the corresponding application to be running and scraped. A stopped optional application may have no fresh samples.

## Create a panel

Create a new dashboard and visualization with OpenShift Prometheus. Enter:

```promql
sum by (pod) (container_memory_working_set_bytes{namespace="bigdata",container!="",container!="POD"})
```

Choose a time-series visualization, set the unit to bytes (IEC), and use `{{pod}}` as the legend. Name it **Pod memory working set** and save under a new dashboard name. Saving requires write permission. Provisioned dashboards can be replaced by configuration updates, so use a separate dashboard for experiments.

Grafana's PVC preserves settings and saved dashboards. Prometheus and Loki retain the underlying datasets independently. For an empty panel, test its query in Explore and check its datasource, labels, time range and backend readiness.
