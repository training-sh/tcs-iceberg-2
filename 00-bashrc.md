# Bash configuration for CRC and OKD

Run the Bash blocks in this guide in the Linux VM terminal as the ordinary login user after installing CRC with [00 - Installation](00-Introduction/00-Installation.md). Keep your existing `~/.bashrc`; back it up before applying the additions. These blocks append shell configuration with quoted heredocs so variables remain literal until Bash loads the file.

## Three separate additions to `.bashrc`

Apply all three additions below in order. They serve different purposes; they are not three replacement files. Copy only the contents of each fenced Bash block using GitHub's copy button. Do not copy JSON from a notebook, Markdown fences, shell prompts, or rendered prose into `.bashrc`. The quoted `EOF` delimiter preserves `$HOME`, `$PATH`, quotes, and command substitutions literally until Bash loads the file.

Back up the existing file first. These additions preserve your Java, Hadoop, Hive, Spark, Kafka, and other settings. If the file is already damaged, inspect the backup and remove the pasted Markdown/JSON before continuing; appending these blocks cannot repair existing corruption.

```bash
# Temporary recovery only if basic commands cannot be found:
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin${PATH:+:$PATH}"
touch "$HOME/.bashrc"
cp -p "$HOME/.bashrc" "$HOME/.bashrc.before-okd.$(date +%Y%m%d-%H%M%S).bak"
bash -n "$HOME/.bashrc"
```

If `bash -n` reports an error, stop and edit the damaged file before continuing.

### Addition 1: original OKD helper functions

If `# BEGIN OKD LAB` already exists, replace that entire section through `# END OKD LAB` with the updated section below (the contents between the `EOF` delimiters). The installer deliberately skips existing sections, so rerunning it alone will not update older functions. Back up and syntax-check `.bashrc` before sourcing it.

For a new setup, run this block once. It appends an `okd-env` function only when the marked section is absent. The function loads the CRC administrator kubeconfig and selects the `bigdata` project. It does not start the cluster automatically.

```bash
touch "$HOME/.bashrc"
if ! grep -q '^# BEGIN OKD LAB$' "$HOME/.bashrc"; then
  tee -a "$HOME/.bashrc" >/dev/null <<'EOF'

# BEGIN OKD LAB
# Stable course copy; okd-env refreshes it from CRC after startup.
export KUBECONFIG="$HOME/.kube/crc-admin.kubeconfig"

okd-env() {
    local crc_state oc_environment
    # Reset this even if a previous command changed or unset KUBECONFIG.
    export KUBECONFIG="$HOME/.kube/crc-admin.kubeconfig"
    if ! crc_state="$(crc status 2>&1)"; then
        printf '%s\n' "$crc_state" >&2
        echo "Cannot read CRC status. Check libvirt and the user session." >&2
        return 1
    fi
    if ! grep -Eq '^(OpenShift|OKD):[[:space:]]+Running' <<<"$crc_state"; then
        echo "OKD is stopped. Run: okd-start" >&2
        return 1
    fi
    # Capture first: eval alone would hide a failed crc oc-env command.
    oc_environment="$(crc oc-env)" || return 1
    eval "$oc_environment" || return 1
    if [[ ! -s "$HOME/.crc/machines/crc/kubeconfig" ]]; then
        echo "CRC administrator kubeconfig is missing or empty. Inspect CRC startup errors." >&2
        return 1
    fi
    mkdir -p "$HOME/.kube" || return 1
    # Restrict permissions from creation; stop if copying or chmod fails.
    (
        umask 077
        cp "$HOME/.crc/machines/crc/kubeconfig" "$KUBECONFIG" &&
        chmod 600 "$KUBECONFIG"
    ) || return 1
    # Fail visibly if the API or administrator credentials are not usable.
    oc whoami >/dev/null || return 1
    oc project bigdata 2>/dev/null || oc new-project bigdata
}

okd-start() {
    crc start && okd-env
}

okd-status() {
    crc status
}

okd-stop() {
    crc stop
}

okd-restart() {
    crc stop && crc start && okd-env
}

echo "OKD commands: okd-start, okd-env, okd-status, okd-stop, okd-restart"
# END OKD LAB
EOF
fi
bash -n "$HOME/.bashrc" && source "$HOME/.bashrc"
```


### Addition 2: CRC and OpenShift client PATH

