# oct 30 - admin

```
Routes

give a name to route

hostname

myfastapidemo.apps-crc.testing

path :   /db

service: 8000

---
another route for ningx

give a name

host name

nginxdemo.apps-crc.testing

path:   /

service: 8080
```
----


https://github.com/training-sh/tcs-iceberg-2/blob/main/04-OpenShift/042-OC-Hands-On.md


crc console --credentials

use login command as kubeadmin


# List projects
oc projects

# Show current project
oc project

# Switch project
oc project bigdata

# Create new project
oc new-project training

# List namespaces
oc get namespaces


# List pods
oc get pods

# List pods in all namespaces
oc get pods -A

# Show pod details
oc get pods -o wide

# List deployments
oc get deployments

# List services
oc get svc

# List all common resources
oc get all

# Describe pod
oc describe pod POD_NAME

# View pod logs
oc logs POD_NAME

# Follow logs
oc logs -f POD_NAME




https://github.com/training-sh/tcs-iceberg-2/blob/main/04-OpenShift/042-OC-Hands-On.md
