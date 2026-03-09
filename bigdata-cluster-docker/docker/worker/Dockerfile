# ════════════════════════════════════════════════════════════════
# worker – DataNode, NodeManager, Spark Worker, HBase RegionServer
# Image partagée entre worker1 et worker2.
# Le rôle de chaque instance est défini par Docker Compose + Ansible.
# ════════════════════════════════════════════════════════════════
FROM bigdata/base

LABEL description="BigData worker node: DataNode + NodeManager + Spark Worker + HBase RegionServer"

ARG HADOOP_VERSION=3.3.6
ARG SPARK_VERSION=3.5.1
ARG HBASE_VERSION=2.5.8
ARG APACHE_MIRROR=https://archive.apache.org/dist

ENV HADOOP_HOME=/opt/bigdata/hadoop
ENV SPARK_HOME=/opt/bigdata/spark
ENV HBASE_HOME=/opt/bigdata/hbase
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$HBASE_HOME/bin

# ─── Téléchargements ─────────────────────────────────────────────
RUN set -ex && cd /tmp && \
    # Hadoop
    wget -q ${APACHE_MIRROR}/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hadoop-${HADOOP_VERSION} ${HADOOP_HOME} && \
    # Spark Worker
    wget -q ${APACHE_MIRROR}/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/spark-${SPARK_VERSION}-bin-hadoop3 ${SPARK_HOME} && \
    # Iceberg jar
    wget -q -O ${SPARK_HOME}/jars/iceberg-spark-runtime.jar \
        https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar || true && \
    # HBase RegionServer
    wget -q ${APACHE_MIRROR}/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-bin.tar.gz && \
    tar -xzf hbase-${HBASE_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hbase-${HBASE_VERSION} ${HBASE_HOME} && \
    # Propriétaire
    chown -R hadoop:hadoop /opt/bigdata && \
    rm -f /tmp/*.tar.gz /tmp/*.tgz

# ─── Profils env ─────────────────────────────────────────────────
RUN printf "export HADOOP_HOME=%s\nexport SPARK_HOME=%s\nexport HBASE_HOME=%s\nexport PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$SPARK_HOME/bin:\$HBASE_HOME/bin\n" \
        "$HADOOP_HOME" "$SPARK_HOME" "$HBASE_HOME" > /etc/profile.d/bigdata.sh && \
    chmod +x /etc/profile.d/bigdata.sh

# ─── Répertoires HDFS DataDir ────────────────────────────────────
# En production, les volumes NVMe sont montés ici
RUN mkdir -p /data/hdfs/datanode /data/hdfs/datanode2 && \
    chown -R hadoop:hadoop /data/hdfs

# ─── Ports ───────────────────────────────────────────────────────
# HDFS DataNode   : 9864, 9866
# YARN NM WebUI   : 8042
# Spark Worker UI : 8081
# HBase RS        : 16020, 16030
EXPOSE 22 9864 9866 8042 8081 16020 16030 9090

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/sbin/init"]
