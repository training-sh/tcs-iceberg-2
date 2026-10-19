# OpenShift / OKD `oc` Command Cheat Sheet

`oc` is the OpenShift command-line interface.

It supports standard Kubernetes resources and adds OpenShift-specific functionality such as Projects, Routes, Operators, Builds, ImageStreams, and administrative commands.

---

# 1. Verify `oc`

Check location:

```bash
which oc
```

Check version:

```bash
oc version
```

With CRC, configure `oc` using:

```bash
eval "$(crc oc-env)"
```

---

# 2. Login and User Information

Check current user:

```bash
oc whoami
```

Show API server:

```bash
oc whoami --show-server
```

Show OpenShift console URL:

```bash
oc whoami --show-console
```

Login:

```bash
oc login https://api.crc.testing:6443
```

Login as a specific user:

```bash
oc login https://api.crc.testing:6443 -u developer
```

Logout:

```bash
oc logout
```

For CRC credentials:

```bash
crc console --credentials
```

---

# 3. Cluster Information

Display cluster information:

```bash
oc cluster-info
```

List nodes:

```bash
oc get nodes
```

More details:

```bash
oc get nodes -o wide
```

Describe a node:

```bash
oc describe node crc
```

---

# 4. Cluster Version

```bash
oc get clusterversion
```

Short form:

```bash
oc get clusterversion version
```

---

# 5. Cluster Operators

List OpenShift cluster operators:

```bash
oc get clusteroperators
```

Short form:

```bash
oc get co
```

A healthy operator normally has:

```text
AVAILABLE   PROGRESSING   DEGRADED
True        False         False
```

Check control-plane operators:

```bash
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

Check API server:

```bash
oc get co kube-apiserver
```

Check etcd:

```bash
oc get co etcd
```

Check authentication:

```bash
oc get co authentication
```

Check console:

```bash
oc get co console
```

Check monitoring:

```bash
oc get co monitoring
```

Describe an operator:

```bash
oc describe co kube-apiserver
```

---

# 6. Projects and Namespaces

OpenShift commonly uses **Projects**.

A Project is based on a Kubernetes Namespace.

List projects:

```bash
oc get projects
```

or:

```bash
oc projects
```

Show current project:

```bash
oc project
```

Create project:

```bash
oc new-project training
```

Switch project:

```bash
oc project training
```

List namespaces:

```bash
oc get namespaces
```

Short form:

```bash
oc get ns
```

Create namespace:

```bash
oc create namespace bigdata
```

Delete project:

```bash
oc delete project training
```

---

# 7. Pods

List pods:

```bash
oc get pods
```

Short form:

```bash
oc get po
```

Detailed listing:

```bash
oc get pods -o wide
```

All namespaces:

```bash
oc get pods -A
```

Watch pod changes:

```bash
oc get pods -w
```

Describe pod:

```bash
oc describe pod <pod-name>
```

Example:

```bash
oc describe pod spark-master
```

Delete pod:

```bash
oc delete pod <pod-name>
```

If the pod belongs to a Deployment, StatefulSet, or another controller, Kubernetes normally creates a replacement.

---

# 8. Pod Logs

Display logs:

```bash
oc logs <pod-name>
```

Follow logs:

```bash
oc logs -f <pod-name>
```

Logs from a particular container:

```bash
oc logs <pod-name> -c <container-name>
```

Previous container logs after a restart:

```bash
oc logs <pod-name> --previous
```

---

# 9. Execute Commands Inside Pods

Run a command:

```bash
oc exec <pod-name> -- <command>
```

Example:

```bash
oc exec spark-master -- hostname
```

Interactive Bash shell:

```bash
oc exec -it <pod-name> -- /bin/bash
```

If Bash is unavailable:

```bash
oc exec -it <pod-name> -- /bin/sh
```

---

# 10. Deployments

List deployments:

```bash
oc get deployments
```

Short form:

```bash
oc get deploy
```

Describe deployment:

```bash
oc describe deployment <deployment-name>
```

Scale deployment:

```bash
oc scale deployment <deployment-name> --replicas=3
```

Restart deployment:

```bash
oc rollout restart deployment/<deployment-name>
```

Check rollout:

```bash
oc rollout status deployment/<deployment-name>
```

Rollout history:

```bash
oc rollout history deployment/<deployment-name>
```

Delete deployment:

```bash
oc delete deployment <deployment-name>
```

---

# 11. StatefulSets

List StatefulSets:

```bash
oc get statefulsets
```

Short form:

```bash
oc get sts
```

Describe:

```bash
oc describe sts <name>
```

Scale:

```bash
oc scale sts <name> --replicas=3
```

---

# 12. DaemonSets

List DaemonSets:

```bash
oc get daemonsets
```

Short form:

```bash
oc get ds
```

Describe:

```bash
oc describe ds <name>
```

---

# 13. Services

List services:

```bash
oc get services
```

Short form:

```bash
oc get svc
```

Detailed listing:

```bash
oc get svc -o wide
```

Describe service:

```bash
oc describe svc <service-name>
```

Delete service:

```bash
oc delete svc <service-name>
```

---

# 14. OpenShift Routes

A **Route** is an OpenShift resource used to expose a service outside the cluster.

List routes:

```bash
oc get routes
```

or:

```bash
oc get route
```

Expose a service:

```bash
oc expose service <service-name>
```

Example:

```bash
oc expose service spark-master
```

Get route URL:

```bash
oc get route
```

Describe route:

```bash
oc describe route <route-name>
```

Delete route:

```bash
oc delete route <route-name>
```

---

# 15. Port Forwarding

Forward a local port to a service:

```bash
oc port-forward svc/<service-name> <local-port>:<service-port>
```

Example:

```bash
oc port-forward svc/spark-master 8080:8080
```

Access from the host:

```text
http://localhost:8080
```

Trino example:

```bash
oc port-forward svc/trino 8081:8080
```

Pod port forwarding:

```bash
oc port-forward pod/<pod-name> 8080:8080
```

---

# 16. Apply YAML

Create or update resources:

```bash
oc apply -f deployment.yaml
```

Apply all YAML files from a directory:

```bash
oc apply -f .
```

Delete resources defined in YAML:

```bash
oc delete -f deployment.yaml
```

---

# 17. View Resource YAML

Deployment:

```bash
oc get deployment <name> -o yaml
```

Pod:

```bash
oc get pod <name> -o yaml
```

Service:

```bash
oc get svc <name> -o yaml
```

---

# 18. Edit Resources

Edit deployment:

```bash
oc edit deployment <name>
```

Edit service:

```bash
oc edit svc <name>
```

Edit ConfigMap:

```bash
oc edit cm <name>
```

---

# 19. ConfigMaps

List ConfigMaps:

```bash
oc get configmaps
```

Short form:

```bash
oc get cm
```

Create ConfigMap:

```bash
oc create configmap app-config \
  --from-literal=HOST=mysql \
  --from-literal=PORT=3306
