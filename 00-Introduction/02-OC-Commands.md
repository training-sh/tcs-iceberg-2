# 02 - OpenShift / OKD oc commands

> **DO NOT DELETE lab resources.** All deletion examples are reference only. Do not uncomment or run them during this course.

Deletion, cleanup, and reset command lines are **commented out with `#` to avoid accidental execution**. In Bash, a line beginning with `#` is a comment and is not executed when pasted into the terminal. Keep these lines commented; do not remove the `#`.

Run selected Bash blocks in the **Linux VM terminal**, not in a Python notebook. This is a command reference, not a script to execute from top to bottom. Complete [installation](00-Installation.md) and the [three Bash validations](../00-bashrc.md) first. Cluster commands require a running cluster and a valid login; cluster-wide listings may require administrator access.

Start with:

```bash
# Start CRC and load the course administrator kubeconfig and bigdata project.
okd-start
# Confirm the current identity and project before changing resources.
oc whoami
oc project
```

For examples with variables, first list real resources, then set only the variables you need:

```bash
# Inspect names in the current project; generated Deployment pod suffixes vary.
oc get pods,deployments,statefulsets,services,routes,pvc
# Course Spark pod/container names; verify they exist in your deployment.
POD=spark-master-0
CONTAINER=spark-master
SERVICE=spark-master
# For other resources, set DEPLOYMENT, STATEFULSET, DAEMONSET, ROUTE,
# PVC, SERVICE_ACCOUNT, and RESOURCE to names from the matching oc get listing.
# Guarded variables below stop Bash with a message if you have not set a name.
```

`oc` is the OpenShift command-line interface.

It supports standard Kubernetes resources and adds OpenShift-specific functionality such as Projects, Routes, Operators, Builds, ImageStreams, and administrative commands.

---

## 1. Verify `oc`

Check location:

```bash
# Check location
command -v oc
```

Check version:

```bash
# Check version
oc version
```

With CRC, configure `oc` using:

```bash
# With CRC, configure oc using
eval "$(crc oc-env)"
```

---

## 2. Login and User Information

Login/logout update the active kubeconfig. The developer identity may lack cluster-admin permissions; use `okd-env` to reload the course administrator environment when needed.

Check current user:

```bash
# Check current user
oc whoami
```

Show API server:

```bash
# Show API server
oc whoami --show-server
```

Show OpenShift console URL:

```bash
# Show OpenShift console URL
oc whoami --show-console
```

Login:

```bash
# Login
oc login https://api.crc.testing:6443
```

Login as a specific user:

```bash
# Login as a specific user
oc login https://api.crc.testing:6443 -u developer
```

Logout:

```bash
# Logout
oc logout
```

For CRC credentials:

```bash
# For CRC credentials
crc console --credentials
```

---

## 3. Cluster Information

Display cluster information:

```bash
# Display cluster information
oc cluster-info
```

List nodes:

```bash
# List nodes
oc get nodes
```

More details:

```bash
# More details
oc get nodes -o wide
```

Describe a node:

```bash
# Describe a node
oc describe nodes
```

---

## 4. Cluster Version

```bash
#  4. Cluster Version
oc get clusterversion
```

Named cluster-version resource (not a short form):

```bash
# Named cluster-version resource (not a short form)
oc get clusterversion version
```

---

## 5. Cluster Operators

List OpenShift cluster operators:

```bash
# List OpenShift cluster operators
oc get clusteroperators
```

Short form:

```bash
# Short form
oc get co
```

A healthy operator normally has:

```text
AVAILABLE   PROGRESSING   DEGRADED
True        False         False
```

Check control-plane operators:

```bash
# Check control-plane operators
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

Check API server:

```bash
# Check API server
oc get co kube-apiserver
```

Check etcd:

```bash
# Check etcd
oc get co etcd
```

Check authentication:

```bash
# Check authentication
oc get co authentication
```

Check console:

```bash
# Check console
oc get co console
```

Check monitoring:

```bash
# Check monitoring
oc get co monitoring
```

Describe an operator:

```bash
# Describe an operator
oc describe co kube-apiserver
```

---

## 6. Projects and Namespaces

OpenShift commonly uses **Projects**.

A Project is based on a Kubernetes Namespace.

List projects:

```bash
# List projects
oc get projects
```

or:

```bash
# or
oc projects
```

Show current project:

```bash
# Show current project
oc project
```

Create project:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Create project
oc new-project training
```

