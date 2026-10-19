
CRC not reflecting in the cloned machine

```
cat <<'EOF' | tee -a ~/.bashrc

# CRC / OpenShift
export PATH="$HOME/.local/bin:$HOME/.crc/bin/oc:$PATH"
EOF
```

```


export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"

systemctl --user daemon-reload

```