This includes the missing CRC `oc` directory and keeps the existing PATH. The marker prevents duplicate appends. Remove an older duplicate section manually if one already exists.

```bash
if ! grep -qxF '# BEGIN CRC PATH' "$HOME/.bashrc"; then
  cat <<'EOF' | tee -a "$HOME/.bashrc" >/dev/null

# BEGIN CRC PATH
case ":$PATH:" in
  *":$HOME/.crc/bin/oc:"*) ;;
  *) export PATH="$HOME/.crc/bin/oc:$PATH" ;;
esac
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
# END CRC PATH
EOF
fi
bash -n "$HOME/.bashrc" && source "$HOME/.bashrc"
```

### Addition 3: user systemd session environment

Run as the ordinary VM login user, including on a cloned image. The UID is calculated on that VM; do not copy a numeric UID or another user's bus address. This only sets the environment when the current user's runtime directory and bus actually exist. It does not create a login session or run `daemon-reload` whenever a terminal opens.

```bash
if ! grep -qxF '# BEGIN CRC USER SESSION' "$HOME/.bashrc"; then
  cat <<'EOF' | tee -a "$HOME/.bashrc" >/dev/null

# BEGIN CRC USER SESSION
if [[ -d "/run/user/$(id -u)" && -O "/run/user/$(id -u)" && -S "/run/user/$(id -u)/bus" ]]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi
# END CRC USER SESSION
EOF
fi
bash -n "$HOME/.bashrc" && source "$HOME/.bashrc"
```

### Validation 1: Bash syntax and preserved programs

```bash
bash -n "$HOME/.bashrc" && echo 'PASS: Bash syntax'
printf 'PATH=%s\n' "$PATH"
command -v bash grep tee crc oc
# If installed in your base image, these should still resolve:
for program in java hadoop hive spark-submit kafka-topics.sh; do
  command -v "$program" || printf 'Check installation/PATH: %s\n' "$program"
done
```

### Validation 2: user runtime directory, bus, and daemon reload

Run this complete block in Bash. Each failed prerequisite stops the subshell. A successful `daemon-reload` normally prints nothing; it reloads user unit definitions and does not restart CRC or repair a missing bus.

```bash
(
  set -e
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
  export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
  echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
  echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
  test -d "$XDG_RUNTIME_DIR"
  test -O "$XDG_RUNTIME_DIR"
  test -S "$XDG_RUNTIME_DIR/bus"
  systemctl --user daemon-reload
  systemctl --user show-environment >/dev/null
  echo 'PASS: user bus reachable and daemon-reload succeeded'
)
```

If this fails after cloning, log out completely and log in directly as the VM user using SSH or the VM console (avoid `sudo su` as a substitute for login). On this Ubuntu lab image, if the user bus still does not exist, run:

```bash
sudo apt-get install -y dbus-user-session libpam-systemd
sudo systemctl start "user@$(id -u).service"
```

Then sign out, sign in, reload `.bashrc`, and repeat validation 2. Inspect failures with:

```bash
loginctl user-status "$USER"
systemctl status "user@$(id -u).service" --no-pager
sudo journalctl -b -u "user@$(id -u).service" --no-pager -n 50
```

Only if user services must survive logout, enable lingering explicitly with `sudo loginctl enable-linger "$USER"`; verify with `loginctl show-user "$USER" -p Linger`. Do not create `/run/user` directories or bus sockets by hand. `sudo systemctl daemon-reload` addresses the system manager and cannot replace `systemctl --user daemon-reload`.

### Validation 3: CRC, client, and cluster

```bash
command -v crc
command -v oc
crc version
oc version --client
# Run cluster checks only if setup succeeds.
if okd-start; then
  printf 'KUBECONFIG=%s\n' "$KUBECONFIG"
  test -s "$KUBECONFIG" && ls -l "$KUBECONFIG"
  oc whoami
  oc project
  oc get nodes
  oc get pods -n bigdata
fi
```

Expect the `bigdata` project and one `Ready` node after startup settles. A working user bus does not prove the CRC VM or Kubernetes API is healthy.

Systemd references: [pam_systemd session/runtime directory](https://www.freedesktop.org/software/systemd/man/251/pam_systemd.html), [systemctl daemon-reload](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html), [loginctl lingering](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html).