Switch project:

```bash
# Switch project
oc project training
```

List namespaces:

```bash
# List namespaces
oc get namespaces
```

Short form:

```bash
# Short form
oc get ns
```

Create namespace:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Alternative to oc new-project for a NEW namespace; skip if bigdata exists.
oc create namespace bigdata
```

Delete project:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete project
# oc delete project training
```

---

## 7. Pods

List pods:

```bash
# List pods
oc get pods
```

Short form:

```bash
# Short form
oc get po
```

Detailed listing:

```bash
# Detailed listing
oc get pods -o wide
```

All namespaces:

```bash
# All namespaces
oc get pods -A
```

Watch pod changes:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Watch pod changes
oc get pods -w
```

Describe pod:

```bash
# Describe pod
oc describe pod "${POD:?Set POD to an existing resource name}"
```

Example:

```bash
# Example
oc describe pod spark-master-0
```

Delete pod:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete pod
# oc delete pod "${POD:?Set POD to an existing resource name}"
```

If the pod belongs to a Deployment, StatefulSet, or another controller, Kubernetes normally creates a replacement.

---

## 8. Pod Logs

For multi-container pods, use `-c "$CONTAINER"` to select a container, or `--all-containers=true` to inspect them all. `--previous` requires a previous instance of the selected container.

Display logs:

```bash
# Display logs
oc logs "${POD:?Set POD to an existing resource name}" --all-containers=true --tail=100
```

Follow logs:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Follow logs
oc logs -f "${POD:?Set POD to an existing resource name}"
```

Logs from a particular container:

```bash
# Logs from a particular container
oc logs "${POD:?Set POD to an existing resource name}" -c "${CONTAINER:?Set CONTAINER to an existing resource name}"
```

Previous container logs after a restart:

```bash
# Previous container logs after a restart
oc logs "${POD:?Set POD to an existing resource name}" -c "${CONTAINER:?Set CONTAINER to an existing resource name}" --previous
```

---

## 9. Execute Commands Inside Pods

Run a command:

```bash
# Run a command
oc exec "${POD:?Set POD to an existing resource name}" -- hostname
```

Example:

```bash
# Example
oc exec spark-master-0 -c spark-master -- hostname
```

Interactive Bash shell:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Interactive Bash shell
oc exec -it "${POD:?Set POD to an existing resource name}" -- /bin/bash
```

If Bash is unavailable:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# If Bash is unavailable
oc exec -it "${POD:?Set POD to an existing resource name}" -- /bin/sh
```

---

## 10. Deployments

List deployments:

```bash
# List deployments
oc get deployments
```

Short form:

```bash
# Short form
oc get deploy
```

Describe deployment:

```bash
# Describe deployment
oc describe deployment "${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}"
```

Scale deployment:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Scale deployment
oc scale deployment "${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}" --replicas=3
```

Restart deployment:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Restart deployment
oc rollout restart deployment/"${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}"
```

Check rollout:

```bash
# Check rollout
oc rollout status deployment/"${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}" --timeout=5m
```

Rollout history:

```bash
# Rollout history
oc rollout history deployment/"${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}"
```

Delete deployment:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete deployment
# oc delete deployment "${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}"
```

---

## 11. StatefulSets

Scaling infrastructure StatefulSets can require application-specific configuration and storage. The single-node course uses one replica; do not treat extra replicas as a generic way to expand Hadoop or Spark.

List StatefulSets:

```bash
# List StatefulSets
oc get statefulsets
```

Short form:

```bash
# Short form
oc get sts
```

Describe:

```bash
# Describe
oc describe sts "${STATEFULSET:?Set STATEFULSET to an existing resource name}"
```

