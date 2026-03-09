# ════════════════════════════════════════════════════════════════
# BigData Cluster – Makefile
# Usage : make <target>
# ════════════════════════════════════════════════════════════════

COMPOSE     = docker compose
ANSIBLE_INV = ../ansible/inventories/hosts.ini
HADOOP_EXEC = docker exec -u hadoop master1 /opt/bigdata/hadoop/bin

.PHONY: help build up down restart clean status logs \
        shell-m1 shell-m2 shell-w1 shell-w2 shell-edge \
        hdfs-init hdfs-status yarn-status ec-status \
        ansible-ping ansible-deploy init-ssh ps pull

# ─── Aide ────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  🐳 BigData Cluster – Commandes disponibles"
	@echo "  ─────────────────────────────────────────────"
	@echo "  make build        Construire toutes les images"
	@echo "  make up           Démarrer le cluster"
	@echo "  make down         Arrêter le cluster"
	@echo "  make restart      Redémarrer"
	@echo "  make status       État de chaque conteneur"
	@echo "  make logs         Logs en temps réel"
	@echo "  make clean        Tout supprimer (conteneurs + volumes)"
	@echo ""
	@echo "  make init-ssh     Distribuer les clés SSH entre conteneurs"
	@echo "  make ansible-ping Tester la connectivité Ansible"
	@echo "  make ansible-deploy Déployer avec Ansible (site.yml)"
	@echo ""
	@echo "  make hdfs-init    Formatter HDFS + activer Erasure Coding"
	@echo "  make hdfs-status  Rapport HDFS"
	@echo "  make yarn-status  Nœuds YARN"
	@echo "  make ec-status    Politiques Erasure Coding"
	@echo ""
	@echo "  make shell-m1     Shell dans master1"
	@echo "  make shell-m2     Shell dans master2"
	@echo "  make shell-w1     Shell dans worker1"
	@echo "  make shell-w2     Shell dans worker2"
	@echo "  make shell-edge   Shell dans edge"
	@echo ""

# ─── Images ──────────────────────────────────────────────────────
build:
	@echo "🔨 Construction de l'image de base..."
	docker build -t bigdata/base -f base/Dockerfile base/
	@echo "🔨 Construction des images des nœuds..."
	docker build -t bigdata/master1 -f master1/Dockerfile .
	docker build -t bigdata/master2 -f master2/Dockerfile .
	docker build -t bigdata/worker  -f worker/Dockerfile  .
	docker build -t bigdata/edge    -f edge/Dockerfile    .
	@echo "✅ Toutes les images construites."

pull:
	docker pull ubuntu:24.04

# ─── Cycle de vie ────────────────────────────────────────────────
up:
	@echo "🚀 Démarrage du cluster BigData..."
	$(COMPOSE) up -d
	@echo "✅ Cluster démarré. Attendez ~30s puis : make status"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

ps:
	$(COMPOSE) ps

status:
	@echo ""
	@echo "═══ Conteneurs BigData ════════════════════════════════"
	$(COMPOSE) ps
	@echo ""
	@echo "═══ Réseau bigdata-net ═════════════════════════════════"
	docker network inspect bigdata-net --format \
		'{{range .Containers}}  {{.Name}} → {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || true

logs:
	$(COMPOSE) logs -f --tail=50

# ─── Shells ──────────────────────────────────────────────────────
shell-m1:
	docker exec -it -u hadoop master1 bash

shell-m2:
	docker exec -it -u hadoop master2 bash

shell-w1:
	docker exec -it -u hadoop worker1 bash

shell-w2:
	docker exec -it -u hadoop worker2 bash

shell-edge:
	docker exec -it -u hadoop edge bash

# ─── SSH / Ansible ───────────────────────────────────────────────
init-ssh:
	@echo "🔑 Distribution des clés SSH entre conteneurs..."
	@for node in master1 master2 worker1 worker2 edge; do \
		PUB=$$(docker exec $$node cat /home/hadoop/.ssh/id_rsa.pub 2>/dev/null); \
		for target in master1 master2 worker1 worker2 edge; do \
			if [ "$$node" != "$$target" ]; then \
				docker exec $$target bash -c \
					"grep -qF '$$PUB' /home/hadoop/.ssh/authorized_keys 2>/dev/null || \
					 echo '$$PUB' >> /home/hadoop/.ssh/authorized_keys" 2>/dev/null || true; \
			fi; \
		done; \
		echo "  ✓ Clé de $$node distribuée"; \
	done
	@echo "✅ Clés SSH distribuées."

