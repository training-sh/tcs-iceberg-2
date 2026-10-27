# Spark standalone master on OpenShift

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Run UI forwarding commands in separate VM terminals and keep them running while using their URLs.

Run commands one at a time and check each result before continuing. Enter heredocs and commands continued with `\` as complete units. If a command fails, resolve the error before running the next command.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Run the commands in the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a Bash terminal in the Linux VM after completing [Bash configuration](../00-bashrc.md). Run this once per terminal to load the cluster credentials and select `bigdata`. Continue only when it succeeds. If the cluster is stopped, run `okd-start`. If `okd-env` is not found, run `source ~/.bashrc` and retry.

```bash
okd-env
```

## 1. Inspect Spark resources

Spark standalone uses one master pod and one scalable worker StatefulSet. The master pod also contains the History Server and JupyterLab containers.

Inspect the workload definitions and Services for these components.

```bash
oc -n bigdata get statefulset/spark-master statefulset/spark-worker service/spark-master service/spark-worker -o wide
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l 'app in (spark-master,spark-worker)' -o wide
```

Show the container names inside this pod. Use these names with `oc exec -c` or `oc logs -c`.

```bash
oc -n bigdata get pod spark-master-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
```

## 2. Start Spark and wait for readiness

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/spark-master statefulset/spark-worker --replicas=1
```

Wait for `statefulset/spark-master` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
```

Wait for `statefulset/spark-worker` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l 'app in (spark-master,spark-worker)'
```

## 3. Check the master and worker processes

Read recent logs from `spark-master-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs spark-master-0 -c spark-master --tail=40
```

Read recent logs from `spark-worker-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs spark-worker-0 -c spark-worker --tail=40
```

Check that the Spark master and worker service names resolve from inside the cluster.

```bash
oc -n bigdata exec spark-master-0 -c spark-master -- bash -c 'getent hosts spark-master; getent hosts spark-worker-0.spark-worker'
```

## 4. Open Spark UIs inside the VM

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18080 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18080:8080
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18081 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-worker 18081:8081
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18082 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18082:18080
```

## 5. Scale workers

Each worker is configured for one Spark core and 1 GiB of Spark worker memory. Keep one worker for the 16 GiB CRC profile unless another lesson requires more.

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/spark-worker --replicas=1
```

Wait for `statefulset/spark-worker` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l app=spark-worker -o wide
```

## 6. Restart and stop Spark

Save notebooks and finish or stop active Spark jobs before continuing. Restarting the master pod also restarts JupyterLab and the History Server and interrupts notebook sessions. Port-forward commands may exit when their selected pod restarts; start them again after the rollout succeeds.

Restart these workloads. Their persistent volumes remain attached; wait for readiness in the following steps.

```bash
oc -n bigdata rollout restart statefulset/spark-master statefulset/spark-worker
```

Wait for `statefulset/spark-master` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
```

Wait for `statefulset/spark-worker` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

### Optional: stop and start again

Skip this stop while using Jupyter or continuing to lesson 17. Jupyter is a container in the master pod, so stopping the master also stops the notebook server.

Stop these workloads without deleting their storage.

```bash
oc -n bigdata scale statefulset/spark-worker statefulset/spark-master --replicas=0
```

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/spark-master statefulset/spark-worker --replicas=1
```

Wait for both workloads before reopening Jupyter or continuing to another lesson.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
```

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

## Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Run follow commands in a separate VM terminal after `okd-env`. Press Ctrl+C to stop following; this does not stop the workload. A scaled-to-zero workload has no current pod logs.

Follow the Spark master container logs.

```bash
oc -n bigdata logs -f spark-master-0 -c spark-master --tail=50 --timestamps
```

Read worker scheduling and executor startup logs.

```bash
oc -n bigdata logs spark-worker-0 -c spark-worker --since=10m --timestamps
```

Read Spark History Server logs.

```bash
oc -n bigdata logs spark-master-0 -c spark-history --tail=50 --timestamps
```
