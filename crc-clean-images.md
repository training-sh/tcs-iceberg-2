# Linux VM - clean logs

copy paste the whole, when prompted for password, enter password

```bash
# Shrink systemd journal logs
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s

# Remove rotated and compressed logs
sudo find /var/log -type f \( -name "*.gz" -o -name "*.old" -o -name "*.1" -o -name "*.2" -o -name "*.3" \) -delete

# Truncate active text logs (preserves files)
sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} +

# Clear common syslog files
sudo truncate -s 0 /var/log/syslog 2>/dev/null
sudo truncate -s 0 /var/log/kern.log 2>/dev/null
sudo truncate -s 0 /var/log/auth.log 2>/dev/null

# Remove crash reports
sudo rm -f /var/crash/*

# Clean APT caches
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove --purge -y
```



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