ansible-ping:
	ansible all -i $(ANSIBLE_INV) -m ping

ansible-deploy:
	ansible-playbook -i $(ANSIBLE_INV) ../ansible/site.yml

# ─── HDFS ────────────────────────────────────────────────────────
hdfs-init:
	@echo "📁 Formatage du NameNode HDFS..."
	docker exec -u hadoop master1 bash -c \
		"$(HADOOP_EXEC)/hdfs namenode -format -clusterId bigdata-cluster -nonInteractive 2>&1 | tail -5"
	@echo "🚀 Démarrage HDFS..."
	docker exec -u hadoop master1 bash -c \
		"source /etc/profile.d/hadoop.sh && \
		 HDFS_NAMENODE_USER=hadoop HDFS_DATANODE_USER=hadoop \
		 HDFS_SECONDARYNAMENODE_USER=hadoop \
		 /opt/bigdata/hadoop/sbin/start-dfs.sh"
	@echo "🚀 Démarrage YARN..."
	docker exec -u hadoop master1 bash -c \
		"source /etc/profile.d/hadoop.sh && \
		 YARN_RESOURCEMANAGER_USER=hadoop YARN_NODEMANAGER_USER=hadoop \
		 /opt/bigdata/hadoop/sbin/start-yarn.sh"
	@sleep 10
	@echo "📊 Activation Erasure Coding..."
	docker exec -u hadoop master1 bash -c \
		"/opt/bigdata/hadoop/bin/hdfs ec -enablePolicy -policy RS-3-2-1024k; \
		 /opt/bigdata/hadoop/bin/hdfs ec -enablePolicy -policy XOR-2-1-1024k; \
		 /opt/bigdata/hadoop/bin/hdfs dfs -mkdir -p /data/cold /data/hot /data/archive /data/test-ec; \
		 /opt/bigdata/hadoop/bin/hdfs ec -setPolicy -policy RS-3-2-1024k -path /data/cold; \
		 /opt/bigdata/hadoop/bin/hdfs ec -setPolicy -policy XOR-2-1-1024k -path /data/test-ec; \
		 /opt/bigdata/hadoop/bin/hdfs dfs -mkdir -p /user /user/hive/warehouse /spark-logs /iceberg-warehouse /tmp; \
		 /opt/bigdata/hadoop/bin/hdfs dfs -chmod 777 /tmp /user/hive/warehouse /spark-logs"
	@echo "✅ HDFS initialisé avec Erasure Coding."
	@make hdfs-status

hdfs-status:
	@echo ""
	@echo "═══ HDFS Report ════════════════════════════════════════"
	docker exec -u hadoop master1 /opt/bigdata/hadoop/bin/hdfs dfsadmin -report 2>/dev/null | head -30 || \
		echo "  ⚠️  HDFS non démarré. Lancer: make hdfs-init"

yarn-status:
	@echo ""
	@echo "═══ YARN Nodes ══════════════════════════════════════════"
	docker exec -u hadoop master1 /opt/bigdata/hadoop/bin/yarn node -list 2>/dev/null || \
		echo "  ⚠️  YARN non démarré."

ec-status:
	@echo ""
	@echo "═══ HDFS Erasure Coding Policies ═══════════════════════"
	docker exec -u hadoop master1 /opt/bigdata/hadoop/bin/hdfs ec -listPolicies 2>/dev/null || \
		echo "  ⚠️  HDFS non démarré."

# ─── Nettoyage ───────────────────────────────────────────────────
clean:
	@echo "⚠️  Suppression des conteneurs ET des volumes..."
	$(COMPOSE) down -v --remove-orphans
	docker image rm bigdata/master1 bigdata/master2 bigdata/worker bigdata/edge bigdata/base 2>/dev/null || true
	@echo "✅ Nettoyage terminé."

clean-soft:
	@echo "Arrêt des conteneurs uniquement (volumes conservés)..."
	$(COMPOSE) down --remove-orphans

# ─── Outils ──────────────────────────────────────────────────────
student-create:
	@read -p "Login étudiant : " u; \
	ansible-playbook -i $(ANSIBLE_INV) ../ansible/playbooks/create_student.yml -e "username=$$u"

health:
	ansible-playbook -i $(ANSIBLE_INV) ../ansible/playbooks/health_check.yml
