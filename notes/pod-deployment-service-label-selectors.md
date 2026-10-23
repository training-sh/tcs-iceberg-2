# Kubernetes Pod, Deployment, Service Names, Labels and Selectors

## 1. Key Concept

Kubernetes connects objects mainly through **Labels and Selectors**.

> **Service `selector` → matches Pod `labels`.**

The Service name and Pod name **do not need to match**.

---

## 2. Example: Deployment and Service

```yaml
# ============================================
# DEPLOYMENT
# ============================================

apiVersion: apps/v1
kind: Deployment

metadata:
  name: nginx-deployment          # <-- DEPLOYMENT NAME

spec:
  replicas: 2

  selector:
    matchLabels:
      app: nginx                  # <-- Must match Pod label

  template:
    metadata:
      labels:
        app: nginx                # <-- POD LABEL ★ IMPORTANT

    spec:
      containers:
        - name: nginx-container   # <-- CONTAINER NAME
          image: nginx:latest

          ports:
            - containerPort: 80

---
# ============================================
# SERVICE
# ============================================

apiVersion: v1
kind: Service

metadata:
  name: nginx-service             # <-- SERVICE NAME

spec:
  selector:
    app: nginx                    # <-- ★ Must match Pod label: app: nginx

  ports:
    - port: 80
      targetPort: 80

  type: ClusterIP
```

---

# 3. Important Names

| Object | Name / Value | Where Defined |
|---|---|---|
| Deployment | `nginx-deployment` | `metadata.name` |
| Container | `nginx-container` | `containers[].name` |
| Pod | Generated automatically | Created by Deployment |
| Pod Label | `app: nginx` | `template.metadata.labels` |
| Service | `nginx-service` | Service `metadata.name` |
| Service Selector | `app: nginx` | Service `spec.selector` |

---

# 4. How Deployment Creates Pods

The Deployment is named:

```yaml
metadata:
  name: nginx-deployment
```

The Deployment creates a ReplicaSet.

The ReplicaSet then creates the Pods.

For example:

```bash
kubectl get pods
```

Output may look like:

```text
NAME                                READY
nginx-deployment-7c79c4bf97-x8k2m   1/1
nginx-deployment-7c79c4bf97-z9p4q   1/1
```

The Pod name is generated approximately as:

```text
Deployment Name
       +
ReplicaSet Hash
       +
Unique Pod Suffix
```

Example:

```text
nginx-deployment-7c79c4bf97-x8k2m
^^^^^^^^^^^^^^^^  ^^^^^^^^^^ ^^^^^
Deployment         RS Hash   Pod
                              Suffix
```

Normally, when using a Deployment, we **do not manually specify the final Pod name**.

---

# 5. How Does the Service Find the Pods?

This is the most important relationship.

The Deployment creates Pods containing this label:

```yaml
template:
  metadata:
    labels:
      app: nginx
```

Therefore the Pods have:

```text
app=nginx
```

The Service contains:

```yaml
selector:
  app: nginx
```

Therefore:

```text
SERVICE
selector: app=nginx
        |
        | searches for
        v
PODS
label: app=nginx
```

The values match:

```text
Pod Label                 Service Selector
---------                 ----------------
app: nginx      <------>  app: nginx
```

This is how the Service knows which Pods should receive traffic.

---

# 6. Names Do NOT Have to Match

For example, the Deployment could be:

```yaml
metadata:
  name: nginx-deployment
```

The Service could be:

```yaml
metadata:
  name: company-web-service
```

The Pods might be:

```text
nginx-deployment-7c79c4bf97-x8k2m
nginx-deployment-7c79c4bf97-z9p4q
```

They can still communicate because the Service uses:

```yaml
selector:
  app: nginx
```

and the Pods have:

```yaml
labels:
  app: nginx
```

Therefore:

```text
Names DON'T connect Service → Pod.

Labels + Selectors DO.
```

---

