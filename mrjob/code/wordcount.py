from mrjob.step import MRStep
from mrjob.job import MRJob
class WordCount(MRJob):
    def steps(self):
        return [MRStep(mapper=self.mapper_get_words, reducer=self.reducer_count_words)]

    def mapper_get_words(self, _, line):
        t = []
        for c in line.split():
            t.append((c, len(c)))
        t.sort(reverse=True, key=lambda x: x[1])
        yield None, t[:2]
    def reducer_count_words(self, key, values):
        t = []
        for v in list(values):
            for j in v:
                if j not in t:
                    t.append(j)
        
        t.sort(reverse=True, key=lambda x: x[1])
        yield None, t[:2]

if __name__ == '__main__':
    WordCount.run()