airflow yaml 

```
cd ~

wget https://raw.githubusercontent.com/training-sh/tcs-iceberg-2/refs/heads/main/airflow/airflow.yaml


oc apply -f airflow.yaml
oc -n bigdata scale statefulset/airflow --replicas=1
oc -n bigdata get pod airflow-0 -w

```

--

airflow

to start airflow

```
oc -n bigdata scale statefulset/airflow --replicas=1
```

to check 
```
oc -n bigdata get pod airflow-0 -w
```

to restart if dag not found
```
oc -n bigdata rollout restart statefulset/airflow
```

