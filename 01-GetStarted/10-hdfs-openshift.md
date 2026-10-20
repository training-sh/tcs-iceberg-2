# HDFS on OpenShift: first operations

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

## 1. Confirm the cluster and project

`oc` is the OpenShift command-line client. A project is an OpenShift namespace.

```bash
(
# 1. Confirm the cluster and project
set -euo pipefail
oc whoami
oc config current-context
oc project bigdata
oc get node -o wide
)
```

## 2. Inspect HDFS resources

HDFS uses one NameNode StatefulSet, one DataNode StatefulSet, two Services and persistent volume claims.

```bash
(
# 2. Inspect HDFS resources
set -euo pipefail
oc -n bigdata get statefulset,pod,service,pvc -l 'app in (namenode,datanode)' -o wide
echo
echo 'HDFS pods only:'
oc -n bigdata get pods -l 'app in (namenode,datanode)' --show-labels
echo
echo 'Containers in each HDFS pod:'
for pod in $(oc -n bigdata get pods -l 'app in (namenode,datanode)' -o name); do
  printf '%s: ' "$pod"
  oc -n bigdata get "$pod" -o jsonpath='{.spec.containers[*].name}'
  echo
done
)
```

## 3. Inspect memory, CPU and storage

Capacity is the physical node capacity. Allocatable resources are available to pods after platform reservations. Requests affect scheduling; limits cap individual containers.

```bash
(
# 3. Inspect memory, CPU and storage
set -euo pipefail
oc get nodes -o custom-columns='NODE:.metadata.name,CPU:.status.capacity.cpu,MEMORY:.status.capacity.memory,ALLOCATABLE_CPU:.status.allocatable.cpu,ALLOCATABLE_MEMORY:.status.allocatable.memory'
echo
oc describe node | sed -n '/Allocated resources:/,/Events:/p'
echo
oc -n bigdata get statefulset namenode datanode -o custom-columns='NAME:.metadata.name,REPLICAS:.spec.replicas,READY:.status.readyReplicas'
echo
oc -n bigdata get pvc -o custom-columns='PVC:.metadata.name,STATUS:.status.phase,SIZE:.status.capacity.storage,CLASS:.spec.storageClassName'
)
```

## 4. Start HDFS and check readiness

```bash
(
# 4. Start HDFS and check readiness
set -euo pipefail
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1
oc -n bigdata rollout status statefulset/namenode --timeout=300s
oc -n bigdata rollout status statefulset/datanode --timeout=300s
oc -n bigdata get pods -l 'app in (namenode,datanode)'
oc -n bigdata exec namenode-0 -- hdfs dfsadmin -report
)
```

## 5. Run HDFS commands without opening a shell

`oc exec` is the Kubernetes equivalent of `docker exec`. Everything after `--` runs inside the selected container.

```bash
(
# 5. Run HDFS commands without opening a shell
set -euo pipefail
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/hello/input
oc -n bigdata exec namenode-0 -- sh -c "printf 'hello hdfs\nhello openshift\n' > /tmp/hello.txt"
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/hello.txt /training/hello/input/hello.txt
oc -n bigdata exec namenode-0 -- hdfs dfs -ls -h /training/hello/input
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/hello/input/hello.txt
oc -n bigdata exec namenode-0 -- hdfs dfs -get -f /training/hello/input/hello.txt /tmp/hello-from-hdfs.txt
oc -n bigdata exec namenode-0 -- cat /tmp/hello-from-hdfs.txt
mkdir -p .state
oc -n bigdata cp namenode-0:/tmp/hello-from-hdfs.txt .state/hello-from-hdfs.txt -c namenode
cat .state/hello-from-hdfs.txt
)
```

## 6. Open an interactive shell

Run this in a VM terminal. Exit the container shell with `exit`.

```bash
(
# 6. Open an interactive shell
set -euo pipefail
echo 'Run: oc -n bigdata exec -it namenode-0 -- bash'
echo 'Then try: hdfs dfs -ls /training/hello/input'
)
```

## 7. Copy files between the VM, a pod and HDFS

`oc cp` copies between the VM filesystem and a container. `hdfs dfs -put` then copies from the container filesystem into HDFS.

```bash
(
# 7. Copy files between the VM, a pod and HDFS
set -euo pipefail
mkdir -p .state/hdfs-upload
printf 'red blue red\nblue green\n' > .state/hdfs-upload/colors.txt
printf 'one two three two\n' > .state/hdfs-upload/numbers.txt
oc -n bigdata cp .state/hdfs-upload namenode-0:/tmp/hdfs-upload -c namenode
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/uploads
# Expand the wildcard inside the container, not on the Linux VM.
oc -n bigdata exec namenode-0 -- sh -c 'hdfs dfs -put -f /tmp/hdfs-upload/* /training/uploads/'
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/uploads
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/uploads/colors.txt
)
```

## 8. Open the HDFS web interfaces locally

Keep each forwarding command running in its terminal. Open the URLs in the browser inside the VM.

```bash
(
# 8. Open the HDFS web interfaces locally
set -euo pipefail
echo 'Terminal 1: oc -n bigdata port-forward --address=127.0.0.1 service/namenode 19870:9870'
echo 'NameNode UI: http://127.0.0.1:19870'
echo
echo 'Terminal 2: oc -n bigdata port-forward --address=127.0.0.1 service/datanode 19864:9864'
echo 'DataNode UI: http://127.0.0.1:19864'
)
```

## 9. View logs, restart and stop

Restarting pods preserves files because the NameNode and DataNode use PVCs. Scaling HDFS to zero stops the processes without deleting PVCs.

```bash
(
# 9. View logs, restart and stop
set -euo pipefail
oc -n bigdata logs namenode-0 --tail=30
oc -n bigdata logs datanode-0 --tail=30
oc -n bigdata rollout restart statefulset/namenode statefulset/datanode
oc -n bigdata rollout status statefulset/namenode --timeout=300s
oc -n bigdata rollout status statefulset/datanode --timeout=300s
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/hello/input/hello.txt
)
```

```bash
(
# 9. View logs, restart and stop
set -euo pipefail
echo 'Optional stop:'
echo 'oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=0'
echo
echo 'Start again:'
echo 'oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1'
)
```

## 10. Useful troubleshooting commands

```bash
(
# 10. Useful troubleshooting commands
set -euo pipefail
oc -n bigdata get events --sort-by=.lastTimestamp | tail -30
oc -n bigdata describe pod namenode-0 | sed -n '/Conditions:/,/Events:/p'
oc -n bigdata get endpointslice -l 'kubernetes.io/service-name in (namenode,datanode)' -o wide
)
```
