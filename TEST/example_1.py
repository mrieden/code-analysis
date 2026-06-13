class DataManager:
    def __init__(self, d, mode):
        self.d = d; self.mode = mode; self.log = open('log.txt','a')
    def process(self):
        r = []
        for i in range(len(self.d)):
            for j in range(len(self.d)):
                if i != j and self.d[i] == self.d[j]:
                    r.append(self.d[i])
        return r
    def render(self, x):
        if self.mode == 'json': return str(x)
        elif self.mode == 'csv': return ','.join(map(str,x))
        elif self.mode == 'html': return '<p>'+str(x)+'</p>'
        return x
    def save(self, x): self.log.write(str(x))
    def fetch(self): return open('data.txt').read()
    def notify(self): print('done', self.d)