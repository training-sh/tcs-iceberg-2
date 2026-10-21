# Bash configuration for the cloned course VM

The instructor and student VMs share the same base image. The complete replacement block below is based on the instructor VM's `.bashrc`. It preserves the shell prompt, aliases, Python virtual environment, Java, Hadoop, Hive, Spark, Kafka, Airflow, classroom S3 settings, and OKD helpers.

**Copy/paste note:** earlier instructions copied from Jupyter-rendered notebook Markdown introduced special characters or formatting into `.bashrc`. Copy only the contents of the fenced Bash blocks below using GitHub's copy button. Do not copy rendered prose, JSON, Markdown fences, prompts, or smart quotes into the shell configuration.

## Step 1: replace the entire `.bashrc`

**This step overwrites the whole file**, not only the marked OKD section. It is intended for the supplied cloned course VMs. Run as the ordinary VM login user in an interactive Bash terminal. No separate script or download is required. First run the backup block, then paste the entire replacement block, including its final `EOF` line.

Back up the current configuration first.

```bash
cp -p "$HOME/.bashrc" "$HOME/.bashrc.before-course.$(date +%Y%m%d-%H%M%S).bak"
```

Replace the entire file with the following block. The quoted `EOF` keeps `$HOME`, `$PATH`, quotes, and command substitutions literal while writing; they are evaluated only when Bash loads `.bashrc`. Keep the opening `tee` line and the closing `EOF` together when copying.

```bash
tee "$HOME/.bashrc" > /dev/null <<'EOF'
# ~/.bashrc: executed by bash(1) for non-login shells.

# ============================================================
# Interactive shell check
# ============================================================

case $- in
    *i*) ;;
      *) return ;;
esac

# ============================================================
# Bash history
# ============================================================

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s checkwinsize

# ============================================================
# lesspipe
# ============================================================

[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# ============================================================
# Chroot detection
# ============================================================

if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# ============================================================
# Terminal prompt support
# ============================================================

case "$TERM" in
    xterm-color|*-256color)
        color_prompt=yes
        ;;
esac

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        color_prompt=yes
    else
        color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi

unset color_prompt force_color_prompt

# ============================================================
# XTerm title
# ============================================================

case "$TERM" in
    xterm*|rxvt*)
        PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
        ;;
esac

# ============================================================
# Colors and aliases
# ============================================================

if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors \
        && eval "$(dircolors -b ~/.dircolors)" \
        || eval "$(dircolors -b)"

    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history | tail -n1 | sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# ============================================================
# User aliases
# ============================================================

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# ============================================================
# Bash completion
# ============================================================

if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

# ============================================================
# Data Engineering Python Environment
# ============================================================

if [ -f "$HOME/dataengenv/bin/activate" ]; then
    source "$HOME/dataengenv/bin/activate"
fi

# ============================================================
# Java
# ============================================================

# Keep repeated sourcing from duplicating tool directories in PATH.
_lab_path_prepend() {
    case ":$PATH:" in *":$1:"*) ;; *) export PATH="$1:$PATH" ;; esac
}
_lab_path_append() {
    case ":$PATH:" in *":$1:"*) ;; *) export PATH="$PATH:$1" ;; esac
}

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# ============================================================
# Hadoop
# ============================================================

export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
_lab_path_append "$HADOOP_HOME/bin"
_lab_path_append "$HADOOP_HOME/sbin"

# ============================================================
# Apache Hive
# ============================================================

export HIVE_HOME=/opt/hive
export HIVE_CONF_DIR="$HIVE_HOME/conf"
_lab_path_append "$HIVE_HOME/bin"

# ============================================================
# Apache Spark
# ============================================================

export SPARK_HOME=/opt/spark
_lab_path_prepend "$SPARK_HOME/sbin"
_lab_path_prepend "$SPARK_HOME/bin"

export PYSPARK_PYTHON="$HOME/dataengenv/bin/python"
export PYSPARK_DRIVER_PYTHON="$HOME/dataengenv/bin/python"

case ":${PYTHONPATH:-}:" in
    *":$SPARK_HOME/python:"*) ;;
    *) export PYTHONPATH="$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip${PYTHONPATH:+:$PYTHONPATH}" ;;
esac

# ============================================================
# Apache Kafka
# ============================================================

export KAFKA_HOME=/opt/kafka
_lab_path_append "$KAFKA_HOME/bin"

# ============================================================
# Apache Airflow 3.3.1
# ============================================================

export AIRFLOW_HOME="$HOME/training/airflow"

export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="mysql+mysqldb://airflow:airflow123@localhost:3306/airflow_db"

export AIRFLOW__API__HOST="127.0.0.1"
export AIRFLOW__API__PORT="8080"

export AIRFLOW__CORE__TEST_CONNECTION="Enabled"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS="True"
export AIRFLOW__CORE__LOAD_EXAMPLES="False"

# Optional Nginx reverse proxy:
# export AIRFLOW_FQDN="$(hostname -f)"
# export AIRFLOW__API__BASE_URL="https://${AIRFLOW_FQDN}/airflow"
# export AIRFLOW__CORE__EXECUTION_API_SERVER_URL="https://${AIRFLOW_FQDN}/airflow/execution/"

# ============================================================
# AWS / S3 Lab
# ============================================================

export AWS_ACCESS_KEY_ID="team"
export AWS_SECRET_ACCESS_KEY="team1234"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_PAGER=""
# Host-side S3 API; start the SeaweedFS forward from lesson 15 first.
export S3_ENDPOINT="http://127.0.0.1:19001"

# ============================================================
# Apache Polaris
# ============================================================

export POLARIS_URL="http://127.0.0.1:18181"

# ============================================================
# OKD / OpenShift Local - CRC
# ============================================================
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

# ============================================================
# Prompt
# ============================================================

PS1='\[\e[34m\]\w\[\e[0m\] \$ '

# BEGIN CRC PATH
_lab_path_prepend "$HOME/.crc/bin/oc"
_lab_path_prepend "$HOME/.local/bin"
# END CRC PATH

unset -f _lab_path_prepend _lab_path_append
EOF
```

