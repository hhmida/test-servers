# ════════════════════════════════════════════════════════════════
# BigData Base Image – Ubuntu 24.04 + systemd + SSH + Java 17
# Tous les nœuds du cluster héritent de cette image.
# ════════════════════════════════════════════════════════════════
FROM ubuntu:24.04

LABEL maintainer="bigdata-cluster"
LABEL description="Base image for BigData cluster nodes – Ubuntu 24.04 + systemd"

# ─── Évite les prompts interactifs apt ───────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV container=docker
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ─── Java 17 home (Ubuntu 24.04) ─────────────────────────────────
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

# ─── Hadoop user / install dirs ──────────────────────────────────
ENV HADOOP_USER=hadoop
ENV INSTALL_DIR=/opt/bigdata
ENV DATA_DIR=/data

# ─── 1. Packages système + systemd ───────────────────────────────
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        # systemd (PID 1 dans le conteneur)
        systemd \
        systemd-sysv \
        dbus \
        # SSH (requis par Ansible)
        openssh-server \
        openssh-client \
        # Java
        openjdk-17-jdk \
        # Outils de base
        curl wget vim git unzip zip \
        net-tools iproute2 iputils-ping \
        ntp \
        rsync \
        jq \
        htop \
        lsof \
        procps \
        # Python (Ansible)
        python3 python3-pip python3-venv \
        # Cockpit (natif Ubuntu 24)
        cockpit \
        cockpit-system \
        cockpit-storaged \
        cockpit-networkmanager \
        # Divers
        sudo \
        locales \
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ─── 2. Désactiver les services systemd inutiles en conteneur ─────
RUN systemctl mask \
        dev-hugepages.mount \
        sys-fs-fuse-connections.mount \
        systemd-update-utmp.service \
        getty.target \
        console-getty.service \
        systemd-logind.service \
    2>/dev/null || true && \
    # Désactiver NetworkManager (réseau géré par Docker)
    systemctl disable NetworkManager 2>/dev/null || true && \
    # Activer SSH
    systemctl enable ssh && \
    # Activer Cockpit
    systemctl enable cockpit.socket

# ─── 3. Paramètres sysctl ────────────────────────────────────────
# (appliqués à l'hôte Docker, donc commentés ici – gérés par Ansible)
RUN echo "# sysctl managed by Ansible" > /etc/sysctl.d/bigdata.conf

# ─── 4. Utilisateur hadoop ───────────────────────────────────────
RUN groupadd -f hadoop && \
    useradd -m -s /bin/bash -g hadoop hadoop && \
    echo "hadoop:Hadoop@2024!" | chpasswd && \
    echo "hadoop ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/hadoop && \
    chmod 440 /etc/sudoers.d/hadoop && \
    usermod -aG sudo hadoop

# ─── 5. Clés SSH Hadoop ──────────────────────────────────────────
RUN mkdir -p /home/hadoop/.ssh && \
    chmod 700 /home/hadoop/.ssh && \
    ssh-keygen -t rsa -b 4096 -N "" -f /home/hadoop/.ssh/id_rsa && \
    cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys && \
    chmod 600 /home/hadoop/.ssh/authorized_keys && \
    chown -R hadoop:hadoop /home/hadoop/.ssh && \
    # SSH config : StrictHostKeyChecking off pour le cluster
    printf "Host 172.20.0.*\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null\nHost master1 master2 worker1 worker2 edge\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null\n" \
        > /home/hadoop/.ssh/config && \
    chmod 600 /home/hadoop/.ssh/config && \
    chown hadoop:hadoop /home/hadoop/.ssh/config

# ─── 6. Configuration SSH serveur ────────────────────────────────
RUN mkdir -p /run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    echo "AllowUsers hadoop root" >> /etc/ssh/sshd_config

# ─── 7. Répertoires Big Data ─────────────────────────────────────
RUN mkdir -p \
        ${INSTALL_DIR} \
        ${DATA_DIR}/hdfs/namenode \
        ${DATA_DIR}/hdfs/datanode \
        ${DATA_DIR}/hdfs/secondary \
        ${DATA_DIR}/zookeeper \
        ${DATA_DIR}/kafka/logs \
        ${DATA_DIR}/nifi \
        ${DATA_DIR}/prometheus \
        /var/log/bigdata \
        /var/run/bigdata && \
    chown -R hadoop:hadoop ${INSTALL_DIR} ${DATA_DIR} \
        /var/log/bigdata /var/run/bigdata

# ─── 8. Profil Java / hadoop ─────────────────────────────────────
RUN printf "export JAVA_HOME=%s\nexport PATH=\$PATH:\$JAVA_HOME/bin\n" \
        "$JAVA_HOME" > /etc/profile.d/java.sh && \
    chmod +x /etc/profile.d/java.sh

# ─── 9. Désactiver le swap (signalé à Hadoop via conf) ───────────
RUN echo "vm.swappiness=1" >> /etc/sysctl.d/bigdata.conf

# ─── 10. Limits fichiers pour hadoop ─────────────────────────────
RUN printf "hadoop soft nofile 1048576\nhadoop hard nofile 1048576\nhadoop soft nproc 131072\nhadoop hard nproc 131072\n* soft nofile 65536\n* hard nofile 65536\n" \
        >> /etc/security/limits.conf && \
    echo "session required pam_limits.so" >> /etc/pam.d/common-session

# ─── 11. Copier le script d'entrypoint ───────────────────────────
COPY scripts/entrypoint.sh /entrypoint.sh
COPY scripts/setup_ssh.sh  /setup_ssh.sh
RUN chmod +x /entrypoint.sh /setup_ssh.sh

# ─── Volumes pour persistence ────────────────────────────────────
VOLUME ["/sys/fs/cgroup", "/data", "/opt/bigdata"]

# ─── Port SSH ─────────────────────────────────────────────────────
EXPOSE 22 9090

# ─── Systemd comme PID 1 ─────────────────────────────────────────
STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/sbin/init"]