Scale:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Scale
oc scale sts "${STATEFULSET:?Set STATEFULSET to an existing resource name}" --replicas=1
```

---

## 12. DaemonSets

List DaemonSets:

```bash
# List DaemonSets
oc get daemonsets
```

Short form:

```bash
# Short form
oc get ds
```

Describe:

```bash
# Describe
oc describe ds "${DAEMONSET:?Set DAEMONSET to an existing resource name}"
```

---

## 13. Services

List services:

```bash
# List services
oc get services
```

Short form:

```bash
# Short form
oc get svc
```

Detailed listing:

```bash
# Detailed listing
oc get svc -o wide
```

Describe service:

```bash
# Describe service
oc describe svc "${SERVICE:?Set SERVICE to an existing resource name}"
```

Delete service:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete service
# oc delete svc "${SERVICE:?Set SERVICE to an existing resource name}"
```

---

## 14. OpenShift Routes

A **Route** exposes an HTTP(S) service outside the cluster. For a multi-port Service, select the intended port explicitly with `--port`; a Route is not generic TCP forwarding. The Spark example exposes port 8080; it requires that Service port and an unused Route name.

List routes:

```bash
# List routes
oc get routes
```

or:

```bash
# or
oc get route
```

Expose a service:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Expose a service
oc expose service "${SERVICE:?Set SERVICE to an existing resource name}"
```

Example:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Example
oc expose service spark-master --name=spark-ui-example --port=8080
```

Get route URL:

```bash
# Get route URL
oc get route
```

Describe route:

```bash
# Describe route
oc describe route "${ROUTE:?Set ROUTE to an existing resource name}"
```

Delete route:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete route
# oc delete route "${ROUTE:?Set ROUTE to an existing resource name}"
```

---

## 15. Port Forwarding

Forward a local port to a service:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Forward a local port to a service
oc port-forward svc/"${SERVICE:?Set SERVICE to an existing resource name}" 8080:8080
```

Example:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Example
oc port-forward --address=127.0.0.1 svc/spark-master 8080:8080
```

Keep port-forward running; press Ctrl+C to stop it. Open the URL on the Linux VM. From another computer, use an SSH tunnel to the VM. Access from the VM:

```text
http://localhost:8080
```

Trino example:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Trino example
oc port-forward --address=127.0.0.1 svc/trino 8081:8080
```

Pod port forwarding:

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Pod port forwarding
oc port-forward pod/"${POD:?Set POD to an existing resource name}" 8080:8080
```

---

## 16. Apply YAML

Create or update resources:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Create or update resources
oc apply -f "${MANIFEST:?Set MANIFEST to an existing YAML file}"
```

Apply all YAML files from a directory:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Apply all YAML files from a directory
oc apply -f "${MANIFEST_DIR:?Set MANIFEST_DIR to the intended YAML directory}"
```

Delete resources defined in YAML:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete resources defined in YAML
# oc delete -f "${MANIFEST:?Set MANIFEST to an existing YAML file}"
```

---

## 17. View Resource YAML

Deployment:

```bash
# Deployment
oc get deployment "${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}" -o yaml
```

Pod:

```bash
# Pod
oc get pod "${RESOURCE:?Set RESOURCE to an existing resource name}" -o yaml
```

Service:

```bash
# Service
oc get svc "${SERVICE:?Set SERVICE to an existing resource name}" -o yaml
```

---

## 18. Edit Resources

Edit deployment:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Edit deployment
oc edit deployment "${DEPLOYMENT:?Set DEPLOYMENT to an existing resource name}"
```

Edit service:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Edit service
oc edit svc "${SERVICE:?Set SERVICE to an existing resource name}"
```

Edit ConfigMap:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Edit ConfigMap
oc edit cm "${RESOURCE:?Set RESOURCE to an existing resource name}"
```

---

## 19. ConfigMaps

List ConfigMaps:

```bash
# List ConfigMaps
oc get configmaps
```

Short form:

```bash
# Short form
oc get cm
```

Create ConfigMap:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Create ConfigMap
oc create configmap app-config \
  --from-literal=HOST=mysql \
  --from-literal=PORT=3306
```

