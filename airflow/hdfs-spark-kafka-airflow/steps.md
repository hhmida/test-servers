# 🚀 Installation et Configuration d'Apache Airflow avec Docker

Ce document décrit comment installer et exécuter **Apache Airflow** avec **Docker Compose**, en intégrant l'installation automatique des providers via `requirements.txt`.

---

## 📌 1. Structure du projet
Créez un dossier `airflow-docker/` et ajoutez les fichiers suivants :
```
airflow-docker/
│── dags/                    # Stockage des DAGs
│── logs/                    # Logs d’Airflow
│── plugins/                 # Plugins personnalisés
│── requirements.txt         # Fichier des dépendances Airflow
│── docker-compose.yml       # Configuration Docker
│── Dockerfile               # Construction de l’image Airflow
│── .env                     # Variables d’environnement
```

---

## 📌 2. `requirements.txt` (Liste des providers)
Ajoutez les providers nécessaires :
```txt
apache-airflow-providers-apache-kafka
apache-airflow-providers-apache-spark
apache-airflow-providers-apache-hdfs
apache-airflow-providers-apache-hadoop
```
Ajoutez d'autres selon vos besoins.

---

## 📌 3. `Dockerfile` pour Airflow
Créez un `Dockerfile` pour installer les providers automatiquement :
```dockerfile
FROM apache/airflow:2.7.3  # Remplacez par la dernière version d'Airflow

# Passer à l’utilisateur root pour installer des dépendances
USER root
RUN apt-get update && apt-get install -y curl vim

# Copier et installer les packages Python
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Revenir à l’utilisateur Airflow
USER airflow
```

---

## 📌 4. `docker-compose.yml`
Fichier complet pour exécuter Airflow avec **PostgreSQL**, **Kafka**, **Spark** et **HDFS** comme backend.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13
    container_name: airflow_postgres
    restart: always
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  kafka:
    image: bitnami/kafka:latest
    container_name: kafka
    restart: always
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper

  zookeeper:
    image: bitnami/zookeeper:latest
    container_name: zookeeper
    restart: always
    environment:
      ALLOW_ANONYMOUS_LOGIN: "yes"
    ports:
      - "2181:2181"

  spark:
    image: bitnami/spark:latest
    container_name: spark
    restart: always
    environment:
      SPARK_MODE: master
    ports:
      - "7077:7077"
      - "8081:8081"

  hdfs:
    image: bde2020/hadoop-namenode:latest
    container_name: hdfs
    restart: always
    environment:
      CLUSTER_NAME: "hadoop_cluster"
    ports:
      - "9870:9870"
    volumes:
      - hdfs_data:/hadoop/dfs/name

  airflow-webserver:
    build: .
    container_name: airflow_webserver
    restart: always
    depends_on:
      - postgres
      - kafka
      - spark
      - hdfs
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    ports:
      - "8080:8080"
    command: ["webserver"]
  
  airflow-scheduler:
    build: .
    container_name: airflow_scheduler
    restart: always
    depends_on:
      - postgres
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    command: ["scheduler"]

volumes:
  postgres_data:
  hdfs_data:
```

---

## 📌 5. `.env` (Facultatif)
Stockez vos variables d’environnement ici :
```env
AIRFLOW_UID=50000
AIRFLOW_GID=0
```
Airflow utilisera ces valeurs pour définir les permissions.

---

## 📌 6. Initialisation et Lancement
Exécutez ces commandes :
```sh
# Créer les dossiers nécessaires
mkdir -p dags logs plugins

# Initialiser la base de données Airflow
docker-compose up airflow-webserver airflow-scheduler -d
docker-compose run airflow-webserver airflow db init

# Créer un utilisateur admin
docker-compose run airflow-webserver airflow users create \
    --username admin --password admin \
    --firstname Air --lastname Flow \
    --role Admin --email admin@example.com

# Lancer Airflow
docker-compose up -d
```

---

## 🚀 Et après ?
✅ **Airflow est maintenant accessible sur** `http://localhost:8080`  
✅ **Les providers sont installés automatiquement** au démarrage  
✅ **Kafka, Spark et HDFS sont intégrés**  

