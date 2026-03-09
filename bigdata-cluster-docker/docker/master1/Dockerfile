# ════════════════════════════════════════════════════════════════
# master1 – NameNode, ResourceManager, Spark Master, ZooKeeper, Kafka
# ════════════════════════════════════════════════════════════════
FROM bigdata/base

LABEL description="BigData master1: NameNode + ResourceManager + Spark Master + ZooKeeper + Kafka"

ARG HADOOP_VERSION=3.3.6
ARG SPARK_VERSION=3.5.1
ARG KAFKA_VERSION=3.7.0
ARG SCALA_VERSION=2.13
ARG ZK_VERSION=3.8.4
ARG APACHE_MIRROR=https://archive.apache.org/dist

ENV HADOOP_HOME=/opt/bigdata/hadoop
ENV SPARK_HOME=/opt/bigdata/spark
ENV KAFKA_HOME=/opt/bigdata/kafka
ENV ZOOKEEPER_HOME=/opt/bigdata/zookeeper
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$SPARK_HOME/sbin:$KAFKA_HOME/bin:$ZOOKEEPER_HOME/bin

# ─── Téléchargement et installation des binaires ─────────────────
RUN set -ex && \
    cd /tmp && \
    # Hadoop
    wget -q ${APACHE_MIRROR}/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hadoop-${HADOOP_VERSION} ${HADOOP_HOME} && \
    # Spark
    wget -q ${APACHE_MIRROR}/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/spark-${SPARK_VERSION}-bin-hadoop3 ${SPARK_HOME} && \
    # Iceberg jar
    wget -q -O ${SPARK_HOME}/jars/iceberg-spark-runtime.jar \
        https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar || true && \
    # ZooKeeper
    wget -q ${APACHE_MIRROR}/zookeeper/zookeeper-${ZK_VERSION}/apache-zookeeper-${ZK_VERSION}-bin.tar.gz && \
    tar -xzf apache-zookeeper-${ZK_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/apache-zookeeper-${ZK_VERSION}-bin ${ZOOKEEPER_HOME} && \
    # Kafka
    wget -q ${APACHE_MIRROR}/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz && \
    tar -xzf kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/kafka_${SCALA_VERSION}-${KAFKA_VERSION} ${KAFKA_HOME} && \
    # Propriétaire
    chown -R hadoop:hadoop /opt/bigdata && \
    # Nettoyage
    rm -f /tmp/*.tar.gz /tmp/*.tgz

# ─── Profils d'environnement ──────────────────────────────────────
RUN printf "export HADOOP_HOME=%s\nexport PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin\n" "$HADOOP_HOME" > /etc/profile.d/hadoop.sh && \
    printf "export SPARK_HOME=%s\nexport PATH=\$PATH:\$SPARK_HOME/bin:\$SPARK_HOME/sbin\n" "$SPARK_HOME" >> /etc/profile.d/hadoop.sh && \
    printf "export KAFKA_HOME=%s\nexport PATH=\$PATH:\$KAFKA_HOME/bin\n" "$KAFKA_HOME"     >> /etc/profile.d/hadoop.sh && \
    printf "export ZOOKEEPER_HOME=%s\nexport PATH=\$PATH:\$ZOOKEEPER_HOME/bin\n" "$ZOOKEEPER_HOME" >> /etc/profile.d/hadoop.sh && \
    chmod +x /etc/profile.d/hadoop.sh

# ─── Ports exposés ────────────────────────────────────────────────
# HDFS NameNode : 9000, 9870
# YARN RM       : 8032, 8088
# Spark Master  : 7077, 8080
# ZooKeeper     : 2181
# Kafka         : 9092
# MapReduce JH  : 10020, 19888
EXPOSE 22 9000 9870 8032 8088 7077 8080 2181 9092 10020 19888 9090

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/sbin/init"]