# 7. Complete Relationship

```text
                 Deployment
          name: nginx-deployment
                     |
                     |
                     | creates
                     v
                ReplicaSet
                     |
                     |
                     | creates
                     v
              +-------------+
              |    Pod 1    |
              | app=nginx   |
              +-------------+
                     ^
                     |
                     |
              selector:
              app=nginx
                     |
                     |
              +-------------+
              |   Service   |
              |nginx-service|
              +-------------+
```

If there are two Pods:

```text
                    Service
                nginx-service
                      |
                selector:
                app=nginx
                      |
             +--------+--------+
             |                 |
             v                 v
          Pod 1              Pod 2
        app=nginx          app=nginx
```

The Service can therefore distribute traffic across both Pods.

---

# 8. Check Pod Labels

Use:

```bash
kubectl get pods --show-labels
```

You may see:

```text
NAME                                READY   LABELS
nginx-deployment-7c79...-x8k2m      1/1     app=nginx,pod-template-hash=7c79...
nginx-deployment-7c79...-z9p4q      1/1     app=nginx,pod-template-hash=7c79...
```

Notice:

```text
app=nginx
```

---

# 9. Find Pods Using a Label

```bash
kubectl get pods -l app=nginx
```

`-l` means **label selector**.

Therefore:

```bash
kubectl get pods -l app=nginx
```

means:

> Show all Pods whose label is `app=nginx`.

---

# 10. Check the Service Selector

```bash
kubectl get service nginx-service
```

More details:

```bash
kubectl describe service nginx-service
```

Or:

```bash
kubectl get service nginx-service -o yaml
```

Look for:

```yaml
selector:
  app: nginx
```

---

# 11. Check Whether Service Found the Pods

```bash
kubectl get endpoints nginx-service
```

Example:

```text
NAME            ENDPOINTS
nginx-service   10.244.0.15:80,10.244.0.16:80
```

You can also inspect EndpointSlices:

```bash
kubectl get endpointslices
```

---

# 12. Port Relationship

```yaml
containers:
  - name: nginx-container
    image: nginx
    ports:
      - containerPort: 80

---
spec:
  ports:
    - port: 80
      targetPort: 80
```

| Setting | Meaning |
|---|---|
| `containerPort` | Port used by the application inside the Pod |
| `targetPort` | Pod port to which Service sends traffic |
| `port` | Port exposed by the Service |

Traffic flow:

```text
Client
   |
   v
Service
port: 80
   |
   v
targetPort: 80
   |
   v
Pod
containerPort: 80
   |
   v
NGINX
```

---

# 13. Apply the Manifest

Save the YAML as:

```text
nginx.yaml
```

Apply it:

```bash
kubectl apply -f nginx.yaml
```

Check the resources:

```bash
kubectl get deployments
kubectl get pods
kubectl get pods --show-labels
kubectl get services
kubectl describe service nginx-service
kubectl get endpoints nginx-service
```

---

# 14. Important Rule to Remember

```text
Deployment
    |
    | creates
    v
ReplicaSet
    |
    | creates
    v
Pods
    |
    | have LABELS
    |
    +------------------+
                       |
                       | matched by
                       v
                 Service SELECTOR
```

## The Golden Rule

> **Service selector must match the Pod label.**

For example:

```yaml
# Pod
labels:
  app: nginx
```

must match:

```yaml
# Service
selector:
  app: nginx
```

The **Deployment name, Pod name, Container name and Service name do not have to be the same**.

---

# 15. Namespace-Aware Troubleshooting

Namespaces are extremely important when troubleshooting Kubernetes.

A Pod, Deployment or Service may exist, but your command may not find it because you are looking in the **wrong namespace**.

## Check Your Current Namespace

First check the current context:

```bash
kubectl config current-context
```

Then check the namespace configured for that context:

```bash
kubectl config view --minify --output 'jsonpath={..namespace}'
```

If nothing is returned, Kubernetes normally uses:

