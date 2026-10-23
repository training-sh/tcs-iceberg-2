# Kubernetes / OpenShift Deployment Example — Apache Spark

## 1. Objective

In this example we will run:

- **1 Spark Master**
- **3 Spark Workers**
- Scale the workers from **3 → 5**
- Use both `kubectl` and `oc`
- Understand how Deployment, ReplicaSet, Pod, labels and Services relate

The architecture will be:

```text
                    Spark Cluster
                         |
                  +--------------+
                  | Spark Master |
                  | replicas: 1  |
                  +------+-------+
                         |
               spark://spark-master:7077
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      Worker 1        Worker 2        Worker 3
```

Later:

```text
kubectl scale deployment spark-worker --replicas=5
```

will result in:

```text
                    Spark Master
                         |
          +-------+------+------+-------+
          |       |      |      |       |
          v       v      v      v       v
         W1      W2     W3     W4      W5
```

---

# 2. Create Namespace

Using Kubernetes:

```bash
kubectl create namespace spark
```

Using OpenShift:

```bash
oc new-project spark
```

Check:

```bash
kubectl get namespaces
```

or:

```bash
oc get projects
```

For the remaining examples we will explicitly use:

```text
-n spark
```

so that it is always clear which namespace/project we are working with.

---

# 3. Spark Master Deployment

Create:

```text
spark-master.yaml
```

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: spark-master
  namespace: spark

spec:

  # We need ONE Spark Master Pod
  replicas: 1

  selector:
    matchLabels:
      app: spark-master

  template:

    metadata:
      labels:
        app: spark-master

    spec:
      containers:

        - name: spark-master
          image: apache/spark:3.5.7

          command:
            - /opt/spark/bin/spark-class

          args:
            - org.apache.spark.deploy.master.Master

          ports:
            - name: spark
              containerPort: 7077

            - name: web-ui
              containerPort: 8080
```

The important part is:

```yaml
replicas: 1
```

Therefore:

```text
Deployment
spark-master
     |
     | replicas: 1
     v
ReplicaSet
     |
     v
Spark Master Pod
```

---

# 4. Create the Spark Master

Using `kubectl`:

```bash
kubectl apply -f spark-master.yaml
```

Using OpenShift:

```bash
oc apply -f spark-master.yaml
```

Both commands create the same Kubernetes Deployment resource.

Check:

```bash
kubectl get deployment -n spark
```

or:

```bash
oc get deployment -n spark
```

Expected conceptually:

```text
NAME           READY   UP-TO-DATE   AVAILABLE
spark-master   1/1     1            1
```

---

# 5. Check the Spark Master Pod

```bash
kubectl get pods -n spark
```

or:

```bash
oc get pods -n spark
```

You should see a generated Pod name similar to:

```text
spark-master-7d8c8c7d4f-kx8mz
```

Notice that we did NOT manually create this Pod.

The relationship is:

```text
Deployment
spark-master
      |
      v
ReplicaSet
spark-master-xxxxxxxxxx
      |
      v
Pod
spark-master-xxxxxxxxxx-xxxxx
```

---

# 6. Create a Service for the Spark Master

Workers need a stable way to find the Spark Master.

Create:

```text
spark-master-service.yaml
```

```yaml
apiVersion: v1
kind: Service

metadata:
  name: spark-master
  namespace: spark

spec:

  selector:
    app: spark-master

  ports:

    - name: spark
      port: 7077
      targetPort: 7077

    - name: web-ui
      port: 8080
      targetPort: 8080

  type: ClusterIP
```

Apply:

```bash
kubectl apply -f spark-master-service.yaml
```

or:

```bash
oc apply -f spark-master-service.yaml
```

---

# 7. How Does the Service Find the Master?

The Master Pod has:

```yaml
labels:
  app: spark-master
```

The Service has:

```yaml
selector:
  app: spark-master
```

Therefore:

```text
Spark Master Service
name: spark-master
       |
       | selector
       | app=spark-master
       v
