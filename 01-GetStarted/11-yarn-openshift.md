# YARN and MapReduce on OpenShift

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Run UI forwarding commands in separate VM terminals and keep them running while using their URLs.

Run commands one at a time and check each result before continuing. Enter heredocs and commands continued with `\` as complete units. If a command fails, resolve the error before running the next command.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Run the commands in the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a Bash terminal in the Linux VM after completing [Bash configuration](../00-bashrc.md). Run this once per terminal to load the cluster credentials and select `bigdata`. Continue only when it succeeds. If the cluster is stopped, run `okd-start`. If `okd-env` is not found, run `source ~/.bashrc` and retry.

```bash
okd-env
```

## 1. Start HDFS and the optional YARN services

The default low-memory profile keeps YARN stopped. This lesson starts one ResourceManager, one NodeManager and one MapReduce History Server.

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1
```

Wait for `statefulset/namenode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/namenode --timeout=300s
```

Wait for `statefulset/datanode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/datanode --timeout=300s
```

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale deployment/resourcemanager deployment/nodemanager deployment/historyserver --replicas=1
```

Wait for `deployment/resourcemanager` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/resourcemanager --timeout=300s
```

Wait for `deployment/nodemanager` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/nodemanager --timeout=300s
```

Wait for `deployment/historyserver` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/historyserver --timeout=300s
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l 'app in (resourcemanager,nodemanager,historyserver)' -o wide
```

## 2. Inspect YARN Services and registered nodes

Inspect the workload definitions and Services for these components.

```bash
oc -n bigdata get deployment,service -l 'app in (resourcemanager,nodemanager,historyserver)' -o wide
```

List YARN nodes and confirm that a NodeManager is registered.

```bash
oc -n bigdata exec deployment/resourcemanager -- yarn node -list -all
```

List YARN applications, including completed jobs, and note an application ID for inspection.

```bash
oc -n bigdata exec deployment/resourcemanager -- yarn application -list -appStates ALL
```

## 3. Create word-count input in HDFS

Create the sample text file inside the NameNode container.

```bash
oc -n bigdata exec namenode-0 -- sh -c "printf 'hadoop spark hive\nhadoop yarn spark\nopenshift hadoop\n' > /tmp/words.txt"
```

Create the HDFS input directory. `-p` also creates missing parent directories.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/mapreduce/input
```

Upload the container file into HDFS. `-f` replaces only the named sample input file.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/words.txt /training/mapreduce/input/words.txt
```

Reference only: keep this deletion command commented out.

```bash
# oc -n bigdata exec namenode-0 -- hdfs dfs -rm -r -f /training/mapreduce/output
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/mapreduce/input/words.txt
```

## 4. Run MapReduce word count

Before submitting, check that the NodeManager Service exposes the MapReduce shuffle port. A Ready NodeManager can run the mapper while reducers fail to fetch its output if this port is missing.

```bash
oc -n bigdata get service nodemanager -o jsonpath='{range .spec.ports[*]}{.name}{" "}{.port}{" -> "}{.targetPort}{"\n"}{end}'
```

The list must include TCP port `13562` targeting `13562`. Older cloned labs may omit it. Only if it is missing, add the port with this targeted Service patch. This preserves the other ports and does not restart the NodeManager or change replicas.

```bash
oc -n bigdata patch service nodemanager --type=strategic -p '{"spec":{"ports":[{"name":"shuffle","port":13562,"targetPort":13562,"protocol":"TCP"}]}}'
```

Repeat the inspection command and confirm `shuffle 13562 -> 13562`. This fixes the confirmed missing-Service-port issue; it does not diagnose every possible shuffle failure. If reducers still fail, inspect the application's task diagnostics in the History Server.

Submit the MapReduce word-count job and wait for successful completion. The output directory must not already exist.

```bash
oc -n bigdata exec deployment/resourcemanager -- hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /training/mapreduce/input /training/mapreduce/output
```

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/mapreduce/output
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/mapreduce/output/part-r-00000
```

## 5. Run the MapReduce Pi example

Run the MapReduce Pi example and wait for its estimate.

```bash
oc -n bigdata exec deployment/resourcemanager -- hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 100
```

## 6. Inspect applications and logs

List YARN applications, including completed jobs, and note an application ID for inspection.

```bash
oc -n bigdata exec deployment/resourcemanager -- yarn application -list -appStates ALL
```

Copy an application ID from the list above into `APP_ID`, replacing the example below.

```bash
APP_ID=application_REPLACE_WITH_YOUR_ID
```

Inspect the selected application status. Run this in the same terminal where you set `APP_ID`.

```bash
oc -n bigdata exec deployment/resourcemanager -- yarn application -status "$APP_ID"
```

## 7. Open YARN web interfaces locally

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18088 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/resourcemanager 18088:8088
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18042 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/nodemanager 18042:8042
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:19888 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/historyserver 19888:19888
```

## 8. Restart or stop YARN

HDFS data remains available when YARN is stopped.

Restart these workloads. Their persistent volumes remain attached; wait for readiness in the following steps.

```bash
oc -n bigdata rollout restart deployment/resourcemanager deployment/nodemanager deployment/historyserver
```

Wait for `deployment/resourcemanager` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/resourcemanager --timeout=300s
```

Wait for `deployment/nodemanager` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/nodemanager --timeout=300s
```

Wait for `deployment/historyserver` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/historyserver --timeout=300s
```

List YARN nodes and confirm that a NodeManager is registered.

```bash
oc -n bigdata exec deployment/resourcemanager -- yarn node -list -all
```

Stop these workloads without deleting their storage.

```bash
oc -n bigdata scale deployment/resourcemanager deployment/nodemanager deployment/historyserver --replicas=0
```

Inspect the workload definitions and Services for these components.

```bash
oc -n bigdata get deployment resourcemanager nodemanager historyserver
```

## Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Run follow commands in a separate VM terminal after `okd-env`. Press Ctrl+C to stop following; this does not stop the workload. A scaled-to-zero workload has no current pod logs.

Follow ResourceManager logs while a MapReduce job runs. YARN must be started first.

```bash
oc -n bigdata logs -f deployment/resourcemanager --tail=50 --timestamps
```

Read NodeManager logs for container startup errors.

```bash
oc -n bigdata logs deployment/nodemanager --since=10m --timestamps
```

Read MapReduce History Server logs while that optional service is running.

```bash
oc -n bigdata logs deployment/historyserver --tail=50 --timestamps
```
