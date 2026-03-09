# Mapping des ports – Mode Docker

| Hôte  | Conteneur | Service           |
|-------|-----------|-------------------|
| 9870  | master1:9870 | HDFS NameNode Web |
| 8088  | master1:8088 | YARN Web UI |
| 8080  | master1:8080 | Spark Master Web |
| 7077  | master1:7077 | Spark Master RPC |
| 9000  | master1:9000 | HDFS RPC |
| 2181  | master1:2181 | ZooKeeper |
| 9092  | master1:9092 | Kafka |
| 9091  | master1:9090 | Cockpit master1 |
| 9868  | master2:9868 | HDFS Secondary NN |
| 10000 | master2:10000 | HiveServer2 |
| 10002 | master2:10002 | HiveServer2 Web |
| 16010 | master2:16010 | HBase Master Web |
| 21000 | master2:21000 | Atlas |
| 6080  | master2:6080 | Ranger Admin |
| 9093  | master2:9090 | Cockpit master2 |
| 9864  | worker1:9864 | DataNode HTTP |
| 8042  | worker1:8042 | NodeManager Web |
| 9094  | worker1:9090 | Cockpit worker1 |
| 9865  | worker2:9864 | DataNode HTTP |
| 8043  | worker2:8042 | NodeManager Web |
| 9095  | worker2:9090 | Cockpit worker2 |
| 8180  | edge:8080 | NiFi HTTP |
| 8443  | edge:8443 | NiFi HTTPS |
| 8765  | edge:8765 | Phoenix QS |
| 9096  | edge:9090 | Prometheus |
| 3000  | edge:3000 | Grafana |
| 9097  | edge:9090 | Cockpit edge |
