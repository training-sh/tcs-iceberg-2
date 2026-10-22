FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jdk-headless python3 curl ca-certificates procps bash \
    && ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")" /opt/java \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/opt/java \
    SPARK_HOME=/opt/spark \
    PYSPARK_PYTHON=/usr/bin/python3 \
    PYSPARK_DRIVER_PYTHON=/usr/bin/python3
ENV PATH="${SPARK_HOME}/bin:${JAVA_HOME}/bin:${PATH}"

# Spark 3.5.9, Hadoop 3 client libraries, Scala 2.12.
RUN cd /tmp \
    && curl -fL --retry 3 -O https://archive.apache.org/dist/spark/spark-3.5.9/spark-3.5.9-bin-hadoop3.tgz \
    && curl -fL --retry 3 -O https://archive.apache.org/dist/spark/spark-3.5.9/spark-3.5.9-bin-hadoop3.tgz.sha512 \
    && sha512sum -c spark-3.5.9-bin-hadoop3.tgz.sha512 \
    && tar -xzf spark-3.5.9-bin-hadoop3.tgz -C /opt \
    && mv /opt/spark-3.5.9-bin-hadoop3 /opt/spark \
    && rm spark-3.5.9-bin-hadoop3.tgz spark-3.5.9-bin-hadoop3.tgz.sha512

# Run bash download-jars.sh on the VM before building.
COPY jars/*.jar /opt/spark/jars/
COPY entrypoint.sh /usr/local/bin/spark-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/spark-entrypoint.sh \
    && chmod +x /usr/local/bin/spark-entrypoint.sh \
    && mkdir -p /opt/spark/work /opt/spark/data

WORKDIR /opt/spark
EXPOSE 7077 7078 8080 8081 4040
ENTRYPOINT ["/usr/local/bin/spark-entrypoint.sh"]
CMD ["master"]
