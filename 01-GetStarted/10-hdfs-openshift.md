# HDFS on OpenShift: first operations

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Run UI forwarding commands in separate VM terminals and keep them running while using their URLs.

Run commands one at a time and check each result before continuing. Enter heredocs and commands continued with `\` as complete units. If a command fails, resolve the error before running the next command.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Run the commands in the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a Bash terminal in the Linux VM after completing [Bash configuration](../00-bashrc.md). Run this once per terminal to load the cluster credentials and select `bigdata`. Continue only when it succeeds. If the cluster is stopped, run `okd-start`. If `okd-env` is not found, run `source ~/.bashrc` and retry.

```bash
okd-env
```

## 1. Confirm the cluster and project

`oc` is the OpenShift command-line client. A project is an OpenShift namespace.

Show the OpenShift identity used by this terminal.

```bash
oc whoami
```

Show the current cluster context.

```bash
oc config current-context
```

Select the `bigdata` project for this terminal.

```bash
oc project bigdata
```

Inspect cluster node capacity and readiness. `-o wide` adds details such as node addresses.

```bash
oc get node -o wide
```

## 2. Inspect HDFS resources

HDFS uses one NameNode StatefulSet, one DataNode StatefulSet, two Services and persistent volume claims. First inspect the resource types, then inspect the containers inside each pod. `-n bigdata` selects the project; `-l` filters resources by label.

Inspect StatefulSets, which manage the stable pod identities and persistent storage used by these services.

```bash
oc -n bigdata get statefulset/namenode statefulset/datanode -o wide
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pod -l 'app in (namenode,datanode)' -o wide
```

Inspect Services, which give pods stable network names and ports.

```bash
oc -n bigdata get service/namenode service/datanode -o wide
```

Inspect persistent volume claims. Confirm `Bound` status and check requested storage.

```bash
oc -n bigdata get pvc data-namenode-0 data-datanode-0 -o wide
```

Display pod labels. The `-l` selector matches pods whose `app` label is `namenode` or `datanode`.

```bash
oc -n bigdata get pods -l 'app in (namenode,datanode)' --show-labels
```

Show the container names inside this pod. Use these names with `oc exec -c` or `oc logs -c`.

```bash
oc -n bigdata get pod namenode-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
```

Show the container names inside this pod. Use these names with `oc exec -c` or `oc logs -c`.

```bash
oc -n bigdata get pod datanode-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
```

## 3. Inspect memory, CPU and storage

Capacity is the physical node capacity. Allocatable resources are available to pods after platform reservations. Requests affect scheduling; limits cap individual containers.

Compare total node CPU and memory with the allocatable resources available to pods.

```bash
oc get nodes -o custom-columns='NODE:.metadata.name,CPU:.status.capacity.cpu,MEMORY:.status.capacity.memory,ALLOCATABLE_CPU:.status.allocatable.cpu,ALLOCATABLE_MEMORY:.status.allocatable.memory'
```

Inspect CPU and memory requests and limits already allocated on the node.

```bash
oc describe node | sed -n '/Allocated resources:/,/Events:/p'
```

Inspect StatefulSets, which manage the stable pod identities and persistent storage used by these services.

```bash
oc -n bigdata get statefulset namenode datanode -o custom-columns='NAME:.metadata.name,REPLICAS:.spec.replicas,READY:.status.readyReplicas'
```

Inspect persistent volume claims. Confirm `Bound` status and check requested storage.

```bash
oc -n bigdata get pvc -o custom-columns='PVC:.metadata.name,STATUS:.status.phase,SIZE:.status.capacity.storage,CLASS:.spec.storageClassName'
```

## 4. Start HDFS and check readiness

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

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l 'app in (namenode,datanode)'
```

Ask HDFS for its storage report. Confirm that a live DataNode is registered.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfsadmin -report
```

## 5. Run HDFS commands without opening a shell

Before writing data, the preceding `dfsadmin -report` must show one live DataNode, nonzero capacity and no `Safe mode is ON`. Ready pods alone do not prove DataNode registration.

If registration fails, inspect its logs:

```bash
oc -n bigdata logs datanode-0 --tail=60
```

For the confirmed `DisallowedDatanodeException` / hostname-resolution registration failure, inspect the isolated classroom correction from the course repository root:

```bash
python3 06-Polaris-Iceberg/patches/repair.py --fix hdfs
```

Only if that failure is present, save work and apply the correction. This rolls the NameNode without changing its image or persistent volumes:

```bash
python3 06-Polaris-Iceberg/patches/repair.py --fix hdfs --apply
```

Repeat `hdfs dfsadmin -report` and continue only after registration succeeds and safe mode clears. The patch relaxes reverse-hostname validation for this single-DataNode classroom profile; it is not needed on every clone. See [patch instructions](../06-Polaris-Iceberg/patches/README.md). Do not force safe mode off or format/delete storage to bypass a registration failure.

`oc exec` is the Kubernetes equivalent of `docker exec`. Everything after `--` runs inside the selected container.

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /
```

