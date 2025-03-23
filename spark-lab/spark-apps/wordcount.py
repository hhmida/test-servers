from pyspark import SparkContext, SparkConf
conf = (SparkConf().setAppName('Wordcount on Spark'))
sc = SparkContext(conf=conf)
texte = sc.textFile('hdfs://nodemaster:9000/user/hadoop/shakespeare.txt')
count = texte.flatMap(lambda l:l.split()).map(lambda w:(w,1)).reduceByKey(lambda a,b:a+b)
count.saveAsTextFile('hdfs://nodemaster:9000/user/hadoop/resultat')