```text
default
```

---

## List Namespaces

```bash
kubectl get namespaces
```

Short form:

```bash
kubectl get ns
```

Example:

```text
NAME              STATUS
default           Active
kube-system       Active
kube-public       Active
training          Active
```

---

## Look for Pods Across All Namespaces

If this returns nothing:

```bash
kubectl get pods
```

do not immediately assume that the Pod does not exist.

Try:

```bash
kubectl get pods -A
```

or:

```bash
kubectl get pods --all-namespaces
```

Example:

```text
NAMESPACE    NAME                               READY
default      nginx-deployment-xxx-abc           1/1
training     spark-master-xxx-def               1/1
kube-system coredns-xxx-ghi                     1/1
```

Now you know **where the Pod actually exists**.

---

## Work With a Specific Namespace

Suppose the application is in:

```text
training
```

Use:

```bash
kubectl get pods -n training
```

Services:

```bash
kubectl get svc -n training
```

Deployments:

```bash
kubectl get deployments -n training
```

Everything:

```bash
kubectl get all -n training
```

---

# 16. Service and Pods Should Normally Be in the Same Namespace

Suppose you have:

```text
Namespace: training

Pod:
  app=nginx

Service:
  selector app=nginx
```

Then:

```text
Namespace: training

        Service
    nginx-service
         |
         | selector
         | app=nginx
         v
    +-----------+
    |   Pod 1   |
    | app=nginx |
    +-----------+
```

But consider:

```text
Namespace: web
    Service
    selector: app=nginx

Namespace: training
    Pod
    label: app=nginx
```

Even though:

```text
app=nginx
```

matches, the Service does **not** normally select that Pod because Services select Pods in their own namespace.

So always check:

```text
1. Namespace
2. Labels
3. Selector
4. Endpoints
5. Ports
```

---

# 17. Namespace-Aware Service Troubleshooting

Suppose:

```bash
kubectl get svc -n training
```

shows:

```text
NAME            TYPE
nginx-service   ClusterIP
```

Check the Service:

```bash
kubectl describe svc nginx-service -n training
```

Look for:

```text
Selector: app=nginx
```

Now check whether matching Pods exist **in the same namespace**:

```bash
kubectl get pods -n training -l app=nginx
```

If Pods appear, check their labels:

```bash
kubectl get pods -n training --show-labels
```

Then check endpoints:

```bash
kubectl get endpoints nginx-service -n training
```

If you see:

```text
ENDPOINTS
<none>
```

there is usually a problem with:

```text
Service selector
      ↓
Pod labels
```

or the selected Pods are not ready.

---

# 18. Troubleshooting Flow

When a Service cannot reach an application, follow this sequence:

```text
STEP 1
Find the namespace
      |
      v
STEP 2
Find the Service
      |
      v
STEP 3
Check Service selector
      |
      v
STEP 4
Find Pods with that label
      |
      v
STEP 5
Check Pod status/readiness
      |
      v
STEP 6
Check Service endpoints
      |
      v
STEP 7
Check port / targetPort
      |
      v
STEP 8
Check application logs
```

Commands:

```bash
# 1. Search everywhere
kubectl get pods -A
kubectl get svc -A

# 2. Assume namespace is training
kubectl get pods -n training
kubectl get svc -n training

# 3. Check labels
kubectl get pods -n training --show-labels

# 4. Check Service
kubectl describe svc nginx-service -n training

# 5. Test the selector manually
kubectl get pods -n training -l app=nginx

# 6. Check endpoints
kubectl get endpoints nginx-service -n training

# 7. Inspect Pod
kubectl describe pod <pod-name> -n training

# 8. Check application logs
kubectl logs <pod-name> -n training
```

---

# 19. Very Useful Troubleshooting Commands

## Find a Resource When You Don't Know Its Namespace

```bash
kubectl get pods -A
```

```bash
kubectl get svc -A
```