```

Create from file:

```bash
oc create configmap app-config --from-file=application.conf
```

Describe:

```bash
oc describe cm app-config
```

Display YAML:

```bash
oc get cm app-config -o yaml
```

Delete:

```bash
oc delete cm app-config
```

---

# 20. Secrets

List secrets:

```bash
oc get secrets
```

Create secret:

```bash
oc create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=mypassword
```

Describe:

```bash
oc describe secret db-secret
```

Display secret YAML:

```bash
oc get secret db-secret -o yaml
```

Secret values in Kubernetes are normally Base64 encoded in the resource representation.

---

# 21. Persistent Storage

List Persistent Volumes:

```bash
oc get pv
```

List Persistent Volume Claims:

```bash
oc get pvc
```

Describe PVC:

```bash
oc describe pvc <pvc-name>
```

List StorageClasses:

```bash
oc get storageclass
```

Short form:

```bash
oc get sc
```

---

# 22. Events

Current namespace:

```bash
oc get events
```

Sort by creation time:

```bash
oc get events --sort-by=.metadata.creationTimestamp
```

All namespaces:

```bash
oc get events -A
```

Sorted:

```bash
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

# 23. Resource Usage

If cluster metrics are available:

```bash
oc adm top nodes
```

Pod usage:

```bash
oc adm top pods
```

All namespaces:

```bash
oc adm top pods -A
```

---

# 24. Get All Common Resources

Current project:

```bash
oc get all
```

Selected resources:

```bash
oc get pods,svc,deploy,route
```

All pods across the cluster:

```bash
oc get pods -A
```

---

# 25. API Resources

List resource types supported by the cluster:

```bash
oc api-resources
```

Find Route resources:

```bash
oc api-resources | grep -i route
```

Find OpenShift resources:

```bash
oc api-resources | grep openshift
```

---

# 26. Output Formats

Wide output:

```bash
oc get pods -o wide
```

YAML:

```bash
oc get pod <pod-name> -o yaml
```

JSON:

```bash
oc get pod <pod-name> -o json
```

Only resource names:

```bash
oc get pods -o name
```

---

# 27. Labels

Show labels:

```bash
oc get pods --show-labels
```

Add label:

```bash
oc label pod <pod-name> environment=training
```

