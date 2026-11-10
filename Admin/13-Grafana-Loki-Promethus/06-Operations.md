# Operations

## Initial setup

Use only when the prepared deployment lacks the observability resources. This assumes its application environment, credentials, registry and host tools already exist. The full profile expects about 32 GiB VM RAM and six visible vCPUs. CRC uses 24 GiB and six CPUs.

The enablement helper can gracefully restart CRC. Save work and run outside an active session:

```bash
cd ~/openshift
bash observability/enable-native.sh
oc get co monitoring
oc -n openshift-monitoring get pods
oc -n openshift-user-workload-monitoring get pods
bash observability/install.sh
```

The installer uses pinned images and the existing registry workflow, creates persistent workloads and installs ServiceMonitors. Reapplying preserves paused replica counts. Use the README's explicit start commands afterward.

## Troubleshooting

```bash
oc -n bigdata get pods,pvc
oc -n bigdata get endpoints grafana prometheus loki bigdata-metrics
oc -n bigdata describe pod grafana-0
oc -n bigdata describe pod loki-0
oc -n bigdata describe pod alloy-0
oc -n bigdata get events --sort-by=.metadata.creationTimestamp
oc get co monitoring
```

| Symptom | Check |
|---|---|
| Missing pod | StatefulSet replicas and startup commands |
| Pending | Events, PVC binding and node resources |
| ImagePullBackOff | Pod events and registry/image availability |
| Grafana partly ready | Both Grafana and proxy containers |
| Metrics API 503 | Thanos readiness, native monitoring, service CA and proxy logs |
| Metrics API 403 | Supported query paths and `bigdata` namespace |
| Empty metrics | Running application, scrape discovery, labels and range |
| No Loki logs | Alloy replicas/logs, namespace and Loki readiness |
| Route 503 | Admission, Service endpoints and pod readiness |
| Route DNS failure | VM browser DNS and CRC ingress access |
| Forward disconnected | Pod readiness; restart forwarding |

```bash
oc -n bigdata logs grafana-0 -c grafana --tail=100
oc -n bigdata logs grafana-0 -c native-metrics-proxy --tail=100
oc -n bigdata logs statefulset/alloy --tail=100
oc -n bigdata logs statefulset/loki --tail=100
oc -n bigdata logs deployment/bigdata-metrics --tail=100
oc -n openshift-monitoring get pods
oc -n openshift-user-workload-monitoring get pods
```

## Pause and resume

Pause collection while keeping existing history queryable:

```bash
oc -n bigdata scale statefulset/alloy --replicas=0
# Resume
oc -n bigdata scale statefulset/alloy --replicas=1
oc -n bigdata rollout status statefulset/alloy --timeout=600s
```

Pause optional observability while retaining PVCs:

```bash
bash ~/openshift/observability/monitoring-control.sh stop
bash ~/openshift/observability/monitoring-control.sh status
# Restore saved counts
bash ~/openshift/observability/monitoring-control.sh start
```

Saved counts may include components already stopped before the pause. Use explicit README scaling to enable all four optional components. Keep native monitoring running: this environment uses Thanos for platform health checks. Native Prometheus is operator-managed.

## Remove tutorial routes

```bash
cd ~/openshift/13-Grafana-Loki-Promethus
oc delete -f metrics-logs.yaml
```

This removes only the three HTTP entry points. Services, pods and stored data remain. Ctrl+C stops port forwarding. Retain PVCs during a pause; deleting them destroys stored data.
