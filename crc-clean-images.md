To clean up crc storage space


```
crc status
```

```
oc project default
```

```
oc debug node/crc
```

```
chroot /host
```

```
crictl images --digests | grep community-operator-index
```
 

```
crictl rmi --prune
```



```
crictl images --digests | grep community-operator-index
```