```bash
kubectl get deployments -A
```

---

## Find a Specific Pod

Linux:

```bash
kubectl get pods -A | grep nginx
```

For example:

```text
training   nginx-deployment-7c79c4bf97-x8k2m   1/1   Running
```

Now you know:

```text
Namespace = training
Pod       = nginx-deployment-7c79c4bf97-x8k2m
```

Then:

```bash
kubectl describe pod nginx-deployment-7c79c4bf97-x8k2m -n training
```

---

## Check Pod Logs

```bash
kubectl logs <pod-name> -n <namespace>
```

Example:

```bash
kubectl logs nginx-deployment-7c79c4bf97-x8k2m -n training
```

Follow logs continuously:

```bash
kubectl logs -f nginx-deployment-7c79c4bf97-x8k2m -n training
```

---

## Check Events

Events are extremely useful when a Pod does not start:

```bash
kubectl get events -n training
```

Sort by creation time:

```bash
kubectl get events -n training --sort-by=.metadata.creationTimestamp
```

This can reveal problems such as:

```text
FailedScheduling
FailedMount
ImagePullBackOff
ErrImagePull
FailedCreate
Insufficient CPU
Insufficient memory
PVC not found
```

---

# 20. Set Your Default Namespace

Instead of repeatedly typing:

```bash
-n training
```

you can set the current context to use that namespace:

```bash
kubectl config set-context --current --namespace=training
```

Now:

```bash
kubectl get pods
```

means:

```bash
kubectl get pods -n training
```

Check it:

```bash
kubectl config view --minify | grep namespace
```

To return to `default`:

```bash
kubectl config set-context --current --namespace=default
```

---

# 21. OKD / OpenShift Equivalent

The same namespace concept applies to your **OKD/OpenShift** environment.

With `oc`, OpenShift commonly presents namespaces to users as **Projects**.

List projects:

```bash
oc get projects
```

Check current project:

```bash
oc project
```

Switch project:

```bash
oc project training
```

Then:

```bash
oc get pods
oc get svc
```

You can also explicitly specify the namespace:

```bash
oc get pods -n training
```

And standard Kubernetes commands continue to work:

```bash
kubectl get pods -n training
```

Therefore, in OKD/OpenShift:

```text
Kubernetes terminology       OpenShift terminology

Namespace            ≈       Project
kubectl                       oc
```

A Project adds OpenShift-specific management around the underlying Kubernetes namespace.

---

# 22. Quick Troubleshooting Checklist

When an application is not reachable:

```text
[ ] Am I connected to the correct cluster/context?

[ ] Am I looking in the correct namespace?

[ ] Is the Deployment available?

[ ] Are the Pods Running and Ready?

[ ] Do the Pods have the expected labels?

[ ] Does the Service selector match those labels?

[ ] Are Service and Pods in the same namespace?

[ ] Does the Service have endpoints?

[ ] Is targetPort correct?

[ ] Is the application actually listening on that port?

[ ] What does kubectl describe show?

[ ] What do kubectl logs show?

[ ] What do namespace events show?
```

Useful sequence:

```bash
kubectl config current-context

kubectl get pods -A

kubectl get svc -A

kubectl get pods -n training --show-labels

kubectl describe svc nginx-service -n training

kubectl get pods -n training -l app=nginx

kubectl get endpoints nginx-service -n training

kubectl describe pod <pod-name> -n training

kubectl logs <pod-name> -n training

kubectl get events -n training --sort-by=.metadata.creationTimestamp
```

## Troubleshooting Rule

> **Always verify the Cluster/Context → Namespace → Service Selector → Pod Label → Endpoint → Port → Logs chain.**

```text
Cluster / Context
       ↓
Namespace
       ↓
Service
       ↓
Selector
       ↓
Pod Label
       ↓
Pod Ready?
       ↓
Endpoint
       ↓
targetPort
       ↓
Container / Application
       ↓
Logs
```
