# 🐳 BigData Cluster – Version Docker (v3)

> Adaptation de la v2 (vSphere + Packer) vers **Docker Compose**.
> Les mêmes rôles Ansible provisionnent les conteneurs via SSH,
> exactement comme des VMs.

---

## 1. Architecture des conteneurs

| Conteneur | Image           | RAM limit | CPU | IP             | Services |
|-----------|-----------------|-----------|-----|----------------|----------|
| master1   | bigdata/master1 | 28 GB     | 8   | 172.20.0.11    | NameNode, ResourceManager, Spark Master, ZooKeeper, Kafka |
| master2   | bigdata/master2 | 26 GB     | 8   | 172.20.0.12    | Secondary NN, HiveServer2, Metastore, HBase Master, Atlas, Ranger |
| worker1   | bigdata/worker  | 28 GB     | 8   | 172.20.0.21    | DataNode (EC), NodeManager, Spark Worker, HBase RegionServer |
| worker2   | bigdata/worker  | 28 GB     | 8   | 172.20.0.22    | DataNode (EC), NodeManager, Spark Worker, HBase RegionServer |
| edge      | bigdata/edge    | 16 GB     | 8   | 172.20.0.31    | NiFi, Phoenix, Prometheus, Grafana, Cockpit |

Réseau Docker : `bigdata-net` (bridge) — sous-réseau `172.20.0.0/24`

---

## 2. Prérequis

```bash
# Docker Engine ≥ 25 ou Docker Desktop ≥ 4.28
docker --version         # Docker version 25+
docker compose version   # Docker Compose version v2.24+

# Ressources recommandées sur l'hôte
# RAM : ≥ 64 GB (production) ou ≥ 32 GB (test avec limites réduites)
# CPU : ≥ 16 cœurs
# Disque : ≥ 100 GB

# Ansible ≥ 2.15 sur l'hôte
ansible --version
pip install ansible-core passlib
```

### Configuration Docker Engine (cgroups v2 + ressources)

```bash
# Vérifier cgroup v2 (requis pour systemd dans Docker)
cat /sys/fs/cgroup/cgroup.controllers
# Doit contenir : cpuset cpu io memory hugetlb pids rdma misc

# Sur Ubuntu 22/24 host : cgroup v2 est actif par défaut
# Sur CentOS/RHEL : ajouter systemd.unified_cgroup_hierarchy=1 dans GRUB

# Augmenter les limites inotify (requis pour Kafka/Elasticsearch)
echo "fs.inotify.max_user_watches=1048576" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_instances=512"   | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 3. Structure des fichiers

```
bigdata-cluster/
├── docker/
│   ├── base/
│   │   ├── Dockerfile           ← Image de base (systemd + SSH + Java 17)
│   │   └── scripts/
│   │       ├── entrypoint.sh    ← Démarre systemd comme PID 1
│   │       └── setup_ssh.sh     ← Configure SSH + clés hadoop
│   ├── master1/
│   │   └── Dockerfile           ← Pré-installe Hadoop, Spark, ZK, Kafka
│   ├── master2/
│   │   └── Dockerfile           ← Pré-installe Hadoop, Hive, HBase, Atlas, Ranger
│   ├── worker/
│   │   └── Dockerfile           ← Pré-installe Hadoop, Spark, HBase (worker1 ET worker2)
│   ├── edge/
│   │   └── Dockerfile           ← Pré-installe NiFi, Phoenix, Prometheus, Grafana
│   ├── docker-compose.yml       ← Orchestration complète
│   ├── .env                     ← Variables (versions, passwords)
│   └── Makefile                 ← Commandes pratiques
│
├── ansible/                     ← Identique à v2 (Ansible provisionne via SSH)
│   ├── inventories/
│   │   ├── hosts.ini            ← IPs Docker (172.20.0.x)
│   │   └── group_vars/
│   ├── roles/                   ← Tous les rôles v2 inchangés
│   └── site.yml
│
└── docs/
    ├── EC_ERASURE_CODING.md
    ├── COCKPIT_GUIDE.md
    └── RANGER_GUIDE.md
```

---

## 4. Démarrage rapide

### Étape 1 – Construire les images

```bash
cd docker/

# Construire toutes les images (ordre important : base en premier)
make build

