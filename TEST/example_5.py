class Checker:
    def __init__(self, s, mode):
        self.s = s; self.mode = mode; self.f = open('p.txt','a')
    def check(self):
        ok = True
        for i in range(len(self.s)):
            for j in range(len(self.s)):
                if i + j == len(self.s) - 1 and self.s[i] != self.s[j]:
                    ok = False
        return ok
    def conv(self, v):
        if self.mode == 'x': return str(v)
        elif self.mode == 'y': return int(v)
        elif self.mode == 'z': return bool(v)
        return v
    def save(self, v): self.f.write(str(v))
    def read(self): return open('p.txt').read()
    def echo(self): print(self.s)