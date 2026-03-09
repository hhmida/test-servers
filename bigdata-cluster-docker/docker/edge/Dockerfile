# ════════════════════════════════════════════════════════════════
# edge – NiFi, Phoenix QueryServer, Prometheus, Grafana, Cockpit
# ════════════════════════════════════════════════════════════════
FROM bigdata/base

LABEL description="BigData edge node: NiFi + Phoenix + Prometheus + Grafana"

ARG NIFI_VERSION=1.25.0
ARG PHOENIX_VERSION=5.1.3
ARG HBASE_VERSION=2.5.8
ARG HADOOP_VERSION=3.3.6
ARG PROMETHEUS_VERSION=2.51.0
ARG GRAFANA_VERSION=10.3.3
ARG APACHE_MIRROR=https://archive.apache.org/dist

ENV NIFI_HOME=/opt/bigdata/nifi
ENV PHOENIX_HOME=/opt/bigdata/phoenix
ENV HBASE_HOME=/opt/bigdata/hbase
ENV HADOOP_HOME=/opt/bigdata/hadoop
ENV PATH=$PATH:$NIFI_HOME/bin:$PHOENIX_HOME/bin:$HBASE_HOME/bin:$HADOOP_HOME/bin

# ─── Dépendances Grafana ─────────────────────────────────────────
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        software-properties-common \
        adduser libfontconfig1 \
        musl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── Téléchargements ─────────────────────────────────────────────
RUN set -ex && cd /tmp && \
    # Hadoop client
    wget -q ${APACHE_MIRROR}/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hadoop-${HADOOP_VERSION} ${HADOOP_HOME} && \
    # HBase client (pour Phoenix)
    wget -q ${APACHE_MIRROR}/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-bin.tar.gz && \
    tar -xzf hbase-${HBASE_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/hbase-${HBASE_VERSION} ${HBASE_HOME} && \
    # NiFi
    wget -q ${APACHE_MIRROR}/nifi/${NIFI_VERSION}/nifi-${NIFI_VERSION}-bin.zip && \
    unzip -q nifi-${NIFI_VERSION}-bin.zip -d /opt/bigdata/ && \
    ln -s /opt/bigdata/nifi-${NIFI_VERSION} ${NIFI_HOME} && \
    # Phoenix QueryServer
    wget -q ${APACHE_MIRROR}/phoenix/phoenix-${PHOENIX_VERSION}/phoenix-hbase-2.5-${PHOENIX_VERSION}-bin.tar.gz && \
    tar -xzf phoenix-hbase-2.5-${PHOENIX_VERSION}-bin.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/phoenix-hbase-2.5-${PHOENIX_VERSION}-bin ${PHOENIX_HOME} || true && \
    # Prometheus
    wget -q https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz && \
    tar -xzf prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz -C /opt/bigdata/ && \
    ln -s /opt/bigdata/prometheus-${PROMETHEUS_VERSION}.linux-amd64 /opt/bigdata/prometheus && \
    # node_exporter
    wget -q https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz && \
    tar -xzf node_exporter-1.8.0.linux-amd64.tar.gz -C /opt/bigdata/ && \
    ln -sf /opt/bigdata/node_exporter-1.8.0.linux-amd64/node_exporter /usr/local/bin/node_exporter && \
    # Grafana via .deb
    wget -q https://dl.grafana.com/oss/release/grafana_${GRAFANA_VERSION}_amd64.deb && \
    apt-get install -y ./grafana_${GRAFANA_VERSION}_amd64.deb && \
    systemctl enable grafana-server && \
    # Propriétaire
    chown -R hadoop:hadoop /opt/bigdata && \
    rm -f /tmp/*.tar.gz /tmp/*.tgz /tmp/*.zip /tmp/*.deb

# ─── Répertoires NiFi ────────────────────────────────────────────
RUN mkdir -p /data/nifi/{content_repository,flowfile_repository,provenance_repository} && \
    chown -R hadoop:hadoop /data/nifi && \
    mkdir -p /data/prometheus && \
    chown hadoop:hadoop /data/prometheus

# ─── Profils env ─────────────────────────────────────────────────
RUN printf "export NIFI_HOME=%s\nexport PHOENIX_HOME=%s\nexport HBASE_HOME=%s\nexport HADOOP_HOME=%s\nexport PATH=\$PATH:\$NIFI_HOME/bin:\$PHOENIX_HOME/bin:\$HBASE_HOME/bin:\$HADOOP_HOME/bin\n" \
        "$NIFI_HOME" "$PHOENIX_HOME" "$HBASE_HOME" "$HADOOP_HOME" > /etc/profile.d/bigdata.sh && \
    chmod +x /etc/profile.d/bigdata.sh

# ─── Ports ───────────────────────────────────────────────────────
# NiFi         : 8080, 8443
# Phoenix QS   : 8765
# Prometheus   : 9090
# Grafana      : 3000
# Cockpit      : 9090 (partagé avec Prometheus → remappé dans compose)
EXPOSE 22 8080 8443 8765 9095 3000 9090

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/sbin/init"]