# Ou manuellement :
docker build -t bigdata/base    -f base/Dockerfile    base/
docker build -t bigdata/master1 -f master1/Dockerfile .
docker build -t bigdata/master2 -f master2/Dockerfile .
docker build -t bigdata/worker  -f worker/Dockerfile  .
docker build -t bigdata/edge    -f edge/Dockerfile    .
```

### Étape 2 – Démarrer le cluster

```bash
# Démarrer tous les conteneurs
make up
# ou
docker compose up -d

# Vérifier que tout est démarré
docker compose ps
make status
```

### Étape 3 – Provisionner avec Ansible

```bash
# Depuis la racine du projet
cd ..

# Copier la clé SSH dans les conteneurs
make -C docker/ init-ssh

# Test de connectivité Ansible
ansible all -i ansible/inventories/hosts.ini -m ping

# Déploiement complet
ansible-playbook -i ansible/inventories/hosts.ini ansible/site.yml

# Déploiements ciblés
ansible-playbook -i ansible/inventories/hosts.ini ansible/site.yml --tags hadoop
ansible-playbook -i ansible/inventories/hosts.ini ansible/site.yml --tags erasure-coding
ansible-playbook -i ansible/inventories/hosts.ini ansible/site.yml --tags ranger
```

### Étape 4 – Initialiser HDFS

```bash
# Formatter le NameNode (première fois)
make hdfs-init

# Vérifier le cluster
make hdfs-status
make yarn-status
```

---

## 5. Commandes Makefile

```bash
make build        # Construire toutes les images Docker
make up           # Démarrer le cluster
make down         # Arrêter le cluster
make restart      # Redémarrer
make status       # État des conteneurs
make logs         # Logs de tous les services
make shell-m1     # Shell dans master1
make shell-m2     # Shell dans master2
make shell-w1     # Shell dans worker1
make shell-edge   # Shell dans edge
make hdfs-init    # Formater + démarrer HDFS (première fois)
make hdfs-status  # Rapport HDFS
make yarn-status  # État YARN
make clean        # Supprimer conteneurs + volumes
make ps           # docker compose ps
```

---

## 6. Interfaces Web

| Service         | URL                              | Login |
|-----------------|----------------------------------|-------|
| HDFS NameNode   | http://172.20.0.11:9870          | – |
| YARN            | http://172.20.0.11:8088          | – |
| Spark Master    | http://172.20.0.11:8080          | – |
| HBase Master    | http://172.20.0.12:16010         | – |
| HiveServer2     | http://172.20.0.12:10002         | – |
| Atlas           | http://172.20.0.12:21000         | admin/admin |
| Ranger Admin    | http://172.20.0.12:6080          | admin/RangerAdmin@2024! |
| NiFi            | http://172.20.0.31:8080/nifi     | – |
| Prometheus      | http://172.20.0.31:9090          | – |
| Grafana         | http://172.20.0.31:3000          | admin/admin |
| Cockpit master1 | https://172.20.0.11:9090         | hadoop/Hadoop@2024! |
| Cockpit edge    | https://172.20.0.31:9090         | hadoop/Hadoop@2024! |

---

## 7. Différences vs version vSphere (v2)

| Aspect              | vSphere v2                    | Docker v3                     |
|---------------------|-------------------------------|-------------------------------|
| Provisioning infra  | Packer → template vSphere     | Dockerfiles → images locales  |
| Isolation           | VMs complètes                 | Conteneurs (namespaces Linux) |
| PID 1               | init Ubuntu                   | systemd (--privileged)        |
| Réseau              | 192.168.10.0/24 (VMkernel)   | 172.20.0.0/24 (bridge Docker) |
| Stockage HDFS       | NVMe RDM passthrough          | Volumes Docker nommés         |
| Démarrage           | ~5 min (boot VMs)             | ~30 sec (conteneurs)          |
| Ansible             | Identique                     | Identique (SSH sur port 22)   |
| Ressources          | Physiques (128 GB RAM)        | Partagées (limits dans compose)|
| Usage pédagogique   | Prod-like, lent à rebuilder   | Rapide, reset en 1 commande   |

---

## 8. Dépannage fréquent

```bash
# Conteneur qui ne démarre pas
docker compose logs master1

# systemd ne démarre pas dans le conteneur
docker exec -it master1 journalctl -xeu ssh

# SSH refusé par Ansible
docker exec -it master1 systemctl status ssh

# Vérifier la clé SSH
docker exec master1 cat /home/hadoop/.ssh/authorized_keys

# Reset complet du cluster
make clean && make build && make up
```
