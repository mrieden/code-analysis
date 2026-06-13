class SetOps:
    def __init__(self, a, b, mode):
        self.a = a; self.b = b; self.mode = mode; self.f = open('i.txt','a')
    def common(self):
        r = []
        for x in self.a:
            for y in self.b:
                if x == y and x not in r:
                    r.append(x)
        return r
    def shape(self, v):
        if self.mode == 'l': return list(v)
        elif self.mode == 't': return tuple(v)
        elif self.mode == 's': return set(v)
        return v
    def write(self, v): self.f.write(str(v))
    def read(self): return open('i.txt').read()
    def emit(self): print(self.a, self.b)