Load the replacement in this interactive Bash terminal.

```bash
bash -n "$HOME/.bashrc" && source "$HOME/.bashrc"
```

The replacement keeps the image's `/opt/hadoop`, `/opt/hive`, `/opt/spark`, `/opt/kafka`, and Java 11 paths. User-specific paths use `$HOME`, including `dataengenv`, so a cloned VM does not depend on the instructor's account name. The host-side tool settings do not change the environment inside Kubernetes containers.

The corrected `okd-env` refreshes the CRC administrator kubeconfig, accepts both `OKD: Running` and `OpenShift: Running`, and selects `bigdata`. It does not start CRC automatically. Use `okd-start` when the cluster is stopped.

## Append the remaining setup blocks

The following blocks can be added at the end. Marker checks prevent duplicate additions. The replacement block already contains the CRC PATH section, so addition 2 safely skips it. Addition 3 supplies the current login user's systemd session environment when available.

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

## Environment settings checked on the instructor VM

All configured Java, Hadoop, Hive, Spark, Kafka, Python virtual-environment, and CRC paths existed when checked. The replacement retains those settings; no extra global Hadoop or Hive variables are required for the Kubernetes lessons.

The replacement adds `AWS_PAGER=""` for terminal output and sets host-side `S3_ENDPOINT=http://127.0.0.1:19001` and `POLARIS_URL=http://127.0.0.1:18181` to match lessons 15?16. These URLs work only while their port-forwards run. Jupyter kernels inside the pod use the deployment's Service endpoints, not these VM loopback addresses.

Do not set `HOME=/workspace`, `NOTEBOOK_DIR=/workspace/notebooks`, or a fixed `OKD_CONTEXT` globally in the VM `.bashrc`. `/workspace` belongs to the Jupyter container, and context names can differ between clones. Use `/workspace/notebooks` through Jupyter as explained in [17-0-Jupyter.md](01-GetStarted/17-0-Jupyter.md).
