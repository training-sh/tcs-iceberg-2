
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


```
# Remove old journal archives, keeping approximately 256 MB
sudo journalctl --rotate
sudo journalctl --vacuum-size=256M

# Clear downloaded APT packages
sudo apt-get clean

# Remove revisions confirmed as disabled on this VM
sudo snap remove core22 --revision=2955
sudo snap remove firefox --revision=9137
sudo snap remove gnome-46-2404 --revision=164
sudo snap remove snap-store --revision=1447

# Remove cached Snap downloads
sudo find /var/lib/snapd/cache -maxdepth 1 -type f -delete

# Check remaining space
df -h /
sudo journalctl --disk-usage
```