Spark Master Pod
label: app=spark-master
```

The names do not create this relationship.

The **selector and label** create the relationship.

---

# 8. Spark Master DNS Name

Because the Service is named:

```text
spark-master
```

workers in the same namespace can reach the master using:

```text
spark-master:7077
```

Spark therefore uses:

```text
spark://spark-master:7077
```

This is much better than putting the Spark Master's Pod IP into the worker configuration.

Pod IPs can change.

The Service gives us a stable network identity.

---

# 9. Spark Worker Deployment

Now create:

```text
spark-worker.yaml
```

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: spark-worker
  namespace: spark

spec:

  # Start THREE Spark Worker Pods
  replicas: 3

  selector:
    matchLabels:
      app: spark-worker

  template:

    metadata:
      labels:
        app: spark-worker

    spec:
      containers:

        - name: spark-worker
          image: apache/spark:3.5.7

          command:
            - /opt/spark/bin/spark-class

          args:
            - org.apache.spark.deploy.worker.Worker
            - spark://spark-master:7077

          ports:
            - name: web-ui
              containerPort: 8081
```

The important line is:

```yaml
replicas: 3
```

This means:

```text
Spark Worker Deployment
       |
       | desired replicas = 3
       v
    ReplicaSet
       |
       +------ Pod: Worker 1
       |
       +------ Pod: Worker 2
       |
       +------ Pod: Worker 3
```

---

# 10. Deploy the Spark Workers

Using Kubernetes:

```bash
kubectl apply -f spark-worker.yaml
```

Using OpenShift:

```bash
oc apply -f spark-worker.yaml
```

Check:

```bash
kubectl get deployments -n spark
```

Expected:

```text
NAME           READY
spark-master   1/1
spark-worker   3/3
```

---

# 11. Look at the Actual Pods

```bash
kubectl get pods -n spark
```

or:

```bash
oc get pods -n spark
```

Conceptually:

```text
NAME                             READY   STATUS
spark-master-7d8c8c7d4f-kx8mz    1/1     Running

spark-worker-68f6c8bd67-ab123     1/1     Running
spark-worker-68f6c8bd67-cd456     1/1     Running
spark-worker-68f6c8bd67-ef789     1/1     Running
```

Therefore we have:

```text
2 Deployments
      |
      +--- spark-master
      |       |
      |       +--- 1 Pod
      |
      +--- spark-worker
              |
              +--- 3 Pods
```

Total:

```text
4 Pods
```

---

# 12. See Deployment → ReplicaSet → Pod

Run:

```bash
kubectl get deployment,rs,pods -n spark
```

You should conceptually see:

```text
deployment.apps/spark-master
deployment.apps/spark-worker

replicaset.apps/spark-master-xxxxxxxxxx
replicaset.apps/spark-worker-xxxxxxxxxx

pod/spark-master-xxxxxxxxxx-xxxxx

pod/spark-worker-xxxxxxxxxx-aaaaa
pod/spark-worker-xxxxxxxxxx-bbbbb
pod/spark-worker-xxxxxxxxxx-ccccc
```

This demonstrates the actual relationship:

```text
Deployment
    |
    v
ReplicaSet
    |
    v
Pods
```

---

# 13. Scale Workers from 3 to 5

This is one of the main reasons Deployment is useful.

Currently:

```text
spark-worker

replicas = 3
```

Run:

```bash
kubectl scale deployment spark-worker \
  --replicas=5 \
  -n spark
```

OpenShift:

```bash
oc scale deployment spark-worker \
  --replicas=5 \
  -n spark
```

Check:

```bash
kubectl get deployment spark-worker -n spark
```

You should eventually see:

```text
NAME           READY
spark-worker   5/5
```

Now:

```bash
kubectl get pods -n spark
```

will show:

```text
1 Spark Master

5 Spark Workers
```

Architecture:

```text
                      Master
                        |
                        |
          +------+------+------+------+------+
          |      |      |      |      |
          v      v      v      v      v
         W1     W2     W3     W4     W5
```

---

# 14. Scale Workers Back Down

Scale from:

```text
5 → 3
```

Using Kubernetes:

```bash
kubectl scale deployment spark-worker \
  --replicas=3 \
  -n spark
```

Using OpenShift:

```bash
oc scale deployment spark-worker \
  --replicas=3 \
  -n spark
```

Kubernetes terminates the extra worker Pods.

