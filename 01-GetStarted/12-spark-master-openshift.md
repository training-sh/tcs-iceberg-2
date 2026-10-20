# Spark standalone master on OpenShift

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Examples that print forwarding commands show what to run in a separate terminal; keep each forward running while using its URL.

Strict-mode command blocks use `( ... )` subshells so their `set -euo pipefail` settings do not change or close your interactive terminal. Variables inside one such block do not carry into the next.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Copy each block into the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a terminal in the Linux VM. The one-time functions are installed by [00 - Installation](../00-Introduction/00-Installation.md). Load them, connect `oc` to the running CRC cluster, and select the `bigdata` project before continuing.

```bash
# Load the helpers into this terminal, then validate access.
source "$HOME/.bashrc"
if declare -F okd-env >/dev/null; then
  okd-env && oc whoami && oc project && oc get nodes
else
  echo 'Complete 00-Introduction/00-Installation.md first.' >&2
fi
```

## 1. Inspect Spark resources

Spark standalone uses one master pod and one scalable worker StatefulSet. The master pod also contains the History Server and JupyterLab containers.

```bash
(
# 1. Inspect Spark resources
set -euo pipefail
oc -n bigdata get statefulset,service -l 'app in (spark-master,spark-worker)' -o wide
oc -n bigdata get pods -l 'app in (spark-master,spark-worker)' -o wide
oc -n bigdata get pod spark-master-0 -o jsonpath='{.spec.containers[*].name}'; echo
)
```

## 2. Start Spark and wait for readiness

```bash
(
# 2. Start Spark and wait for readiness
set -euo pipefail
oc -n bigdata scale statefulset/spark-master statefulset/spark-worker --replicas=1
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
oc -n bigdata get pods -l 'app in (spark-master,spark-worker)'
)
```

## 3. Check the master and worker processes

```bash
(
# 3. Check the master and worker processes
set -euo pipefail
oc -n bigdata logs spark-master-0 -c spark-master --tail=40
oc -n bigdata logs spark-worker-0 -c spark-worker --tail=40
oc -n bigdata exec spark-master-0 -c spark-master -- bash -c 'getent hosts spark-master; getent hosts spark-worker-0.spark-worker'
)
```

## 4. Open Spark UIs inside the VM

```bash
(
# 4. Open Spark UIs inside the VM
set -euo pipefail
echo 'Master UI: oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18080:8080'
echo 'Open: http://127.0.0.1:18080'
echo
echo 'Worker UI: oc -n bigdata port-forward --address=127.0.0.1 service/spark-worker 18081:8081'
echo 'Open: http://127.0.0.1:18081'
echo
echo 'History UI: oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18082:18080'
echo 'Open: http://127.0.0.1:18082'
)
```

## 5. Scale workers

Each worker is configured for one Spark core and 1 GiB of Spark worker memory. Keep one worker for the 16 GiB CRC profile unless another lesson requires more.

```bash
(
# 5. Scale workers
set -euo pipefail
oc -n bigdata scale statefulset/spark-worker --replicas=1
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
oc -n bigdata get pods -l app=spark-worker -o wide
)
```

## 6. Restart and stop Spark

```bash
(
# 6. Restart and stop Spark
set -euo pipefail
oc -n bigdata rollout restart statefulset/spark-master statefulset/spark-worker
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
)
```

```bash
(
# 6. Restart and stop Spark
set -euo pipefail
echo 'Optional stop:'
echo 'oc -n bigdata scale statefulset/spark-worker statefulset/spark-master --replicas=0'
echo
echo 'Start again:'
echo 'oc -n bigdata scale statefulset/spark-master statefulset/spark-worker --replicas=1'
)
```
