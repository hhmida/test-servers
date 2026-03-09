# ════════════════════════════════════════════════════════════════
# master2 – Secondary NN, HiveServer2, HBase Master, Atlas, Ranger
# ════════════════════════════════════════════════════════════════
FROM bigdata/base

LABEL description="BigData master2: Secondary NN + Hive + HBase Master + Atlas + Ranger"

ARG HADOOP_VERSION=3.3.6
ARG HIVE_VERSION=3.1.3
ARG HBASE_VERSION=2.5.8
ARG ATLAS_VERSION=2.3.0
ARG RANGER_VERSION=2.4.0
ARG APACHE_MIRROR=https://archive.apache.org/dist

ENV HADOOP_HOME=/opt/bigdata/hadoop
ENV HIVE_HOME=/opt/bigdata/hive
ENV HBASE_HOME=/opt/bigdata/hbase
ENV ATLAS_HOME=/opt/bigdata/atlas
ENV RANGER_HOME=/opt/bigdata/ranger-admin
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$HBASE_HOME/bin

# ─── Dépendances supplémentaires ─────────────────────────────────
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        python3-dev gcc g++ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── Téléchargements ─────────────────────────────────────────────
RUN set -ex && cd /tmp && \
    # Hadoop (client + secondary NN)
    wget -q ${APACHE_MIRROR}/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hadoop-${HADOOP_VERSION} ${HADOOP_HOME} && \
    # Hive
    wget -q ${APACHE_MIRROR}/hive/hive-${HIVE_VERSION}/apache-hive-${HIVE_VERSION}-bin.tar.gz && \
    tar -xzf apache-hive-${HIVE_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/apache-hive-${HIVE_VERSION}-bin ${HIVE_HOME} && \
    # HBase
    wget -q ${APACHE_MIRROR}/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-bin.tar.gz && \
    tar -xzf hbase-${HBASE_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hbase-${HBASE_VERSION} ${HBASE_HOME} && \
    # Atlas
    wget -q ${APACHE_MIRROR}/atlas/${ATLAS_VERSION}/apache-atlas-${ATLAS_VERSION}-server.tar.gz && \
    tar -xzf apache-atlas-${ATLAS_VERSION}-server.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/apache-atlas-${ATLAS_VERSION}-server ${ATLAS_HOME} || true && \
    # Ranger Admin
    mkdir -p /opt/bigdata/ranger && \
    wget -q ${APACHE_MIRROR}/ranger/${RANGER_VERSION}/apache-ranger-${RANGER_VERSION}-admin.tar.gz && \
    tar -xzf apache-ranger-${RANGER_VERSION}-admin.tar.gz -C /opt/bigdata/ranger/ || true && \
    # Propriétaire
    chown -R hadoop:hadoop /opt/bigdata && \
    rm -f /tmp/*.tar.gz /tmp/*.tgz

# ─── Profils env ─────────────────────────────────────────────────
RUN printf "export HADOOP_HOME=%s\nexport HIVE_HOME=%s\nexport HBASE_HOME=%s\nexport ATLAS_HOME=%s\nexport PATH=\$PATH:\$HADOOP_HOME/bin:\$HIVE_HOME/bin:\$HBASE_HOME/bin\n" \
        "$HADOOP_HOME" "$HIVE_HOME" "$HBASE_HOME" "$ATLAS_HOME" > /etc/profile.d/bigdata.sh && \
    chmod +x /etc/profile.d/bigdata.sh

# ─── Ports ───────────────────────────────────────────────────────
# HDFS Secondary NN : 9868
# Hive Metastore    : 9083
# HiveServer2       : 10000, 10002
# HBase Master      : 16000, 16010
# Atlas             : 21000
# Ranger Admin      : 6080
EXPOSE 22 9868 9083 10000 10002 16000 16010 21000 6080 9090

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/sbin/init"]