Check:

```bash
kubectl get pods -n spark
```

---

# 15. What Happens if a Worker Pod Dies?

Assume:

```text
Desired Workers = 3

Worker 1   Running
Worker 2   Running
Worker 3   Running
```

Delete one manually:

```bash
kubectl delete pod <spark-worker-pod-name> -n spark
```

For example:

```bash
kubectl delete pod spark-worker-68f6c8bd67-ab123 -n spark
```

Immediately check:

```bash
kubectl get pods -n spark
```

The Deployment/ReplicaSet notices:

```text
Desired = 3

Actual = 2
```

and creates another Pod.

```text
Worker 1 ✓
Worker 2 ✓
Worker 3 ✗
     |
     | ReplicaSet detects missing replica
     v
New Worker Pod created
```

Eventually:

```text
Desired = 3
Actual  = 3
```

This demonstrates **self-healing**.

---

# 16. Why Deployment Instead of Creating Pods Manually?

Without Deployment:

```text
Create Worker Pod 1 manually
Create Worker Pod 2 manually
Create Worker Pod 3 manually

Worker 2 crashes
        |
        v
You need to deal with it yourself
```

With Deployment:

```text
Deployment

"I always want 3 Spark workers."

        |
        v

Kubernetes continuously maintains

Worker 1
Worker 2
Worker 3
```

If one disappears:

```text
3 desired
2 actual
    |
    v
Create replacement
    |
    v
3 actual
```

---

# 17. Change Worker Count in YAML

Instead of:

```bash
kubectl scale
```

we can modify:

```yaml
replicas: 3
```

to:

```yaml
replicas: 5
```

and apply again:

```bash
kubectl apply -f spark-worker.yaml
```

or:

```bash
oc apply -f spark-worker.yaml
```

The Deployment controller changes the actual number of Pods until it reaches:

```text
Desired = 5
Actual  = 5
```

For configuration managed in Git, changing the YAML and applying it is generally preferable because the desired replica count remains documented in the manifest.

---

# 18. Useful Deployment Commands — kubectl

## List Deployments

```bash
kubectl get deployments -n spark
```

Short form:

```bash
kubectl get deploy -n spark
```

## Describe Deployment

```bash
kubectl describe deployment spark-worker -n spark
```

## List Pods

```bash
kubectl get pods -n spark
```

## Show Labels

```bash
kubectl get pods -n spark --show-labels
```

## List ReplicaSets

```bash
kubectl get rs -n spark
```

## Scale Deployment

```bash
kubectl scale deployment spark-worker \
  --replicas=5 \
  -n spark
```

## Check Rollout

```bash
kubectl rollout status deployment/spark-worker -n spark
```

## View Rollout History

```bash
kubectl rollout history deployment/spark-worker -n spark
```

## Restart Deployment

```bash
kubectl rollout restart deployment/spark-worker -n spark
```

## Delete Deployment

```bash
kubectl delete deployment spark-worker -n spark
```

---

# 19. Same Commands Using OpenShift `oc`

Most standard Deployment operations are almost identical.

## List Deployments

```bash
oc get deployments -n spark
```

## List Pods

```bash
oc get pods -n spark
```

## List ReplicaSets

```bash
oc get rs -n spark
```

## Describe Worker Deployment

```bash
oc describe deployment spark-worker -n spark
```

## Scale Workers

```bash
oc scale deployment spark-worker \
  --replicas=5 \
  -n spark
```

## Check Rollout

```bash
oc rollout status deployment/spark-worker -n spark
```

## Restart

```bash
oc rollout restart deployment/spark-worker -n spark
```

## Check Logs

```bash
oc logs <worker-pod-name> -n spark
```

---

# 20. kubectl vs oc

For standard Kubernetes resources such as:

```text
Pod
Deployment
ReplicaSet
Service
ConfigMap
Secret
PVC
```

you will commonly find that:

```bash
kubectl get pods
```

and:

```bash
oc get pods
```

perform equivalent Kubernetes resource operations when pointed at the same OpenShift/OKD cluster.

Therefore:

```text
             Kubernetes API
                   |
         +---------+---------+
         |                   |
      kubectl                oc
                             |
                             + OpenShift-specific
                               capabilities
```

