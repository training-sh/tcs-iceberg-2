# OKD on CRC: installation and cluster operations

This lab runs the community OKD distribution in a CodeReady Containers (CRC) virtual machine. **CRC installation and initial preparation are already complete on the supplied training VM. No installation is needed; the host requirements and installation instructions below are for information only.** The remaining setup is to complete the [full `.bashrc` replacement and validations](../00-bashrc.md) before using the startup helpers. Run selected operational shell blocks in a Bash terminal on the Linux VM; diagnostic and workload operations are separate examples, not a script to run from top to bottom. Commands that begin with `sudo` require the VM user's sudo access.

## Software and data locations

| Purpose | Location |
|---|---|
| Course deployment files | `$HOME/openshift` |
| Stable administrator kubeconfig | `$HOME/.kube/crc-admin.kubeconfig` |
| CRC program installed by this course | `$HOME/.local/bin/crc` |
| CRC configuration, cache and VM disks | `$HOME/.crc` |
| Active CRC virtual disk | `$HOME/.crc/machines/crc/crc.qcow2` |
| Extracted OKD base image cache | `$HOME/.crc/cache` |
| System libvirt virtual machine | `crc` |
| Big-data Kubernetes project | `bigdata` |

The OKD operating system and cluster data are stored inside the CRC virtual disk. `/opt` on the Linux host is separate from the CRC installation.

## Verify host requirements

CRC uses KVM and the system libvirt service. The login user should belong to the `libvirt` and `kvm` groups. A new group membership becomes active after signing out and signing in again.

```bash
uname -m
egrep -c '(vmx|svm)' /proc/cpuinfo
id
systemctl is-active libvirtd
sudo virsh -c qemu:///system list --all
free -h
df -h /
```

If the required groups are missing, add the current user and then sign out of the VM completely and sign in again.

```bash
sudo usermod -aG libvirt,kvm "$USER"
getent group libvirt
getent group kvm
```

## Install and prepare CRC