Create the HDFS input directory. `-p` also creates missing parent directories.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/hello/input
```

Create the sample text file inside the NameNode container.

```bash
oc -n bigdata exec namenode-0 -- sh -c "printf 'hello hdfs\nhello openshift\n' > /tmp/hello.txt"
```

Upload the container file into HDFS. `-f` replaces only the named sample input file.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/hello.txt /training/hello/input/hello.txt
```

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls -h /training/hello/input
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/hello/input/hello.txt
```

Download the HDFS file into the container filesystem.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -get -f /training/hello/input/hello.txt /tmp/hello-from-hdfs.txt
```

Read the file inside the container to verify its contents.

```bash
oc -n bigdata exec namenode-0 -- cat /tmp/hello-from-hdfs.txt
```

Create a local working directory on the VM for lesson files.

```bash
mkdir -p .state
```

Copy the file from the pod to the VM working directory.

```bash
oc -n bigdata cp namenode-0:/tmp/hello-from-hdfs.txt .state/hello-from-hdfs.txt -c namenode
```

Read the downloaded file on the VM and compare it with the HDFS source.

```bash
cat .state/hello-from-hdfs.txt
```

## 6. Open an interactive shell

Run this in a VM terminal. Exit the container shell with `exit`.

Open a Bash shell inside the NameNode container. The next command runs inside that container.

```bash
oc -n bigdata exec -it namenode-0 -- bash
```

Inside the container shell, list the HDFS input files.

```bash
hdfs dfs -ls /training/hello/input
```

Return from the container shell to the VM terminal before continuing.

```bash
exit
```

## 7. Copy files between the VM, a pod and HDFS

`oc cp` copies between the VM filesystem and a container. `hdfs dfs -put` then copies from the container filesystem into HDFS.

Create a local working directory on the VM for lesson files.

```bash
mkdir -p .state/hdfs-upload
```

Write a small sample text file on the VM.

```bash
printf 'red blue red\nblue green\n' > .state/hdfs-upload/colors.txt
```

Write a small sample text file on the VM.

```bash
printf 'one two three two\n' > .state/hdfs-upload/numbers.txt
```

Copy the local lesson file or directory from the VM into the selected container.

```bash
oc -n bigdata cp .state/hdfs-upload namenode-0:/tmp/hdfs-upload -c namenode
```

Create the HDFS input directory. `-p` also creates missing parent directories.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/uploads
```

Upload the container file into HDFS. `-f` replaces only the named sample input file.

```bash
oc -n bigdata exec namenode-0 -- sh -c 'hdfs dfs -put -f /tmp/hdfs-upload/* /training/uploads/'
```

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/uploads
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/uploads/colors.txt
```

## 8. Open the HDFS web interfaces locally

Keep each forwarding command running in its terminal. Open the URLs in the browser inside the VM.

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:19870 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/namenode 19870:9870
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:19864 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/datanode 19864:9864
```

## 9. View logs, restart and stop

Restarting pods preserves files because the NameNode and DataNode use PVCs. Scaling HDFS to zero stops the processes without deleting PVCs.

Read recent logs from `namenode-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs namenode-0 --tail=30
```

Read recent logs from `datanode-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs datanode-0 --tail=30
```

Restart these workloads. Their persistent volumes remain attached; wait for readiness in the following steps.

```bash
oc -n bigdata rollout restart statefulset/namenode statefulset/datanode
```

Wait for `statefulset/namenode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/namenode --timeout=300s
```

Wait for `statefulset/datanode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/datanode --timeout=300s
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/hello/input/hello.txt
```

### Optional: stop and start again

Skip this optional stop while continuing to the later lessons or Jupyter: they require HDFS to remain running. A port-forward cannot start a stopped NameNode.

Stop these workloads without deleting their storage.

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=0
```

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1
```

## 10. Useful troubleshooting commands

Read the most recent project events to find workload errors.

```bash
oc -n bigdata get events --sort-by=.lastTimestamp | tail -30
```

Inspect the NameNode conditions and events for scheduling or startup problems.

```bash
oc -n bigdata describe pod namenode-0 | sed -n '/Conditions:/,/Events:/p'
```

Check which pod addresses back the HDFS Services.

```bash
oc -n bigdata get endpointslice -l 'kubernetes.io/service-name in (namenode,datanode)' -o wide
```

## Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Run follow commands in a separate VM terminal after `okd-env`. Press Ctrl+C to stop following; this does not stop the workload. A scaled-to-zero workload has no current pod logs.

Follow NameNode logs while running HDFS commands.

```bash
oc -n bigdata logs -f namenode-0 --tail=50 --timestamps
```

Read recent DataNode logs for registration and storage errors.

```bash
oc -n bigdata logs datanode-0 --since=10m --timestamps
```
