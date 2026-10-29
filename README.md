# Git Clone for all machines

```
sudo tailscale down
sudo systemctl disable --now tailscaled
sudo apt purge -y tailscale
```


# CRC Memory Adjustment

```
crc stop
crc config set memory 18432
crc start
```


Baseline your commands from the cloned directory

```
cd ~
git clone https://github.com/training-sh/tcs-iceberg-2

cd tcs-iceberg-2
```

# IceBerg Trino Spark

# for any code sharing, link sharing

https://codepad.pro/pad/IBd6pJ_iW7VX


## Chrome

 Download latest Google Chrome .deb
```
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
```

 Install
```
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```
 Remove downloaded installer
```
rm google-chrome-stable_current_amd64.deb
```

OpenShift data engineering training guides and lessons.

Code share

https://codepad.pro/pad/IBd6pJ_iW7VX



## Course index

Start with [00 - Introduction](00-Introduction/README.md), in this order:

1. [00 - Bash configuration](00-bashrc.md): full cloned-VM shell configuration and validation; apply after CRC installation.
2. [00 - Installation](00-Introduction/00-Installation.md): CRC installation and cluster operations.
3. [01 - CRC commands](00-Introduction/01-CRC-Commands.md): cluster lifecycle and configuration.
4. [02 - OpenShift oc commands](00-Introduction/02-OC-Commands.md): workloads and troubleshooting.
5. [03 - Architecture](00-Introduction/03-Architecture.md): illustrated platform guide.

Continue with [01 - Getting started](01-GetStarted/README.md):

1. [10 - HDFS](01-GetStarted/10-hdfs-openshift.md)
2. [11 - YARN](01-GetStarted/11-yarn-openshift.md)
3. [12 - Spark master](01-GetStarted/12-spark-master-openshift.md)
4. [13 - Spark submit](01-GetStarted/13-spark-submit-openshift.md)
5. [14 - Hive](01-GetStarted/14-hive-openshift.md)
6. [15 - SeaweedFS S3](01-GetStarted/15-seaweedfs.md)
7. [16 - Polaris and Iceberg](01-GetStarted/16-polaris.md)
8. [17-0 - Jupyter operations](01-GetStarted/17-0-Jupyter.md)
9. [17-1 - PySpark integration notebook](01-GetStarted/17-1-pyspark.ipynb)

## Reference presentation

- [Red Hat OpenShift: Innovation without limitation (PDF)](https://people.redhat.com/bhinson/presentations/openshift/Red-Hat-OpenShift--Innovation-without-limitation.pdf)
