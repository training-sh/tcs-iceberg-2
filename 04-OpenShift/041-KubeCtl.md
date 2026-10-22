# kubectl with OpenShift

**Connect · Inspect · Read logs · Run commands · Forward ports · Understand manifests**

---

## 01 · What is kubectl?

`kubectl` is the Kubernetes command-line client. It sends requests to the cluster API to inspect and manage resources such as Pods, Deployments, Services and persistent storage claims.

OpenShift exposes Kubernetes APIs, so `kubectl` works with the existing OpenShift cluster. It uses the same kubeconfig and permissions as `oc` when both commands run with the same configuration.

```text
kubectl or oc
     │
     │  API address + credentials from kubeconfig
     ▼
OpenShift API → controllers and scheduler → node → Pod containers
```

`kubectl` manages cluster resources. `crc` manages the local cluster environment. Run both from the Ubuntu terminal.

Reference: [Kubernetes command-line tool](https://kubernetes.io/docs/concepts/overview/kubectl/).

---

## 02 · Prepare cluster access

```bash
okd-status
```

If OKD is stopped:

```bash
okd-start
```

Load access for the current terminal:

```bash
okd-env
```

Continue with namespace `bigdata`. Both `oc` and `kubectl` use the loaded kubeconfig.

---

## 03 · Verify the client

```bash
command -v kubectl
command -v oc
kubectl version --client
kubectl version
```

Use a `kubectl` version compatible with the Kubernetes server reported by the cluster. Kubernetes supports `kubectl` within one minor version older or newer than the API server; matching the server minor version is a straightforward choice.

If `kubectl` is missing, inspect the existing CRC client environment before installing another client:

```bash
eval "$(crc oc-env)"
command -v kubectl
command -v oc
```

The configured host already provides `/home/dev/.local/bin/kubectl`. It resolves to CRC's `oc` executable and successfully accepts Kubernetes commands under the `kubectl` name. A second installation is optional. Standard examples below can also be run with `oc` in place of `kubectl`.

### Install a standalone kubectl on Linux

Use this when `kubectl` is absent or when a separate upstream binary is required. The verified host is `x86_64`, which uses the `amd64` download. The example pins `v1.35.2`, matching the working client version and the running API server's `1.35` minor version.

Run this complete block in the Linux Bash session. It downloads the binary and checksum, verifies the download, then installs into a versioned user directory without replacing the existing CRC-managed command:

```bash
(
  set -euo pipefail
  KUBECTL_VERSION=v1.35.2
  case "$(uname -m)" in
    x86_64) KUBECTL_ARCH=amd64 ;;
    aarch64|arm64) KUBECTL_ARCH=arm64 ;;
    *) echo 'Select a supported kubectl architecture before continuing.' >&2; exit 1 ;;
  esac

  KUBECTL_TMP=$(mktemp -d)
  trap 'rm -f -- "$KUBECTL_TMP/kubectl" "$KUBECTL_TMP/kubectl.sha256"; rmdir -- "$KUBECTL_TMP"' EXIT
  cd "$KUBECTL_TMP"

  curl -fL --retry 3 -o kubectl \
    "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${KUBECTL_ARCH}/kubectl"
  curl -fL --retry 3 -o kubectl.sha256 \
    "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${KUBECTL_ARCH}/kubectl.sha256"
  printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum --check

  KUBECTL_DEST="$HOME/.local/share/kubectl/${KUBECTL_VERSION}"
  mkdir -p "$KUBECTL_DEST"
  install -m 0755 kubectl "$KUBECTL_DEST/kubectl"
  "$KUBECTL_DEST/kubectl" version --client
)
```

`curl`, `sha256sum` and `install` must be available on the host. No `sudo`, kubelet installation or cluster initialization is required.

Verify the standalone client against the existing OpenShift credentials:

```bash
okd-env
"$HOME/.local/share/kubectl/v1.35.2/kubectl" version
"$HOME/.local/share/kubectl/v1.35.2/kubectl" get nodes
"$HOME/.local/share/kubectl/v1.35.2/kubectl" -n bigdata get pods
```

To select it as `kubectl` for the current shell, prepend its directory **after** running `okd-env`:

```bash
export PATH="$HOME/.local/share/kubectl/v1.35.2:$PATH"
hash -r
command -v kubectl
kubectl version
```

`okd-env` can change client PATH ordering again. The full binary path always selects the standalone installation explicitly. Recheck version compatibility after upgrading the cluster.

Reference: [Kubernetes version compatibility](https://kubernetes.io/releases/version-skew-policy/), [Install kubectl on Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/).

---

## 04 · Understand kubeconfig and context

Kubeconfig connects three pieces of information:

| Entry | Purpose |
|---|---|
| Cluster | API endpoint and trust information |
| User | Credentials or authentication configuration |
| Context | Selected cluster, user and optional default namespace |

```bash
kubectl config get-contexts
kubectl config current-context
kubectl config view --minify
```

Both clients respect `KUBECONFIG`. Without it, the usual default is `$HOME/.kube/config`. In this environment, `okd-env` explicitly sets the stable CRC administrator file.

Use `-n bigdata` in commands to make the namespace explicit. To change the current context's default namespace instead:

```bash
kubectl config set-context --current --namespace=bigdata
```

This changes local client configuration, not application resources. Because `okd-env` refreshes the file, use explicit namespace flags for commands that should remain independent of that refresh.

Reference: [Organizing cluster access with kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).

---

## 05 · Read the command structure

```text
kubectl [global flags] VERB RESOURCE [NAME] [command flags]
```

```bash
kubectl -n bigdata get pods
kubectl -n bigdata get pod spark-master-0 -o wide
kubectl -n bigdata describe pod spark-master-0
```

| Part | Example | Meaning |
|---|---|---|
| Namespace | `-n bigdata` | Select the application namespace |
| Verb | `get` | List resources or retrieve one |
| Resource | `pod` | Select an API resource type |
| Name | `spark-master-0` | Select an existing object |
| Output | `-o wide` | Include additional columns |

Use `kubectl help` or `kubectl COMMAND --help` to inspect the installed client's options.

---

## 06 · Inspect the cluster and its workloads

```bash
kubectl cluster-info
kubectl get nodes -o wide
kubectl get namespaces
kubectl -n bigdata get deployments,statefulsets
kubectl -n bigdata get pods -o wide
kubectl -n bigdata get services
kubectl -n bigdata get pvc
```

| Resource | Short name | What to inspect |
|---|---|---|
| Pod | `po` | Readiness, status, restarts and assigned node |
| Deployment | `deploy` | Desired and available replicas |
| StatefulSet | `sts` | Stable replicas such as `spark-master-0` |
| Service | `svc` | Discovery names, selectors and ports |
| PersistentVolumeClaim | `pvc` | Storage request and binding status |
| ConfigMap | `cm` | Non-sensitive configuration |
| Namespace | `ns` | Resource grouping |

`kubectl get all` lists a resource category; it does not include every object. Inspect PVCs, ConfigMaps and other types explicitly.

---

## 07 · Inspect the existing data platform

The existing manifests and getting-started guides define these components:

| Area | Resources to inspect |
|---|---|
| HDFS | `namenode`, `datanode` StatefulSets |
| Spark | `spark-master`, `spark-worker` StatefulSets |
| YARN | `resourcemanager`, `nodemanager`, `historyserver` Deployments |
| Hive | Metastore and HiveServer2 Deployments |
| Object storage | `seaweedfs` StatefulSet |
| Iceberg catalog | `polaris` Deployment and its backing database |

Inspect the actual current replica counts; some components may intentionally be scaled down.

```bash
kubectl -n bigdata get sts,deploy
kubectl -n bigdata get pods -l 'app in (namenode,datanode)' -o wide
kubectl -n bigdata get pods -l 'app in (spark-master,spark-worker)' -o wide
kubectl -n bigdata get svc -l 'app in (spark-master,spark-worker)' -o wide
kubectl -n bigdata get pods --show-labels
```

`-l` selects labels. Labels are metadata attached to objects; they are separate from object names.

Related guide: [Platform architecture](../00-Introduction/03-Architecture.md).

---

## 08 · Read Pod and container details

Jupyter runs inside `spark-master-0` alongside `spark-master` and `spark-history`. Select the container when reading its logs or running a command.

```bash
kubectl -n bigdata describe pod spark-master-0

kubectl -n bigdata get pod spark-master-0 \
  -o jsonpath='{.spec.containers[*].name}{"\n"}'

kubectl -n bigdata get pod spark-master-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" ready="}{.ready}{" restarts="}{.restartCount}{"\n"}{end}'
```

`describe` includes scheduling decisions, mounts, health checks and recent Pod events. `get -o yaml` retrieves the API representation:

```bash
kubectl -n bigdata get statefulset spark-master -o yaml
kubectl -n bigdata get service spark-master -o yaml
kubectl explain pod.spec.containers
```

---

## 09 · Read application logs

```bash
kubectl -n bigdata logs spark-master-0 -c spark-master --tail=100
kubectl -n bigdata logs spark-master-0 -c spark-history --tail=100
kubectl -n bigdata logs spark-master-0 -c jupyter --tail=100
```

Follow new output until you press `Ctrl+C`:

```bash
kubectl -n bigdata logs -f spark-master-0 -c jupyter --tail=50
```

Read the previous terminated container's logs when a restart has occurred:

```bash
kubectl -n bigdata logs spark-master-0 -c jupyter --previous --tail=100
```

`--previous` needs a previous container instance. An error saying none exists is expected when that container has not restarted.

Container logs show standard output and standard error. They do not automatically include every application log file on disk.

---

## 10 · Run commands inside a container

Use `exec` to run a command in an existing, running container. `--` separates the Kubernetes command from the container command.

```bash
kubectl -n bigdata exec spark-master-0 -c spark-master -- hostname
kubectl -n bigdata exec spark-master-0 -c spark-master -- java -version
kubectl -n bigdata exec spark-master-0 -c jupyter -- ls -la /workspace/notebooks
kubectl -n bigdata exec namenode-0 -- hdfs dfs -ls /
```

For an interactive shell:

```bash
kubectl -n bigdata exec -it spark-master-0 -c spark-master -- /bin/bash
```

`-i` keeps input open and `-t` allocates a terminal. Run `exit` to leave the container shell. The image must contain the requested program; use `/bin/sh` if Bash is unavailable.

Run host administration commands in the Ubuntu terminal. Run application commands through `exec` when they require the software and network environment inside that container.

---

## 11 · Inspect Services, endpoints and storage

```bash
kubectl -n bigdata get service spark-master
kubectl -n bigdata describe service spark-master
kubectl -n bigdata get endpointslices \
  -l kubernetes.io/service-name=spark-master

kubectl get storageclasses
kubectl -n bigdata get pvc
kubectl -n bigdata describe pvc spark-notebooks
```

The Spark notebook volume is mounted at `/workspace` in the master and Jupyter containers. The existing notebook guide uses `/workspace/notebooks` for saved notebooks.

A Service selects backend Pods; a PVC requests storage. Neither object is another application process.

Related guide: [Jupyter storage and access](../01-GetStarted/17-0-Jupyter.md).

---

## 12 · Forward Jupyter to the Linux host

In the remote Linux session, load access and start the forward:

```bash
okd-env
kubectl -n bigdata port-forward --address=127.0.0.1 \
  service/spark-master 18888:8888
```

Keep this terminal running. The command maps **Linux host port `18888`** to **Service port `8888`**, which reaches the Jupyter container.

If using a browser inside the remote desktop, open:

```text
http://127.0.0.1:18888
```

If Jupyter requests authentication, follow the existing Jupyter setup and inspect its startup output as needed:

```bash
kubectl -n bigdata logs spark-master-0 -c jupyter --tail=100
```

A port-forward does not start a scaled-down StatefulSet. Check `kubectl -n bigdata get sts,pods` first. Reuse an existing forward if the host port is already occupied.

---

## 13 ? Use the Ubuntu browser

Keep the Jupyter port-forward from the previous section running. In Firefox or another browser inside Ubuntu, open:

```text
http://127.0.0.1:18888
```

Open the URL in the Ubuntu browser. Stop the forward with `Ctrl+C` when finished.

---

## 14 · Forward other existing services

Run selected forwards in separate Linux host terminals after `okd-env`. Each command stays active until `Ctrl+C`.

```bash
# Spark master web UI
kubectl -n bigdata port-forward --address=127.0.0.1 \
  service/spark-master 18080:8080

# Spark History Server
kubectl -n bigdata port-forward --address=127.0.0.1 \
  service/spark-master 18082:18080

# Polaris API and health endpoint
kubectl -n bigdata port-forward --address=127.0.0.1 \
  service/polaris 18181:8181 18182:8182

# SeaweedFS S3 API and administration UI
kubectl -n bigdata port-forward --address=127.0.0.1 \
  service/seaweedfs 19001:8333 19002:23646
```

Open the forwarded URLs in the Ubuntu browser. Forward only the ports you need.

Polaris and the S3 endpoint are APIs, rather than general-purpose web pages. Existing guides show their authentication and requests: [Polaris](../01-GetStarted/16-polaris.md), [SeaweedFS](../01-GetStarted/15-seaweedfs.md).

---

## 15 · OpenShift resources through kubectl

`kubectl` discovers API resources from the server. It can inspect OpenShift API objects as well as built-in Kubernetes objects when the current identity has permission.

```bash
kubectl api-resources --api-group=route.openshift.io
kubectl -n bigdata get routes.route.openshift.io
kubectl get clusteroperators.config.openshift.io
kubectl get clusterversions.config.openshift.io
```

`oc` adds convenient OpenShift commands and workflows:

| Task | kubectl | oc |
|---|---|---|
| List Pods | `kubectl -n bigdata get pods` | `oc -n bigdata get pods` |
| Read logs | `kubectl logs ...` | `oc logs ...` |
| Run a container command | `kubectl exec ...` | `oc exec ...` |
| Select default namespace | `kubectl config set-context --current --namespace=bigdata` | `oc project bigdata` |
| Log in through OpenShift | Use a configured kubeconfig | `oc login` |
| Show current OpenShift identity | Inspect authentication configuration or supported identity API | `oc whoami` |
| Enter a remote shell | `kubectl exec -it ... -- /bin/sh` | `oc rsh ...` |

The distinction is the additional client workflows. OpenShift resources are not hidden from `kubectl`.

Reference: [OpenShift CLI](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/cli_tools/openshift-cli-oc).

---

## 16 · Understand manifests before applying them

A manifest describes desired API objects. `apiVersion` selects the API, `kind` selects the resource type, `metadata` identifies it, and `spec` defines the desired configuration.

Inspect the existing Spark source on the Linux host:

```bash
cd "$HOME/openshift"
sed -n '1,115p' spark-image/openshift.yaml
```

Validate a chosen manifest without persisting its resources:

```bash
MANIFEST="$HOME/openshift/spark-image/openshift.yaml"
kubectl -n bigdata apply --dry-run=server -f "$MANIFEST"
```

Server dry-run exercises validation and admission. It does not prove that an application will start or have enough capacity. The source file can also differ from changes made by deployment scripts or from the running cluster.

Applying a manifest changes resources. For an intended deployment update, the command is:

```bash
# Run only when deliberately applying the selected deployment configuration.
# kubectl -n bigdata apply -f "$MANIFEST"
```

Keep the already deployed services intact while following inspection examples. Do not apply every file in `$HOME/openshift` as a directory-wide operation.

---

## 17 · Observe rollouts and permissions

Observe existing workload rollout status:

```bash
kubectl -n bigdata rollout status statefulset/spark-master --timeout=120s
kubectl -n bigdata rollout status deployment/polaris --timeout=120s
kubectl -n bigdata get pods -w
```

Press `Ctrl+C` to stop the watch. These commands observe state; they do not restart or scale a workload.

Check permissions without changing resources:

```bash
kubectl auth can-i get pods -n bigdata
kubectl auth can-i get pods/log -n bigdata
kubectl auth can-i create pods/exec -n bigdata
kubectl auth can-i --list -n bigdata
```

An authenticated identity can still receive `Forbidden` when its permissions do not allow an operation. Refreshing credentials does not grant new permissions.

---

## 18 · Troubleshoot access and application failures

| Symptom | First check |
|---|---|
| `kubectl: command not found` | Load `okd-env`; inspect `PATH` and the available client |
| `okd-env: command not found` | Load the existing `.bashrc` and check the Bash setup guide |
| Connection refused or API timeout | Check `crc status`, then refresh access with `okd-env` |
| API hostname cannot resolve | Run inside the configured host and check the kubeconfig endpoint and host DNS |
| Certificate error | Check endpoint, trusted CA and refreshed kubeconfig; do not disable TLS verification as a routine fix |
| `Unauthorized` | Check the selected kubeconfig and authentication |
| `Forbidden` | Check the current identity and RBAC |
| Resource `NotFound` | Confirm namespace, resource type, name and current deployment |
| `Pending` Pod | Inspect events, capacity, placement and PVC binding |
| `CrashLoopBackOff` | Inspect current and previous container logs |
| Forwarded UI unavailable | Check both forwards, port conflicts, Pod readiness and the selected Service port |

Use this sequence for a failing Spark master Pod:

```bash
kubectl -n bigdata get pods -o wide
kubectl -n bigdata describe pod spark-master-0
kubectl -n bigdata logs spark-master-0 -c spark-master --tail=100
kubectl -n bigdata get events --sort-by=.metadata.creationTimestamp
kubectl -n bigdata get svc,pvc
```

For resource usage, if the metrics API is available:

```bash
kubectl top nodes
kubectl -n bigdata top pods --containers
```

---

## 19 ? A short working sequence

```bash
okd-env
oc whoami
kubectl config current-context
kubectl get nodes
kubectl -n bigdata get sts,deploy,pods
kubectl -n bigdata get svc,pvc
kubectl -n bigdata logs spark-master-0 -c jupyter --tail=50
```

Continue with the component-specific commands in [01-GetStarted](../01-GetStarted/README.md). Standard `oc get`, `oc logs`, `oc exec` and `oc port-forward` examples map directly to their `kubectl` equivalents.

---

## 20 · Verified against the running environment

The following checks were executed in the configured Ubuntu environment after loading `okd-env`:

| Check | Observed result |
|---|---|
| API endpoint | `https://api.crc.testing:6443` |
| OpenShift identity | `system:admin` |
| Existing client path | `/home/dev/.local/bin/kubectl`, resolving to CRC's `oc` binary |
| Client Kubernetes version | `v1.35.2` |
| API server Kubernetes version | `v1.35.6` |
| OKD release | `4.22.0-okd-scos.10`, available and not progressing |
| Node | `crc`, `Ready` |
| Node operating system | CentOS Stream CoreOS 10 |
| Spark master | `spark-master-0`, `3/3` containers ready |
| Container execution | `kubectl exec ... -- hostname` returned `spark-master-0` |
| Container logs | Spark master logs were retrieved successfully |
| OpenShift API discovery | `kubectl` listed ClusterVersion and Route resources |
| Jupyter Route | `spark-jupyter-bigdata.apps-crc.testing` |
| Notebook storage | `spark-notebooks` PVC was `Bound` |

The `course-workspace` PVC was `Pending`; other listed application PVCs were `Bound`. Successful client access does not imply every resource is healthy. Inspect that claim separately if a workload needs it.

These checks used the already installed client. The standalone installation procedure is an optional documented alternative; it was not installed over the working setup. Browser access, forwarding sessions and manifest changes were not exercised by these read-only checks.