**For information only: host packages, CRC installation, and initial configuration are already complete on the supplied training VM. Skip both setup blocks in this section and continue with [Configure `.bashrc`](#configure-bashrc).**

The commands below document the original installation procedure. They run as the ordinary sudo-capable login user. The download is skipped when `$HOME/.local/bin/crc` already exists.

```bash
sudo apt-get update
sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients network-manager apache2-utils skopeo curl xz-utils python3-boto3
mkdir -p "$HOME/.local/bin" "$HOME/downloads"
if [[ ! -x "$HOME/.local/bin/crc" ]]; then
  curl -fL --retry 2 \
    https://developers.redhat.com/content-gateway/rest/mirror/pub/cgw/crc/2.64.0/crc-linux-amd64.tar.xz \
    -o "$HOME/downloads/crc-linux-amd64.tar.xz"
  tar -xf "$HOME/downloads/crc-linux-amd64.tar.xz" -C "$HOME/downloads"
  find "$HOME/downloads" -name crc -type f -exec cp {} "$HOME/.local/bin/crc" \;
  chmod 755 "$HOME/.local/bin/crc"
fi
export PATH="$HOME/.local/bin:$PATH"
crc version
crc config set consent-telemetry no
crc config set preset okd
crc config set cpus 4
crc config set memory 16384
crc config set disk-size 50
crc setup
crc config view
```

For the classroom profile, configure four virtual CPUs, 16 GiB of memory, and a 50 GiB CRC disk before the first start. CRC memory is specified in MiB. Increasing the disk setting after creation does not resize an existing virtual disk.

```bash
crc config set preset okd
crc config set consent-telemetry no
crc config set cpus 4
crc config set memory 16384
crc config set disk-size 50
crc config view
```

## Start OKD and load the command environment

After installing the [`.bashrc` functions](../00-bashrc.md), `okd-start` starts CRC and prepares `oc`. The first start can take several minutes.

```bash
# First paste the full replacement block and session additions from 00-bashrc.md and load .bashrc.
# This starts CRC and refreshes the stable administrator kubeconfig.
okd-start && oc whoami && oc get nodes
```

The [`.bashrc` functions](../00-bashrc.md) load CRC's `oc` client and copy CRC's current administrator kubeconfig from `$HOME/.crc/machines/crc/kubeconfig` to `$HOME/.kube/crc-admin.kubeconfig`. Every `okd-env` call explicitly exports that stable destination; `crc oc-env` only configures the client PATH. The destination file is created by a successful `okd-start` or `okd-env`, not merely by sourcing `.bashrc`. This keeps terminal initialization independent of the course repository.

## Configure `.bashrc`

Follow [00 - Bash configuration](../00-bashrc.md) to back up your file, paste the full replacement block, append the remaining session setup, and run all three validations. That guide provides the copyable full-file replacement block and append-only PATH/session blocks, including cloned-VM recovery.

The helpers use `KUBECONFIG="$HOME/.kube/crc-admin.kubeconfig"`. `okd-env` refreshes this copy from CRC and checks authentication; sourcing `.bashrc` alone does not create it.


Start CRC and load the OKD environment with `okd-start`. In later terminals, use `okd-env` when the cluster is already running. These functions work without changing directory and without sourcing a file from the course repository.

```bash
okd-start
oc whoami
oc project
oc get nodes
oc get pods -n bigdata
```

`$HOME/.local/bin` is the standard per-user location used here for `crc`. Adding it to the front of `PATH` does not change Java, Hadoop, Hive, Spark, or Kafka installations. A command with the same name in this directory takes precedence over a system command. Check the resolved programs after installation; `crc oc-env` then selects the `oc` client supplied with CRC.

```bash
type -a crc
type -a oc
type -a kubectl
command -v crc
command -v oc
command -v kubectl
crc version
oc version --client
kubectl version --client
```

```bash
okd-env
printf 'KUBECONFIG=%s\n' "$KUBECONFIG"
oc version
oc cluster-info
```

## Check cluster status

`crc status` checks the CRC virtual machine. The `oc` commands check the Kubernetes API, nodes, OpenShift cluster operators, projects, and workloads.

```bash
okd-status
okd-env
oc get nodes -o wide
oc get clusterversion
oc get clusteroperators
oc get projects
oc get pods -n bigdata -o wide
oc get deployments,statefulsets,services,pvc -n bigdata
```

A healthy single-node lab has one `Ready` node. Cluster operators may briefly show `PROGRESSING=True` after startup. Investigate an operator when it remains degraded or unavailable.

```bash
oc describe clusteroperator authentication
oc get events -A --sort-by=.lastTimestamp | tail -50
oc get pods -A | grep -vE 'Running|Completed'
```

For another operator, replace `authentication` with a name from `oc get clusteroperators`.

## Stop, start, and restart the whole OKD cluster

Stop CRC cleanly before shutting down or cloning the Linux VM. CRC has start and stop operations; a controlled restart is a stop followed by a start.

```bash
okd-stop
sudo virsh -c qemu:///system domstate crc
```

```bash
# First paste the full replacement block and session additions from 00-bashrc.md and load .bashrc.
# This starts CRC and refreshes the stable administrator kubeconfig.
okd-start && oc whoami && oc get nodes
```

For a full restart, run the stop block, wait until `domstate` reports `shut off`, and then run the start block. Do not use `crc delete` for restart: it permanently removes the CRC cluster and its data.

## Manage workloads with `oc`

These operations affect applications inside OKD and do not stop the CRC virtual machine. Set `POD` and `DEPLOYMENT` to actual names from the corresponding `oc get` listings. Restart and scale operations change workloads. **DO NOT DELETE lab resources**; the deletion example is commented with `#` so Bash will not execute it.

```bash
oc -n bigdata get pods
oc -n bigdata get pod "${POD:?Set POD from oc -n bigdata get pods}" -o yaml
oc -n bigdata describe pod "${POD:?Set POD from oc -n bigdata get pods}"
oc -n bigdata logs "${POD:?Set POD from oc -n bigdata get pods}" --all-containers --tail=100
oc -n bigdata exec -it "${POD:?Set POD from oc -n bigdata get pods}" -- bash
```

```bash
oc -n bigdata rollout restart deployment/"${DEPLOYMENT:?Set DEPLOYMENT from oc -n bigdata get deployments}"
oc -n bigdata rollout status deployment/"${DEPLOYMENT:?Set DEPLOYMENT from oc -n bigdata get deployments}" --timeout=5m
oc -n bigdata scale deployment/"${DEPLOYMENT:?Set DEPLOYMENT from oc -n bigdata get deployments}" --replicas=0
oc -n bigdata scale deployment/"${DEPLOYMENT:?Set DEPLOYMENT from oc -n bigdata get deployments}" --replicas=1
# DO NOT DELETE: commented out to avoid accidental execution. Keep the #.
# oc -n bigdata delete pod "${POD:?Set POD from oc -n bigdata get pods}"
```

Deleting a pod managed by a Deployment or StatefulSet makes its controller create a replacement. Scaling to zero is the normal way to stop a Deployment until it is needed again.

## Use `kubectl` with OKD

OKD exposes a Kubernetes API, so standard `kubectl` commands work with the same kubeconfig. `oc` includes Kubernetes operations and adds OpenShift operations such as projects, routes, image streams, builds, OAuth, and cluster operators. Prefer `oc` throughout this course.

```bash
okd-env
kubectl version --client
kubectl config current-context
kubectl get nodes
kubectl -n bigdata get pods,services
kubectl -n bigdata describe pod "${POD:?Set POD from oc -n bigdata get pods}"
kubectl -n bigdata logs "${POD:?Set POD from oc -n bigdata get pods}" --tail=100
kubectl -n bigdata exec -it "${POD:?Set POD from oc -n bigdata get pods}" -- bash
```

The namespace selection differs slightly: `oc project bigdata` changes the active project, while portable `kubectl` commands commonly include `-n bigdata`.

## OpenShift-specific resources

```bash
oc project bigdata
oc get routes -n bigdata
oc get imagestreams -n bigdata
oc get securitycontextconstraints
oc auth can-i --list -n bigdata
oc get console.operator.openshift.io cluster -o jsonpath='{.status.consoleURL}{"\n"}'
```

## Resource and storage checks

```bash
crc config view
du -sh "$HOME/.crc" "$HOME/openshift"
df -h /
oc describe node | sed -n '/Capacity:/,/System Info:/p'
oc get storageclass
oc get pvc -A
oc adm top nodes
oc adm top pods -n bigdata --containers
```

Metrics may take a short time to become available after cluster startup. The host filesystem must have enough free space for both the CRC virtual disk and container image builds.

## Diagnose CRC access problems

If `crc status` reports that it cannot connect to the KVM driver, confirm group membership and query the CRC domain through system libvirt.

```bash
id
systemctl status libvirtd --no-pager
sudo virsh -c qemu:///system list --all
sudo virsh -c qemu:///system domstate crc
pgrep -af 'qemu-system.*crc' || echo 'No CRC QEMU process'
crc status
```

When the group list is correct but the current terminal still cannot access libvirt, sign out of the Linux login session and sign in again. If CRC is running but `oc` cannot connect, run `okd-env` and inspect the API address with `oc config view --minify`.
