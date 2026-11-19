# Host journal maintenance

Run these on the Linux VM host when checking disk use:

```bash
df -h /
sudo journalctl --disk-usage
sudo du -xhd1 /var/log
```

To remove old journal archives while retaining roughly 512 MiB:

```bash
sudo journalctl --rotate
sudo journalctl --vacuum-size=512M
sudo journalctl --disk-usage
df -h /
```

This affects host journal history. It does not delete images, application data, PVCs or the CRC disk. It does not set a permanent retention policy. Keep this separate from the capstone's namespace cleanup.
