# CRC on a cloned Linux VM

Follow [the Bash configuration guide](00-bashrc.md#three-separate-additions-to-bashrc) for the three Bash additions: OKD helpers, CRC/oc PATH, and the user session environment.

Then run all [three validation stages](00-bashrc.md#validation-1-bash-syntax-and-preserved-programs), including `systemctl --user daemon-reload`. The guide includes recovery steps if the current user has no runtime directory or D-Bus socket. Exporting variables alone cannot create either one.

Back up your existing `~/.bashrc` before applying the additions in the Bash configuration guide. Do not paste Markdown prose or fences into it.


---

Linux Service related issue for crc


```
sudo systemctl stop libvirtd.service libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket && \
sudo systemctl start libvirtd.socket && \
sudo systemctl start libvirtd.service
```

---
```
systemctl --user daemon-reload
sudo systemctl status libvirtd --no-pager
virsh -c qemu:///system list --all
```

--
