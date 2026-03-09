# Guide Docker – BigData Cluster

## Pourquoi systemd dans Docker ?

Les services Big Data (Hadoop, HBase, NiFi, etc.) sont tous gérés
comme des **services systemd** — exactement comme sur une VM.
Cela garantit :
- Compatibilité totale avec les rôles Ansible v2
- Redémarrage automatique en cas de crash (`Restart=on-failure`)
- Gestion unifiée via `systemctl` et **Cockpit**
- Comportement identique entre l'environnement Docker et la production vSphere

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                   Hôte Docker                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │            Docker Network bigdata-net        │   │
│  │            172.20.0.0/24                     │   │
│  │                                              │   │
│  │  master1:172.20.0.11  ←── Ansible (SSH:22)  │   │
│  │  master2:172.20.0.12                         │   │
│  │  worker1:172.20.0.21                         │   │
│  │  worker2:172.20.0.22                         │   │
│  │  edge   :172.20.0.31  ←── Ports publics      │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Volumes Docker :                                   │
│  bigdata-master1-namenode  (HDFS NameNode data)     │
│  bigdata-worker1-hdfs1     (DataNode data)          │
│  bigdata-edge-nifi         (NiFi repositories)      │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

## Cgroup v2 et systemd

Docker + systemd nécessite cgroup v2 et `--privileged`.
Vérification sur l'hôte :

```bash
# Vérifier cgroup v2
mount | grep cgroup2
# Doit retourner quelque chose comme :
# cgroup2 on /sys/fs/cgroup type cgroup2 ...

# Si absent (systèmes anciens) :
# Ajouter dans /etc/default/grub :
# GRUB_CMDLINE_LINUX="... systemd.unified_cgroup_hierarchy=1"
# Puis : sudo update-grub && sudo reboot
```

## Workflow complet

```bash
cd docker/

# 1. Construire les images (une fois)
make build

# 2. Démarrer
make up

# 3. Vérifier
make status

# 4. Distribuer les clés SSH (une fois)
make init-ssh

# 5. Tester Ansible
make ansible-ping

# 6. Déployer
make ansible-deploy

# 7. Initialiser HDFS
make hdfs-init

# Accéder à un nœud
make shell-m1    # master1
make shell-edge  # nœud edge
```

## Réinitialisation complète

```bash
# Arrêter et supprimer tout (conteneurs + volumes)
make clean

# Repartir de zéro
make build && make up && make init-ssh && make ansible-deploy && make hdfs-init
```

## Cas d'usage pédagogiques

### Snapshot d'état (docker commit)
```bash
# Sauvegarder l'état d'un conteneur après configuration
docker commit master1 bigdata/master1:configured-$(date +%Y%m%d)
docker commit master2 bigdata/master2:configured-$(date +%Y%m%d)
```

### Multi-étudiants simultanés
Chaque étudiant peut instancier son propre cluster en changeant le nom du projet :
```bash
COMPOSE_PROJECT_NAME=etudiant01 docker compose up -d
COMPOSE_PROJECT_NAME=etudiant02 docker compose up -d
```
Les ports sont différents si on utilise `--scale` ou des compose files adaptés.

### Reset d'un seul nœud
```bash
docker compose stop worker1
docker compose rm -f worker1
docker compose up -d worker1
# Puis re-provisionner avec Ansible
ansible-playbook -i ansible/inventories/hosts.ini ansible/site.yml \
  --limit worker1 --tags hadoop
```
