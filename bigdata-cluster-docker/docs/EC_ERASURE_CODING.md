# HDFS Erasure Coding – Guide Pédagogique

## Résumé

| Répertoire HDFS  | Policy        | Min nœuds | Overhead | Usage |
|-----------------|---------------|-----------|---------|-------|
| /data/cold      | RS-3-2-1024k  | 5         | 67%     | Données froides |
| /data/archive   | RS-6-3-1024k  | 9         | 50%     | Archives (futur) |
| /data/test-ec   | XOR-2-1-1024k | 3         | 50%     | Tests étudiants |
| /data/hot       | Réplication×2 | 1         | 100%    | Données chaudes |

## Exercices

```bash
# Écrire dans un répertoire EC
echo "Test EC" | hdfs dfs -put - /data/cold/test.txt
hdfs ec -getPolicy -path /data/cold/test.txt

# Benchmark
hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-client-jobclient-*-tests.jar \
  TestDFSIO -write -nrFiles 4 -fileSize 128
```
