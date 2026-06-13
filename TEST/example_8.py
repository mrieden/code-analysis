class Trader:
    def __init__(self, p, mode):
        self.p = p; self.mode = mode; self.f = open('t.txt','a')
    def profit(self):
        best = 0
        for i in range(len(self.p)):
            for j in range(i+1, len(self.p)):
                if self.p[j] - self.p[i] > best:
                    best = self.p[j] - self.p[i]
        return best
    def tag(self, v):
        if self.mode == 'usd': return '$'+str(v)
        elif self.mode == 'eur': return str(v)+'E'
        elif self.mode == 'gbp': return str(v)+'P'
        return v
    def save(self, v): self.f.write(str(v))
    def load(self): return open('t.txt').read()
    def show(self): print(self.p)