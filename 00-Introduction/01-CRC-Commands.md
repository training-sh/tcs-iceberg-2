# 01 - CRC lifecycle commands

> **DO NOT DELETE lab resources or run cleanup/reset commands.** Deletion examples below are reference only and are commented out. Do not uncomment or run them during this course.

Deletion, cleanup, and reset command lines are **commented out with `#` to avoid accidental execution**. In Bash, a line beginning with `#` is a comment and is not executed when pasted into the terminal. Keep these lines commented; do not remove the `#`.

Run selected Bash blocks in the **Linux VM terminal**, not in a Python notebook. This is a command reference, not a script to execute from top to bottom. Complete [installation](00-Installation.md) and the [three Bash validations](../00-bashrc.md) first. Cluster commands require a running cluster and a valid login; cluster-wide listings may require administrator access.

CRC provides a local single-node OpenShift/OKD cluster for development, testing, demonstrations, and training.

---

## 1. Check CRC Installation

Check where CRC is installed:

```bash
# Check where CRC is installed
command -v crc
```

Check CRC version:

```bash
# Check CRC version
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
# Display available commands
crc help
```

Help for a specific command:

```bash
# Help for a specific command
crc help start
```

or:

```bash
# or
crc start --help
```

---

## 3. CRC Setup

Before starting CRC for the first time:

```bash
# Before starting CRC for the first time
crc setup
```

This prepares the host system for running the CRC virtual machine.

---

## 4. Start CRC

Start the OpenShift/OKD cluster:

```bash
# Start the OpenShift/OKD cluster
crc start
```

CRC starts a local VM containing the OpenShift/OKD cluster.

---

## 5. Check CRC Status

```bash
#  5. Check CRC Status
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
#  6. Stop CRC
crc stop
```

This stops the CRC VM without deleting the cluster.

Start it again using:

```bash
# Start it again using
crc start
```

---

## 7. Restart CRC

CRC does not require a special restart command.

Use:

```bash
# Use
crc stop && crc start
```

---

## 8. Get CRC IP Address

```bash
#  8. Get CRC IP Address
crc ip
```

This displays the IP address used by the CRC virtual machine.

---

## 9. Open OpenShift Web Console

Open the console using the default browser:

```bash
# Open the console using the default browser
crc console
```

Display only the console URL:

```bash
# Display only the console URL
crc console --url
```

---

## 10. Get OpenShift Login Credentials

```bash
#  10. Get OpenShift Login Credentials
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
# Display the required environment configuration
crc oc-env
```

Example output:

```text
export PATH="/home/dev/.crc/bin/oc:$PATH"
```

Apply it to the current terminal:

```bash
# Apply it to the current terminal
eval "$(crc oc-env)"
```

Verify:

```bash
# Verify
command -v oc
```

Then:

```bash
# Then
oc version
```

---

## 12. Permanent PATH and cloned-VM session configuration