Remove label:

```bash
oc label pod <pod-name> environment-
```

Select resources using a label:

```bash
oc get pods -l environment=training
```

---

# 28. Authentication and Authorization

Current user:

```bash
oc whoami
```

Check whether the user can create pods:

```bash
oc auth can-i create pods
```

Check whether the user can delete pods:

```bash
oc auth can-i delete pods
```

Check permission in a namespace:

```bash
oc auth can-i create pods -n training
```

Display permissions:

```bash
oc auth can-i --list
```

---

# 29. Service Accounts

List service accounts:

```bash
oc get serviceaccounts
```

Short form:

```bash
oc get sa
```

Describe:

```bash
oc describe sa <service-account>
```

---

# 30. Roles and RBAC

List Roles:

```bash
oc get roles
```

List RoleBindings:

```bash
oc get rolebindings
```

List ClusterRoles:

```bash
oc get clusterroles
```

List ClusterRoleBindings:

```bash
oc get clusterrolebindings
```

Check a user's permissions:

```bash
oc auth can-i --list
```

---

# 31. OpenShift Control Plane Health

Check nodes:

```bash
oc get nodes
```

Expected CRC example:

```text
NAME   STATUS   ROLES
crc    Ready    control-plane,master,worker
```

Check operators:

```bash
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
oc get co \
  kube-apiserver \
  kube-controller-manager \
  kube-scheduler \
  etcd
```

---

# 32. Troubleshooting a Pod

Start with:

```bash
oc get pods
```

If a pod is failing:

```bash
oc describe pod <pod-name>
```

Then check logs:

```bash
oc logs <pod-name>
```

For multiple containers:

```bash
oc logs <pod-name> -c <container-name>
```

Previous crash:

```bash
oc logs <pod-name> --previous
```

Check events:

```bash
oc get events --sort-by=.metadata.creationTimestamp
```

Check resource usage:

```bash
oc adm top pods
```

---

# 33. Common Pod Failure States

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
oc get pods -o wide
oc describe pod <pod-name>
oc logs <pod-name>
oc get events --sort-by=.metadata.creationTimestamp
```

---

# 34. Big Data Workload Examples

For Spark:

```bash
oc get pods | grep spark
```

```bash
oc get svc | grep spark
```

```bash
oc logs <spark-pod>
```

For Trino:

```bash
oc get pods | grep trino
```

```bash
oc logs <trino-pod>
```

For Polaris:

```bash
oc get pods | grep polaris
```

```bash
oc logs <polaris-pod>
```

For Airflow:

```bash
oc get pods | grep airflow
```

```bash
oc logs <airflow-pod>
```

For PostgreSQL:

```bash
oc get pods | grep postgres
```

For MySQL:

```bash
oc get pods | grep mysql
```

For SeaweedFS:

```bash
oc get pods | grep seaweed
```

---

# 35. Quick Cluster Health Check

Run:

```bash
oc whoami
oc get nodes
oc get clusterversion
oc get co
oc get pods -A
```

Check control plane:

```bash
oc get co kube-apiserver kube-controller-manager kube-scheduler etcd
```

Check recent events:

```bash
oc get events -A --sort-by=.metadata.creationTimestamp
```

---

# 36. Most Important Commands for Administrators

```bash
oc get
oc describe
oc logs
oc exec
oc get events
oc get nodes
oc get co
oc get pods -A
oc get svc
oc get route
oc get pvc
oc get cm
oc get secrets
oc auth can-i
oc adm top
```

These commands cover a large part of everyday OpenShift workload monitoring and troubleshooting.

---

# 37. `oc` vs `kubectl`

Most standard Kubernetes commands work using `oc`.

Kubernetes:

```bash
kubectl get pods
kubectl get nodes
kubectl apply -f app.yaml
kubectl logs mypod
```

OpenShift:

```bash
oc get pods
oc get nodes
oc apply -f app.yaml
oc logs mypod
```

`oc` additionally understands OpenShift-specific resources and commands.

Examples:

```bash
oc get routes
oc get projects
oc get clusteroperators
oc adm top nodes
```

For an OpenShift/OKD environment, using `oc` as the main CLI is normally convenient.

---

# 38. Useful Short Resource Names

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
| Route | `routes` | — |

Examples:

```bash
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

# 39. Daily Admin Quick Reference

```bash
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
oc describe pod <pod-name>

# Pod logs
oc logs <pod-name>

# Enter container
oc exec -it <pod-name> -- /bin/bash

# Resource usage
oc adm top nodes
oc adm top pods
```

---

# 40. Basic Troubleshooting Flow

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
