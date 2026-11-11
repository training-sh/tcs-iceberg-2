
```
df -h
sudo du -sh /var/log/*
sudo journalctl --disk-usage
```

Keep only the last 2 days of systemd logs
 Limit journal size to 100 MB
Remove rotated/compressed log files

```
sudo journalctl --vacuum-time=2d
sudo journalctl --vacuum-size=100M
sudo find /var/log -type f -name "*.gz" -delete
sudo find /var/log -type f -name "*.1" -delete
sudo find /var/log -type f -name "*.old" -delete
```

```
sudo apt clean
sudo apt autoclean
sudo apt autoremove --purge -y
```

```
sudo systemd-tmpfiles --clean
```

check space again

```
df -h
```
