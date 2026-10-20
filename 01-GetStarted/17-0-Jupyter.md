# JupyterLab: launch, storage, access, and logs

This guide contains terminal commands only. The Python exercises are in [17-1-pypark.ipynb](17-1-pypark.ipynb). Complete [16 - Polaris](16-polaris.md) first and retain its `demo_catalog_temp.demo_database_temp.demo_table_temp` table and `demo-catalog-temp` S3 bucket.

Run one command at a time in the Linux VM terminal. Open browser URLs inside the VM through RDP. The notebook kernel connects directly to cluster Services; web port-forwards are only for browser access.

## 1. Load cluster access and find Jupyter

Load the helpers and select `bigdata`. Use `okd-start` first if CRC is stopped.

```bash
okd-env
```

List the Spark master pod. Jupyter is a container in `spark-master-0`, not a separate pod.

```bash
oc -n bigdata get pods -l app=spark-master -o wide
```

Show the three container names: `spark-master`, `spark-history`, and `jupyter`.

```bash
oc -n bigdata get pod spark-master-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
```

Show each container's readiness and restart count.

```bash
oc -n bigdata get pod spark-master-0 -o jsonpath='{range .status.containerStatuses[*]}{.name}{" ready="}{.ready}{" restarts="}{.restartCount}{"\n"}{end}'
```

Inspect scheduling, mounts, readiness, and pod events if a container is unhealthy.

```bash
oc -n bigdata describe pod spark-master-0
```

## 2. Start the notebook service and data services

Start the master pod if scaled down. Its entrypoint launches Jupyter automatically; do not start a second Jupyter server with `oc exec`.

```bash
oc -n bigdata scale statefulset/spark-master --replicas=1
```

Wait for the pod's containers to become ready.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
```

The notebook uses one standalone Spark worker. Start it if stopped.

```bash
oc -n bigdata scale statefulset/spark-worker --replicas=1
```

Wait for the worker to be ready.

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

Start HDFS if it was stopped in the HDFS lesson. A port-forward does not start stopped workloads.

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode --replicas=1
```

Wait for NameNode readiness.

```bash
oc -n bigdata rollout status statefulset/namenode --timeout=300s
```

Wait for DataNode readiness.

```bash
oc -n bigdata rollout status statefulset/datanode --timeout=300s
```

Confirm the other prerequisites are running. HiveServer2 and YARN are not required: Spark uses the Hive Metastore directly.

```bash
oc -n bigdata get pods -l 'app in (spark-master,spark-worker,namenode,datanode,hive-metastore,polaris,seaweedfs,postgres,mysql)' -o wide
```

Prepare a dedicated HDFS directory for notebook runs. The notebook driver and executors use the `spark` account; `/training` is owned by the HDFS lab account, so Spark cannot create a new child there until this directory is prepared.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/notebook-demo
```

Assign ownership of only this notebook parent directory to Spark. Do not change ownership recursively or change `/training` itself.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -chown spark /training/notebook-demo
```

Inspect the resulting owner and permissions before running the notebook.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls -d /training/notebook-demo
```

## 3. Understand notebook locations and persistence

| Location | Path | Meaning |
|---|---|---|
| Course source on Windows | `C:\Course\DataEng\tcs\tcs-iceberg-2\01-GetStarted\17-1-pypark.ipynb` | Versioned notebook source |
| Running Jupyter home | `/workspace` | Server root and notebook kernel's `$HOME` |
| Jupyter notebook directory | `/workspace/notebooks` | The only notebook working directory |
| Browser path | `notebooks/17-1-pypark.ipynb` | Path relative to Jupyter's root |
| Kubernetes storage | PVC `spark-notebooks`, mounted at `/workspace` | Survives pod replacement; deleting the PVC destroys its contents |

Use **`/workspace/notebooks` as the only notebook working directory**. Open, edit, execute, and save notebooks from JupyterLab there. The Windows repository file is the course template; no separate notebook directory under the VM user's home is needed. No pod or server restart is needed to add a notebook file.

Inspect the persistent volume claim. It must be `Bound`.

```bash
oc -n bigdata get pvc spark-notebooks
```

Show the Jupyter container's volume mounts.

```bash
oc -n bigdata get pod spark-master-0 -o jsonpath='{.spec.containers[?(@.name=="jupyter")].volumeMounts}{"\n"}'
```

A new `oc exec` process can inherit `HOME=/nonexistent` from the image even though the running Jupyter process sets `HOME=/workspace`. Set that environment explicitly when opening an inspection shell.

```bash
oc -n bigdata exec -it spark-master-0 -c jupyter -- env HOME=/workspace bash
```

Inside the container shell, switch to its persistent home directory.

```bash
cd "$HOME"
```

Print the current directory; expect `/workspace`.

```bash
pwd
```

List the home directory and existing notebook folders.

```bash
ls -la
```

Return to the VM before running the next `oc` commands.

```bash
exit
```

## 4. Open or upload the notebook in JupyterLab

Create the persistent notebook directory if it is missing. This directory is inside the pod's PVC mount, not the VM home directory.

```bash
oc -n bigdata exec spark-master-0 -c jupyter -- mkdir -p /workspace/notebooks
```

Inspect its contents. The prepared training VM already has `17-1-pypark.ipynb` and `17-1-pypark-executed.ipynb` here; open either in JupyterLab without copying it elsewhere.

```bash
oc -n bigdata exec spark-master-0 -c jupyter -- ls -lh /workspace/notebooks
```

For a fresh deployment, first open JupyterLab using section 5. In the file browser, open `notebooks`, click **Upload Files**, and select `17-1-pypark.ipynb` from this repository on the computer running your browser. With the browser inside the VM, make the source file available to that browser using your normal file transfer method. Upload directly into the Jupyter `notebooks` folder; do not create a second working directory on the VM. Do not replace an existing notebook containing edits you want to keep.

## 5. Inspect Service ports and forward JupyterLab

Inspect the Service shared by the Spark master, History Server, and Jupyter.

```bash
oc -n bigdata get service spark-master -o wide
```

Show its named ports and pod endpoints.

```bash
oc -n bigdata describe service spark-master
```

| Interface | Service port | VM browser port |
|---|---:|---:|
| Spark master RPC | 7077 | No browser UI |
| Spark master UI | 8080 | 18080 |
| Spark History UI | 18080 | 18082 in the optional forward below |
| JupyterLab | 8888 | 18888 |

In a separate VM terminal, run `okd-env`, then start the notebook forward and leave it running.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18888:8888
```

