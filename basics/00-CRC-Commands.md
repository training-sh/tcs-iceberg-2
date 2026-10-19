# CRC (OpenShift Local / OKD) Command Cheat Sheet

CRC provides a local single-node OpenShift/OKD cluster for development, testing, demonstrations, and training.

---

## 1. Check CRC Installation

Check where CRC is installed:

```bash
which crc
```

Check CRC version:

```bash
crc version
```

Example installation path:

```text
/home/dev/.local/bin/crc
```

---

## 2. CRC Help

Display available commands:

```bash
crc help
```

Help for a specific command:

```bash
crc help start
```

or:

```bash
crc start --help
```

---

## 3. CRC Setup

Before starting CRC for the first time:

```bash
crc setup
```

This prepares the host system for running the CRC virtual machine.

---

## 4. Start CRC

Start the OpenShift/OKD cluster:

```bash
crc start
```

CRC starts a local VM containing the OpenShift/OKD cluster.

---

## 5. Check CRC Status

```bash
crc status
```

Typical information includes:

- CRC VM status
- OpenShift status
- RAM usage
- Disk usage

Example:

```text
CRC VM:          Running
OpenShift:       Running
RAM Usage:       ...
Disk Usage:      ...
```

---

## 6. Stop CRC

```bash
crc stop
```

This stops the CRC VM without deleting the cluster.

Start it again using:

```bash
crc start
```

---

## 7. Restart CRC

CRC does not require a special restart command.

Use:

```bash
crc stop
crc start
```

---

## 8. Get CRC IP Address

```bash
crc ip
```

This displays the IP address used by the CRC virtual machine.

---

## 9. Open OpenShift Web Console

Open the console using the default browser:

```bash
crc console
```

Display only the console URL:

```bash
crc console --url
```

---

## 10. Get OpenShift Login Credentials

```bash
crc console --credentials
```

This normally displays credentials for users such as:

```text
developer
kubeadmin
```

Use `developer` for normal application work.

Use `kubeadmin` when cluster administrator privileges are required.

---

## 11. Configure the `oc` CLI

CRC provides an OpenShift CLI binary.

Display the required environment configuration:

```bash
crc oc-env
```

Example output:

```bash
export PATH="/home/dev/.crc/bin/oc:$PATH"
```

Apply it to the current terminal:

```bash
eval "$(crc oc-env)"
```

Verify:

```bash
which oc
```

Then:

```bash
oc version
```

---

## 12. Permanent PATH Configuration

If CRC is installed at:

```text
/home/dev/.local/bin/crc
```

and `oc` is provided at:

```text
/home/dev/.crc/bin/oc/oc
```

add both directories to `~/.bashrc`:

```bash
cat <<'EOF' | tee -a ~/.bashrc

# CRC / OpenShift
export PATH="$HOME/.local/bin:$HOME/.crc/bin/oc:$PATH"
EOF
```

Reload the shell:

```bash
source ~/.bashrc
```

Verify:

```bash
which crc
which oc
```

---

## 13. View CRC Configuration

```bash
crc config view
```

---

## 14. Configure CPU

Example:

```bash
crc config set cpus 6
```

Check:

```bash
crc config view
```

CPU changes may require recreating/restarting the CRC environment depending on the configuration and CRC version.

---

## 15. Configure Memory

Example: configure approximately 24 GB RAM.

```bash
crc config set memory 24576
```

Check:

```bash
crc config view
```

---

## 16. Configure Disk Size

Check available CRC configuration options:

```bash
crc config
```

or:

```bash
crc config --help
```

Available disk configuration options can vary by CRC version.

---

## 17. Check Cluster After Starting CRC

First:

```bash
crc status
```

Then configure `oc` if required:

```bash
eval "$(crc oc-env)"
```

Check the OpenShift node:

```bash
oc get nodes
```

Example:

```text
NAME   STATUS   ROLES                         AGE   VERSION
crc    Ready    control-plane,master,worker   34d   v1.35.5
```

A CRC cluster normally uses a **single node** for:

- Control Plane
- Master
- Worker

This is normal for CRC.

---

## 18. Check OpenShift Operators

```bash
oc get clusteroperators
```

Short form:

```bash
oc get co
```

A healthy operator normally shows:

```text
AVAILABLE   PROGRESSING   DEGRADED
True        False         False
```

Check important control-plane operators:

```bash
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

---

## 19. Check OpenShift Version

```bash
oc get clusterversion
```

Short form:

```bash
oc get clusterversion version
```

---

## 20. Check OpenShift API

```bash
oc cluster-info
```

Check currently logged-in user:

```bash
oc whoami
```

Check API server:

```bash
oc whoami --show-server
```

Check console URL:

```bash
oc whoami --show-console
```

---

## 21. Delete CRC Cluster

> **WARNING:** This destroys the local CRC cluster.

```bash
crc delete
```

Applications and cluster configuration stored inside the CRC cluster will be lost.

---

## 22. Clean CRC Environment

> **WARNING:** Use this for cleanup/troubleshooting, not as a normal daily command.

```bash
crc cleanup
```

After cleanup, setup may be required again:

```bash
crc setup
```

---

## 23. Recreate CRC Cluster

When a completely fresh environment is required:

```bash
crc stop
crc delete
crc cleanup
crc setup
crc start
```

> This destroys the existing local cluster.

---

## 24. Basic CRC Troubleshooting

Check status:

```bash
crc status
```

Check configuration:

```bash
crc config view
```

Check CRC version:

```bash
crc version
```

Check IP:

```bash
crc ip
```

Check OpenShift node:

```bash
oc get nodes
```

Check cluster operators:

```bash
oc get co
```

Check pods:

```bash
oc get pods -A
```

Check recent events:

```bash
oc get events -A --sort-by=.metadata.creationTimestamp
```

---

## 25. Daily CRC Commands

For normal training/lab usage, these are the most useful commands:

```bash
# Check CRC
crc status

# Start CRC
crc start

# Configure oc
eval "$(crc oc-env)"

# Check OpenShift node
oc get nodes

# Check cluster health
oc get co

# Get console URL
crc console --url

# Get credentials
crc console --credentials
```

When finished:

```bash
crc stop
```

---

# CRC Quick Reference

| Task | Command |
|---|---|
| CRC version | `crc version` |
| Prepare host | `crc setup` |
| Start cluster | `crc start` |
| Stop cluster | `crc stop` |
| Cluster status | `crc status` |
| CRC IP | `crc ip` |
| Open console | `crc console` |
| Console URL | `crc console --url` |
| Credentials | `crc console --credentials` |
| Configure OC | `eval "$(crc oc-env)"` |
| View config | `crc config view` |
| Set CPUs | `crc config set cpus 6` |
| Set RAM | `crc config set memory 24576` |
| Delete cluster | `crc delete` |
| Cleanup | `crc cleanup` |

---

# CRC Architecture

A typical local CRC environment looks like:

```text
Linux Host
   |
   +-- CRC
       |
       +-- CRC Virtual Machine
           |
           +-- OKD / OpenShift
               |
               +-- Control Plane
               +-- Kubernetes API
               +-- OpenShift Operators
               +-- Worker
               +-- Pods
               +-- Services
               +-- Routes
```

CRC normally creates a **single-node cluster**, so the same node can have:

```text
control-plane
master
worker
```

roles.

CRC manages the local cluster lifecycle, while `oc` is used to manage resources **inside OpenShift/OKD**.
