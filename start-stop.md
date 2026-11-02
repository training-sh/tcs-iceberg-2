
# Stop Containers/Pod commands


# Kafka and ZooKeeper

```
oc -n bigdata scale statefulset/kafka statefulset/zookeeper --replicas=0
```

# HiveServer2 and Hive Metastore

```
oc -n bigdata scale deployment/hiveserver2 deployment/hive-metastore --replicas=0
```


# YARN ResourceManager, NodeManager and MapReduce History Server

```
oc -n bigdata scale deployment/resourcemanager deployment/nodemanager deployment/historyserver --replicas=0
```


# HDFS DataNode and NameNode
```
oc -n bigdata scale statefulset/datanode statefulset/namenode --replicas=0
```



# Main MySQL instance
```
oc -n bigdata scale statefulset/mysql --replicas=0
```
