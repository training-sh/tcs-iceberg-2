# troubleshoot

refer start-stop.md to stop yarn and other not used components

Troubleshooting lab

crc stop
or 
crc stop --force

--
for terminal

renew tokens

crc console --credentials

copy the oc login for kubeadmin

oc whoami

kubeadmin

--

crc start


degrade warning, wait for 2-3 minutes
-----

crc start 

console url 

login as kubeadmin

--

Close as many google chrome tab

----




```
oc get co
```

stop trino and airflow

```
source ~/openshift/env.sh
oc -n bigdata scale statefulset/airflow statefulset/trino --replicas=0
```

stop hiveserver2

```
oc -n bigdata scale deployment/hiveserver2 --replicas=0
```

stop yarn 
```
oc -n bigdata scale \
  deployment/resourcemanager \
  deployment/nodemanager \
  deployment/historyserver --replicas=0
```
stop grafana 

```
oc -n bigdata scale \
  statefulset/grafana statefulset/loki statefulset/alloy \
  deployment/bigdata-metrics --replicas=0
```

```
oc get co kube-controller-manager monitoring
oc -n openshift-monitoring get pods
```

