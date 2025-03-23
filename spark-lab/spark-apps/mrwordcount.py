from mrjob.step import MRStep
from mrjob.job import MRJob
class WordCount(MRJob):
    def steps(self):
        return [MRStep(mapper=self.mapper_get_words, reducer=self.reducer_count_words)]
    def mapper_get_words(self, _, line):
        for word in line.split():
            yield word, 1
    def reducer_count_words(self, key, values):
        yield key, sum(values)
if __name__ == '__main__':
    WordCount.run()
