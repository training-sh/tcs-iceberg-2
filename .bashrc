tee "$HOME/.bashrc" >/dev/null <<'EOF'
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

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# ============================================================
# Hadoop
# ============================================================

export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
export PATH="$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin"

# ============================================================
# Apache Hive
# ============================================================

export HIVE_HOME=/opt/hive
export HIVE_CONF_DIR="$HIVE_HOME/conf"
export PATH="$PATH:$HIVE_HOME/bin"

# ============================================================
# Apache Spark
# ============================================================

export SPARK_HOME=/opt/spark
export PATH="$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH"

export PYSPARK_PYTHON="$HOME/dataengenv/bin/python"
export PYSPARK_DRIVER_PYTHON="$HOME/dataengenv/bin/python"

export PYTHONPATH="$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip${PYTHONPATH:+:$PYTHONPATH}"

# ============================================================
# Apache Kafka
# ============================================================

export KAFKA_HOME=/opt/kafka
export PATH="$PATH:$KAFKA_HOME/bin"

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

# ============================================================
# Apache Polaris
# ============================================================

export POLARIS_URL="http://localhost:8181"

# ============================================================
# OKD / OpenShift Local - CRC
# ============================================================
# BEGIN OKD LAB

export KUBECONFIG="$HOME/.kube/crc-admin.kubeconfig"

okd-env() {
    local crc_state

    if ! crc_state="$(crc status 2>&1)"; then
        printf '%s\n' "$crc_state" >&2
        echo "Cannot read CRC status. Check libvirt access, then run: okd-start" >&2
        return 1
    fi

    if ! grep -Eq '^OpenShift:[[:space:]]+Running' <<< "$crc_state"; then
        echo "OKD is stopped. Run: okd-start" >&2
        return 1
    fi

    eval "$(crc oc-env)"

    mkdir -p "$HOME/.kube"

    if [[ ! -s "$HOME/.crc/machines/crc/kubeconfig" ]]; then
        echo "CRC kubeconfig was not found. Run: okd-start" >&2
        return 1
    fi

    cp "$HOME/.crc/machines/crc/kubeconfig" "$KUBECONFIG"
    chmod 600 "$KUBECONFIG"

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
EOF
