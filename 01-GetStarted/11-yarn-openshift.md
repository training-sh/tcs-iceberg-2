# YARN and MapReduce on OpenShift

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

## 1. Start HDFS and the optional YARN services

The default low-memory profile keeps YARN stopped. This lesson starts one ResourceManager, one NodeManager and one MapReduce History Server.

```bash
(
# 1. Start HDFS and the optional YARN services
set -euo pipefail
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1
oc -n bigdata rollout status statefulset/namenode --timeout=300s
oc -n bigdata rollout status statefulset/datanode --timeout=300s
oc -n bigdata scale deployment/resourcemanager deployment/nodemanager deployment/historyserver --replicas=1
for d in resourcemanager nodemanager historyserver; do oc -n bigdata rollout status deployment/$d --timeout=300s; done
oc -n bigdata get pods -l 'app in (resourcemanager,nodemanager,historyserver)' -o wide
)
```

## 2. Inspect YARN Services and registered nodes

```bash
(
# 2. Inspect YARN Services and registered nodes
set -euo pipefail
oc -n bigdata get deployment,service -l 'app in (resourcemanager,nodemanager,historyserver)' -o wide
oc -n bigdata exec deployment/resourcemanager -- yarn node -list -all
oc -n bigdata exec deployment/resourcemanager -- yarn application -list -appStates ALL
)
```

## 3. Create word-count input in HDFS

```bash
(
# 3. Create word-count input in HDFS
set -euo pipefail
oc -n bigdata exec namenode-0 -- sh -c "printf 'hadoop spark hive\nhadoop yarn spark\nopenshift hadoop\n' > /tmp/words.txt"
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/mapreduce/input
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/words.txt /training/mapreduce/input/words.txt
# DO NOT DELETE: reference only; keep this command commented out.
# oc -n bigdata exec namenode-0 -- hdfs dfs -rm -r -f /training/mapreduce/output
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/mapreduce/input/words.txt
)
```

## 4. Run MapReduce word count

```bash
(
# 4. Run MapReduce word count
set -euo pipefail
oc -n bigdata exec deployment/resourcemanager -- hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /training/mapreduce/input /training/mapreduce/output
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/mapreduce/output
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/mapreduce/output/part-r-00000
)
```

## 5. Run the MapReduce Pi example

```bash
(
# 5. Run the MapReduce Pi example
set -euo pipefail
oc -n bigdata exec deployment/resourcemanager -- hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 100
)
```

## 6. Inspect applications and logs

```bash
(
# 6. Inspect applications and logs
set -euo pipefail
oc -n bigdata exec deployment/resourcemanager -- yarn application -list -appStates ALL
APP_ID=$(oc -n bigdata exec deployment/resourcemanager -- yarn application -list -appStates ALL 2>/dev/null | awk '/application_/ {print $1}' | tail -1)
echo "Latest application: ${APP_ID:-none}"
if [[ -n "${APP_ID:-}" ]]; then
  oc -n bigdata exec deployment/resourcemanager -- yarn application -status "$APP_ID" || true
fi
)
```

## 7. Open YARN web interfaces locally

```bash
(
# 7. Open YARN web interfaces locally
set -euo pipefail
echo 'ResourceManager: oc -n bigdata port-forward --address=127.0.0.1 service/resourcemanager 18088:8088'
echo 'Open: http://127.0.0.1:18088'
echo
echo 'NodeManager: oc -n bigdata port-forward --address=127.0.0.1 service/nodemanager 18042:8042'
echo 'Open: http://127.0.0.1:18042'
echo
echo 'History Server: oc -n bigdata port-forward --address=127.0.0.1 service/historyserver 19888:19888'
echo 'Open: http://127.0.0.1:19888'
)
```

## 8. Restart or stop YARN

HDFS data remains available when YARN is stopped.

```bash
(
# 8. Restart or stop YARN
set -euo pipefail
oc -n bigdata rollout restart deployment/resourcemanager deployment/nodemanager deployment/historyserver
for d in resourcemanager nodemanager historyserver; do oc -n bigdata rollout status deployment/$d --timeout=300s; done
oc -n bigdata exec deployment/resourcemanager -- yarn node -list -all
)
```

```bash
(
# 8. Restart or stop YARN
set -euo pipefail
echo 'Stop YARN after this lesson:'
oc -n bigdata scale deployment/resourcemanager deployment/nodemanager deployment/historyserver --replicas=0
oc -n bigdata get deployment resourcemanager nodemanager historyserver
)
```
