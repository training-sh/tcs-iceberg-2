# troubleshoot

```
oc get co
```

stop grafana 

```
oc -n bigdata scale \
  statefulset/grafana statefulset/loki statefulset/alloy \
  deployment/bigdata-metrics --replicas=0
```