`oc` additionally provides commands and workflows specific to OpenShift.

---

# 21. Important Deployment Fields

Look again at the worker:

```yaml
spec:

  replicas: 3

  selector:
    matchLabels:
      app: spark-worker

  template:

    metadata:
      labels:
        app: spark-worker
```

Three important concepts:

### `replicas`

```yaml
replicas: 3
```

means:

```text
Maintain 3 Pods.
```

### Deployment Selector

```yaml
selector:
  matchLabels:
    app: spark-worker
```

means:

```text
These are the Pods this Deployment manages.
```

### Pod Label

```yaml
labels:
  app: spark-worker
```

means the created Pods receive:

```text
app=spark-worker
```

The selector and Pod template label must match.

---

# 22. Master and Worker Labels Must Be Different

Master:

```yaml
labels:
  app: spark-master
```

Worker:

```yaml
labels:
  app: spark-worker
```

Therefore:

```text
Master Deployment
selector:
app=spark-master
       |
       v
Master Pod
app=spark-master


Worker Deployment
selector:
app=spark-worker
       |
       +------ Worker Pod
       +------ Worker Pod
       +------ Worker Pod
```

Do not accidentally give both Deployments overlapping selectors.

---

# 23. Inspect Only Spark Workers

Because workers have:

```text
app=spark-worker
```

we can run:

```bash
kubectl get pods \
  -l app=spark-worker \
  -n spark
```

Likewise with OpenShift:

```bash
oc get pods \
  -l app=spark-worker \
  -n spark
```

This should return only the Spark worker Pods.

---

# 24. Scale Using the Manifest vs CLI

There are two common approaches.

### CLI

```bash
kubectl scale deployment spark-worker --replicas=5 -n spark
```

Good for:

```text
Demonstrations
Testing
Temporary scaling
Troubleshooting
```

### YAML

Change:

```yaml
replicas: 5
```

then:

```bash
kubectl apply -f spark-worker.yaml
```

Better for:

```text
Git
GitOps
Repeatable environments
Production configuration
Auditing
```

Important:

If YAML says:

```yaml
replicas: 3
```

and you manually run:

```bash
kubectl scale deployment spark-worker --replicas=5 -n spark
```

you now have 5.

But if you later reapply the YAML containing:

```yaml
replicas: 3
```

the desired state goes back to:

```text
3
```

---

# 25. Complete Architecture

```text
Namespace / OpenShift Project
             spark
               |
               |
      +--------+---------+
      |                  |
      v                  v
Master Deployment    Worker Deployment
replicas: 1          replicas: 3
      |                  |
      v                  v
 ReplicaSet           ReplicaSet
      |                  |
      v             +----+----+
 Master Pod         |    |    |
                    v    v    v
                   W1   W2   W3

      ^
      |
Spark Master Service
spark-master:7077
      ^
      |
      +---------------- Workers connect here
```

After:

```bash
kubectl scale deployment spark-worker --replicas=5 -n spark
```

we get:

```text
Master Deployment
      |
      v
  1 Master


Worker Deployment
      |
      +---- W1
      +---- W2
      +---- W3
      +---- W4
      +---- W5
```

---

# 26. Key Takeaways

```text
Deployment
    |
    | controls desired state
    v
ReplicaSet
    |
    | maintains replica count
    v
Pods
```

For this Spark example:

```text
spark-master Deployment
replicas: 1
        ↓
1 Spark Master Pod


spark-worker Deployment
replicas: 3
        ↓
3 Spark Worker Pods
```

Scale:

```bash
kubectl scale deployment spark-worker --replicas=5 -n spark
```

becomes:

```text
spark-worker Deployment
replicas: 5
        ↓
5 Spark Worker Pods
```

The same standard Kubernetes Deployment can be managed on OKD/OpenShift using:

```text
kubectl
```

or:

```text
oc
```

## Simple Definition

> **A Deployment tells Kubernetes how many instances of an application should be running and Kubernetes continuously works to maintain that desired state.**

For our Spark example:

> **Master Deployment says: keep 1 Spark Master running.**

> **Worker Deployment says: keep 3 (or 5) Spark Workers running.**
