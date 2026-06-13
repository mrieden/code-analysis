class Calc:
    def __init__(self, n, mode):
        self.n = n; self.mode = mode; self.f = open('c.txt','a')
    def fib(self, k):
        if k < 2: return k
        return self.fib(k-1) + self.fib(k-2)
    def run(self): return self.fib(self.n)
    def out(self, v):
        if self.mode == 1: return str(v)
        elif self.mode == 2: return hex(v)
        elif self.mode == 3: return bin(v)
        return v
    def persist(self, v): self.f.write(str(v))
    def read(self): return open('c.txt').read()
    def show(self): print(self.n)