Open [JupyterLab](http://127.0.0.1:18888/lab?token=team1234) in the VM browser. The token is **`team1234`**; no separate username/password is required. Navigate to `notebooks`, then open `17-1-pypark.ipynb`. Its direct URL is [open the PySpark notebook](http://127.0.0.1:18888/lab/tree/notebooks/17-1-pypark.ipynb?token=team1234).

Choose the **Python 3** kernel and run cells from top to bottom. The first cells show resolved connections and verify lesson 16's retained data. Follow the notebook instructions if a prerequisite is missing. Save the notebook after the run. Shut down a previous Spark notebook kernel before starting another to avoid competing for the single worker.

The notebook runs inside Kubernetes. It uses `spark-master:7077`, `namenode:9000`, `hive-metastore:9083`, `polaris:8181`, and `seaweedfs:8333`; it does not use these browser port-forwards for data access.

Optionally forward the Spark master and History Server in another initialized VM terminal. Open `http://127.0.0.1:18080` for the master and `http://127.0.0.1:18082` for history; neither uses a login. Do not run this simultaneously with a helper already using `18080`. This notebook disables event logging, so its current run is visible on the master while active but is not added to the History Server.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18080:8080 18082:18080
```

## 6. Use expose-uis instead of manual web forwards

Stop the manual Jupyter forward and any optional Spark master forward with Ctrl+C first. The helper creates its own forwards; starting both on `18888` causes a port conflict.

Change to the reference deployment directory.

```bash
cd "$HOME/openshift"
```

Inspect readiness without opening ports. The helper requires `kubectl`; see lesson 15 if that command is missing. Passing the current context explicitly supports older copies of the helper.

```bash
python3 workspace/expose-uis.py --context "$(oc config current-context)" --only jupyter spark-master seaweed-admin --list
```

Start the three UIs. Jupyter remains on `18888`, Spark master on `18080`, and SeaweedFS admin on `19002`. Stop a SeaweedFS manual forward first if it occupies that port.

```bash
python3 workspace/expose-uis.py --context "$(oc config current-context)" --only jupyter spark-master seaweed-admin
```

Open the displayed URLs in the VM browser. Jupyter uses token `team1234`; Spark master has no login; SeaweedFS admin uses `team` / `team1234`. Press Q or Esc to stop the helper. It ignores Ctrl+C.

## 7. Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Use `-c` because the master pod has multiple containers. Run `-f` in a separate terminal; Ctrl+C stops following, not the server.

Follow Jupyter server and kernel lifecycle logs.

```bash
oc -n bigdata logs -f spark-master-0 -c jupyter --tail=50 --timestamps
```

Read Spark master scheduling logs.

```bash
oc -n bigdata logs spark-master-0 -c spark-master --since=10m --timestamps
```

Read worker startup and scheduling logs. Executor task details may also be written to worker files; driver results and exceptions appear in notebook cells, not necessarily in `oc logs`.

```bash
oc -n bigdata logs spark-worker-0 -c spark-worker --since=10m --timestamps
```

Read Polaris logs for catalog and authorization errors.

```bash
oc -n bigdata logs deployment/polaris -c polaris --since=10m --timestamps
```

Read Hive Metastore logs for namespace/table requests.

```bash
oc -n bigdata logs deployment/hive-metastore --since=10m --timestamps
```

Read SeaweedFS logs for object storage errors.

```bash
oc -n bigdata logs seaweedfs-0 -c seaweedfs --since=10m --timestamps
```

If the Jupyter container restarted, inspect its previous instance's logs. This command only works when a previous container log exists.

```bash
oc -n bigdata logs spark-master-0 -c jupyter --previous --tail=50
```

## 8. Save in JupyterLab

Use **File > Save Notebook** or Ctrl+S. Changes and cell outputs are saved directly to `/workspace/notebooks/17-1-pypark.ipynb` on the PVC. To retain a separate result file in the same directory, use **Save Notebook As** and choose another filename there. The prepared VM also contains `17-1-pypark-executed.ipynb`, with the verified run's results.

The notebook saves its retained table names and storage paths under `/workspace/notebooks/runs`. All notebook work stays under `/workspace/notebooks`; no host-side synchronization step is required.

Stopping a forward or shutting down the notebook kernel does not delete notebook files, HDFS data, or catalog tables. Keep lesson 16's resources and this notebook's run-specific examples for later inspection. Do not scale the master pod down while other users are working in Jupyter.
