class Parent:
    def f(self, x):
        if x < 100:
            return x


class Child(Parent):
    def f(self, x):
        if x < 10:   # ❌ Narrows the valid domain drastically
            return x
        return None   # ❌ Returns None while parent never returns None
