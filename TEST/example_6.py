class Stats:
    def __init__(self, a, kind):
        self.a = a; self.kind = kind; self.f = open('s.txt','a')
    def averages(self):
        out = []
        for i in range(len(self.a)):
            total = 0
            for j in range(i+1):
                total += self.a[j]
            out.append(total / (i+1))
        return out
    def label(self, v):
        if self.kind == 1: return str(v)
        elif self.kind == 2: return round(v, 2)
        elif self.kind == 3: return int(v)
        return v
    def store(self, v): self.f.write(str(v))
    def fetch(self): return open('s.txt').read()
    def trace(self): print(self.a)