Create from file:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Create from file
oc create configmap app-file-config --from-file="${CONFIG_FILE:?Set CONFIG_FILE to an existing file}"
```

Describe:

```bash
# Describe
oc describe cm app-config
```

Display YAML:

```bash
# Display YAML
oc get cm app-config -o yaml
```

Delete:

> **DO NOT RUN: DO NOT DELETE lab resources.** Reference only.

```bash
# DO NOT RUN OR UNCOMMENT the deletion command below.
# CHANGES RESOURCES: check oc project and the target name before running.
# Delete
# oc delete cm app-config
```

---

## 20. Secrets

List secrets:

```bash
# List secrets
oc get secrets
```

Create secret:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Create secret
oc create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=mypassword
```

Describe:

```bash
# Describe
oc describe secret db-secret
```

Display secret YAML:

```bash
# Display secret YAML
oc get secret db-secret -o yaml
```

Secret values in Kubernetes are normally Base64 encoded in the resource representation.

---

## 21. Persistent Storage

List Persistent Volumes:

```bash
# List Persistent Volumes
oc get pv
```

List Persistent Volume Claims:

```bash
# List Persistent Volume Claims
oc get pvc
```

Describe PVC:

```bash
# Describe PVC
oc describe pvc "${PVC:?Set PVC to an existing resource name}"
```

List StorageClasses:

```bash
# List StorageClasses
oc get storageclass
```

Short form:

```bash
# Short form
oc get sc
```

---

## 22. Events

Current namespace:

```bash
# Current namespace
oc get events
```

Sort by creation time:

```bash
# Sort by creation time
oc get events --sort-by=.metadata.creationTimestamp
```

All namespaces:

```bash
# All namespaces
oc get events -A
```

Sorted:

```bash
# Sorted
oc get events -A --sort-by=.metadata.creationTimestamp
```

Events are extremely useful when troubleshooting:

```text
Pending
CrashLoopBackOff
ImagePullBackOff
Mount failures
Scheduling failures
Readiness failures
```

---

## 23. Resource Usage

If cluster metrics are available:

```bash
# If cluster metrics are available
oc adm top nodes
```

Pod usage:

```bash
# Pod usage
oc adm top pods
```

All namespaces:

```bash
# All namespaces
oc adm top pods -A
```

---

## 24. Get All Common Resources

Current project:

```bash
# Current project
oc get all
# The all category omits resources such as PVCs, ConfigMaps, and Secrets.
oc get pvc,configmaps,secrets
```

Selected resources:

```bash
# Selected resources
oc get pods,svc,deploy,route
```

All pods across the cluster:

```bash
# All pods across the cluster
oc get pods -A
```

---

## 25. API Resources

List resource types supported by the cluster:

```bash
# List resource types supported by the cluster
oc api-resources
```

Find Route resources:

```bash
# Find Route resources
oc api-resources | grep -i route
```

Find OpenShift resources:

```bash
# Find OpenShift resources
oc api-resources | grep openshift
```

---

## 26. Output Formats

Wide output:

```bash
# Wide output
oc get pods -o wide
```

YAML:

```bash
# YAML
oc get pod "${POD:?Set POD to an existing resource name}" -o yaml
```

JSON:

```bash
# JSON
oc get pod "${POD:?Set POD to an existing resource name}" -o json
```

Only resource names:

```bash
# Only resource names
oc get pods -o name
```

---

## 27. Labels

Show labels:

```bash
# Show labels
oc get pods --show-labels
```

Add label:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Add label
oc label pod "${POD:?Set POD to an existing resource name}" environment=training
```

Remove label:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# Remove label
oc label pod "${POD:?Set POD to an existing resource name}" environment-
```

Select resources using a label:

```bash
# Select resources using a label
oc get pods -l environment=training
```

---

## 28. Authentication and Authorization

Current user:

```bash
# Current user
oc whoami
```

Check whether the user can create pods:

```bash
# Check whether the user can create pods
oc auth can-i create pods
```

Check whether the user can delete pods:

```bash
# Check whether the user can delete pods
# Permission check only; this does not delete anything.
oc auth can-i delete pods
```

Check permission in a namespace:

```bash
# Check permission in a namespace
oc auth can-i create pods -n training
```

Display permissions:

```bash
# Display permissions
oc auth can-i --list
```

---

## 29. Service Accounts

List service accounts:

```bash
# List service accounts
oc get serviceaccounts
```

Short form:

```bash
# Short form
oc get sa
```

Describe:

```bash
# Describe
oc describe sa "${SERVICE_ACCOUNT:?Set SERVICE_ACCOUNT to an existing resource name}"
```

---

## 30. Roles and RBAC

List Roles:

```bash
# List Roles
oc get roles
```

List RoleBindings:

```bash
# List RoleBindings
oc get rolebindings
```

List ClusterRoles:

```bash
# List ClusterRoles
oc get clusterroles
```

List ClusterRoleBindings:

```bash
# List ClusterRoleBindings
oc get clusterrolebindings
```

Check a user's permissions:

```bash
# Check a user's permissions
oc auth can-i --list
```

---

## 31. OpenShift Control Plane Health

Check nodes:

```bash
# Check nodes
oc get nodes
```

Expected CRC example:

```text
NAME   STATUS   ROLES
crc    Ready    control-plane,master,worker
```

Check operators:

```bash
# Check operators
oc get co
```

Healthy state:

```text
AVAILABLE=True
PROGRESSING=False
DEGRADED=False
```

Check critical control-plane operators:

```bash
# Check critical control-plane operators
oc get co \
  kube-apiserver \
  kube-controller-manager \
  kube-scheduler \
  etcd
```

---

## 32. Troubleshooting a Pod

Start with:

```bash
# Start with
oc get pods
```

If a pod is failing:

```bash
# If a pod is failing
oc describe pod "${POD:?Set POD to an existing resource name}"
```

Then check logs:

```bash
# Then check logs
oc logs "${POD:?Set POD to an existing resource name}" --all-containers=true --tail=100
```

For multiple containers:

```bash
# For multiple containers
oc logs "${POD:?Set POD to an existing resource name}" -c "${CONTAINER:?Set CONTAINER to an existing resource name}"
```

Previous crash:

```bash
# Previous crash
oc logs "${POD:?Set POD to an existing resource name}" -c "${CONTAINER:?Set CONTAINER to an existing resource name}" --previous
```

Check events:

```bash
# Check events
oc get events --sort-by=.metadata.creationTimestamp
```

Check resource usage:

```bash
# Check resource usage
oc adm top pods
```

---

## 33. Common Pod Failure States

Common statuses include:

```text
Pending
CrashLoopBackOff
ImagePullBackOff
ErrImagePull
Error
Completed
ContainerCreating
Terminating
```

Useful investigation sequence:

```bash
# Useful investigation sequence
oc get pods -o wide
oc describe pod "${POD:?Set POD to an existing resource name}"
oc logs "${POD:?Set POD to an existing resource name}" --all-containers=true --tail=100
oc get events --sort-by=.metadata.creationTimestamp
```

---

## 34. Big Data Workload Examples

For Spark:

```bash
# For Spark
oc get pods | grep spark
```

```bash
# 34. Big Data Workload Examples
oc get svc | grep spark
```

```bash
# 34. Big Data Workload Examples
oc logs "${POD:?Set POD to an existing resource name}"
```

For Trino:

```bash
# For Trino
oc get pods | grep trino
```

```bash
# 34. Big Data Workload Examples
oc logs "${POD:?Set POD to an existing resource name}"
```

For Polaris:

```bash
# For Polaris
oc get pods | grep polaris
```

```bash
# 34. Big Data Workload Examples
oc logs "${POD:?Set POD to an existing resource name}"
```

For Airflow:

```bash
# For Airflow
oc get pods | grep airflow
```

```bash
# 34. Big Data Workload Examples
oc logs "${POD:?Set POD to an existing resource name}"
```

For PostgreSQL:

```bash
# For PostgreSQL
oc get pods | grep postgres
```

For MySQL:

```bash
# For MySQL
oc get pods | grep mysql
```

For SeaweedFS:

```bash
# For SeaweedFS
oc get pods | grep seaweed
```

---

## 35. Quick Cluster Health Check

Run:

```bash
# Run
oc whoami
oc get nodes
oc get clusterversion
oc get co
oc get pods -A
```

Check control plane:

```bash
# Check control plane
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

Check recent events:

```bash
# Check recent events
oc get events -A --sort-by=.metadata.creationTimestamp
```

---

## 36. Most important commands for administrators

```bash
# Complete examples: inspect resources before making changes.
oc get pods
oc describe pod "${POD:?Set POD from oc get pods}"
oc logs "${POD:?Set POD}" --all-containers=true --tail=100
oc exec "${POD:?Set POD}" -c "${CONTAINER:?Set CONTAINER}" -- hostname
oc get events --sort-by=.metadata.creationTimestamp
oc get nodes
oc get co
oc get pods -A
oc get svc,route,pvc,cm,secrets
oc auth can-i get pods
oc adm top pods
```

---

## 37. `oc` vs `kubectl`

Most standard Kubernetes commands work using `oc`.

Kubernetes:

```bash
# Kubernetes
kubectl get pods
kubectl get nodes
kubectl apply -f "${MANIFEST:?Set MANIFEST to an existing YAML file}"
kubectl logs "${POD:?Set POD}" --all-containers=true --tail=100
```

OpenShift:

```bash
# CHANGES RESOURCES: check oc project and the target name before running.
# OpenShift
oc get pods
oc get nodes
oc apply -f "${MANIFEST:?Set MANIFEST to an existing YAML file}"
oc logs "${POD:?Set POD}" --all-containers=true --tail=100
```

`oc` additionally understands OpenShift-specific resources and commands.

Examples:

```bash
# Examples
oc get routes
oc get projects
oc get clusteroperators
oc adm top nodes
```

For an OpenShift/OKD environment, using `oc` as the main CLI is normally convenient.

---

## 38. Useful Short Resource Names

| Resource | Full Name | Short Name |
|---|---|---|
| Pod | `pods` | `po` |
| Service | `services` | `svc` |
| Deployment | `deployments` | `deploy` |
| StatefulSet | `statefulsets` | `sts` |
| DaemonSet | `daemonsets` | `ds` |
| Namespace | `namespaces` | `ns` |
| ConfigMap | `configmaps` | `cm` |
| PersistentVolume | `persistentvolumes` | `pv` |
| PersistentVolumeClaim | `persistentvolumeclaims` | `pvc` |
| StorageClass | `storageclasses` | `sc` |
| ServiceAccount | `serviceaccounts` | `sa` |
| ClusterOperator | `clusteroperators` | `co` |
| Route | `routes` | â€” |

Examples:

```bash
# Examples
oc get po
oc get svc
oc get deploy
oc get sts
oc get ns
oc get cm
oc get pvc
oc get sc
oc get co
```

---

## 39. Daily Admin Quick Reference

```bash
# Interactive/long-running command: Ctrl+C stops a watch/forward; exit leaves a pod shell.
# Who am I?
oc whoami

# Node health
oc get nodes

# OpenShift health
oc get co

# All pods
oc get pods -A

# Current project
oc project

# Services
oc get svc

# Routes
oc get route

# Storage
oc get pvc

# Recent events
oc get events --sort-by=.metadata.creationTimestamp

# Pod details
oc describe pod "${POD:?Set POD to an existing resource name}"

# Pod logs
oc logs "${POD:?Set POD to an existing resource name}" --all-containers=true --tail=100

# Enter container
oc exec -it "${POD:?Set POD to an existing resource name}" -- /bin/bash

# Resource usage
oc adm top nodes
oc adm top pods
```

---

## 40. Basic Troubleshooting Flow

When an application is not working:

```text
1. Node
   |
   +-- oc get nodes

2. Operators
   |
   +-- oc get co

3. Pods
   |
   +-- oc get pods -o wide

4. Pod Details
   |
   +-- oc describe pod <pod>

5. Logs
   |
   +-- oc logs <pod>

6. Events
   |
   +-- oc get events

7. Service
   |
   +-- oc get svc

8. Route
   |
   +-- oc get route

9. Storage
   |
   +-- oc get pvc

10. CPU / Memory
    |
    +-- oc adm top pods
```

For OpenShift administrators, **`get -> describe -> logs -> events`** is one of the most useful troubleshooting patterns to remember.

Reference: [OpenShift CLI command reference](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/cli_tools/openshift-cli-oc). Check `oc COMMAND --help` for the client installed with your CRC bundle.