Use the [three `.bashrc` additions and validations](../00-bashrc.md#three-separate-additions-to-bashrc). They preserve existing PATH entries, add CRC and `oc`, and check the user runtime directory and D-Bus socket before `systemctl --user daemon-reload`. Do not append another unmarked PATH block.

```bash
# Check syntax before loading your existing shell configuration.
bash -n "$HOME/.bashrc" && source "$HOME/.bashrc"
command -v crc
command -v oc
```

---

## 13. View CRC Configuration

```bash
#  13. View CRC Configuration
crc config view
```

---

## 14. Configure CPU

Example:

```bash
# Example
crc config set cpus 4
```

Check:

```bash
# Check
crc config view
```

CPU changes may require recreating/restarting the CRC environment depending on the configuration and CRC version.

---

## 15. Configure Memory

Example: configure 16 GiB RAM (16384 MiB).

```bash
# Example: configure 16 GiB RAM (16384 MiB).
crc config set memory 16384
```

Check:

```bash
# Check
crc config view
```

---

## 16. Configure disk before initial cluster creation

```bash
# Use the course profile before the first start; this does not resize an existing disk.
crc config set disk-size 50
crc config view
crc config --help
```

---

## 17. Check Cluster After Starting CRC

First:

```bash
# First
crc status
```

Then configure `oc` if required:

```bash
# Then configure oc if required
eval "$(crc oc-env)"
```

Check the OpenShift node:

```bash
# Check the OpenShift node
oc get nodes
```

Example:

```text
NAME   STATUS   ROLES                         AGE   VERSION
crc    Ready    control-plane,master,worker   34d   <bundle-version>
```

A CRC cluster normally uses a **single node** for:

- Control Plane
- Master
- Worker

This is normal for CRC.

---

## 18. Check OpenShift Operators

```bash
#  18. Check OpenShift Operators
oc get clusteroperators
```

Short form:

```bash
# Short form
oc get co
```

A healthy operator normally shows:

```text
AVAILABLE   PROGRESSING   DEGRADED
True        False         False
```

Check important control-plane operators:

```bash
# Check important control-plane operators
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

---

## 19. Check OpenShift Version

```bash
#  19. Check OpenShift Version
oc get clusterversion
```

Named cluster-version resource:

```bash
# Named cluster-version resource
oc get clusterversion version
```

---

## 20. Check OpenShift API

```bash
#  20. Check OpenShift API
oc cluster-info
```

Check currently logged-in user:

```bash
# Check currently logged-in user
oc whoami
```

Check API server:

```bash
# Check API server
oc whoami --show-server
```

Check console URL:

```bash
# Check console URL
oc whoami --show-console
```

---

## 21. Delete CRC Cluster

> **DO NOT DELETE the CRC cluster.** This destroys the lab and its stored data.

> **DO NOT RUN: DO NOT DELETE.** This example removes lab resources, cluster data, or host configuration. Reference only.

```bash
# DO NOT RUN OR UNCOMMENT: deletion/cleanup is prohibited during the course.
#  WARNING: This destroys the local CRC cluster.
# crc delete
```

Applications, cluster configuration, and data on the CRC VM disk will be lost. This is not a restart command.

---

## 22. Clean CRC Environment

> **DO NOT RUN `crc cleanup`.** It removes the CRC instance and host setup; it is not a course troubleshooting step.

> **DO NOT RUN: DO NOT DELETE.** This example removes lab resources, cluster data, or host configuration. Reference only.

```bash
# DO NOT RUN OR UNCOMMENT: deletion/cleanup is prohibited during the course.
#  WARNING: Use this for cleanup/troubleshooting, not as a normal daily command.
# crc cleanup
```

After cleanup, setup may be required again:

```bash
# After cleanup, setup may be required again
crc setup
```

---

## 23. Recreate CRC Cluster

**DO NOT recreate or reset the course cluster.** The sequence below is disabled and retained only to explain the commands:

> **DO NOT RUN: DO NOT DELETE.** This example removes lab resources, cluster data, or host configuration. Reference only.

```bash
# DO NOT RUN OR UNCOMMENT: deletion/cleanup is prohibited during the course.
# When a completely fresh environment is required
# crc stop &&
# crc delete &&
# crc cleanup &&
# crc setup &&
# crc start
```

> This destroys the existing local cluster and its disk data.

---

## 24. Basic CRC Troubleshooting

Check status:

```bash
# Check status
crc status
```

Check configuration:

```bash
# Check configuration
crc config view
```

Check CRC version:

```bash
# Check CRC version
crc version
```

Check IP:

```bash
# Check IP
crc ip
```

Check OpenShift node:

```bash
# Check OpenShift node
oc get nodes
```

Check cluster operators:

```bash
# Check cluster operators
oc get co
```

Check pods:

```bash
# Check pods
oc get pods -A
```

Check recent events:

```bash
# Check recent events
oc get events -A --sort-by=.metadata.creationTimestamp
```

---

## 25. Daily CRC Commands

For normal training/lab usage, these are the most useful commands:

```bash
# Check CRC
crc status

# Start CRC
okd-start

# Configure oc (client PATH only; okd-start also loads the administrator kubeconfig)
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
# When finished
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
| Set CPUs | `crc config set cpus 4` |
| Set RAM | `crc config set memory 16384` |
| Delete cluster ? **DO NOT RUN** | `# crc delete` |
| Cleanup ? **DO NOT RUN** | `# crc cleanup` |

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

Sources: [CRC usage](https://crc.dev/docs/using/), [configuration](https://crc.dev/docs/configuring/), [troubleshooting](https://crc.dev/docs/troubleshooting/). Use `crc COMMAND --help` for the installed version.
