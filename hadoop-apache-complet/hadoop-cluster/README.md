# Hadoop Cluster (HDFS + YARN + Hive + Hue)

Stack based on official Apache images.

## Architecture

- 1 NameNode + 3 DataNodes
- 1 ResourceManager + 3 NodeManagers
- HistoryServer (Timeline)
- Postgres (Hive Metastore + Hue)
- Hive Metastore + HiveServer2
- Hue
- Tools container (for Pig / Sqoop / client commands)

## Prerequisites

- Docker + Docker Compose
- At least 8 GB RAM recommended

## Quick start

```bash
# 1. Download PostgreSQL JDBC driver
mkdir -p jars
curl -L -o jars/postgresql.jar \
  https://jdbc.postgresql.org/download/postgresql-42.7.4.jar

# 2. Start the cluster
docker compose up -d

# 3. Wait ~1-2 minutes then check
docker compose ps
docker logs namenode --tail 30
```

## Access URLs

| Service            | URL                          |
|--------------------|------------------------------|
| Hue                | http://localhost:8888        |
| NameNode           | http://localhost:9870        |
| ResourceManager    | http://localhost:8088        |
| History Server     | http://localhost:8188        |
| HiveServer2 Web UI | http://localhost:10002       |

Default Hue login: create an account on first access (or admin/admin depending on version).

## Useful commands

```bash
# Enter NameNode
docker exec -it namenode bash

# Check HDFS
hdfs dfsadmin -report
hdfs dfs -ls /

# Run WordCount example
hdfs dfs -mkdir -p /user/root/input
echo "Hello Hadoop Hello MapReduce" > /tmp/test.txt
hdfs dfs -put /tmp/test.txt /user/root/input/
yarn jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar wordcount \
  /user/root/input /user/root/output
hdfs dfs -cat /user/root/output/part-r-00000

# Beeline (Hive)
docker exec -it hiveserver2 beeline -u 'jdbc:hive2://localhost:10000'

# Pig and Sqoop clients
docker exec -it tools pig -version
docker exec -it tools sqoop version
```

## Reset the cluster (destroy all data)

```bash
docker compose down -v
```

## Notes

- NameNode is automatically formatted on first start.
- capacity-scheduler.xml is included to avoid the "Queue configuration missing child queue names for root" error.
- log4j.properties is included to remove the "log4j.properties is not found" warning.
