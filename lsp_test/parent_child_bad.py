class Parent:
    def compute(self, x: int) -> int:
        if x < 0:
            raise ValueError("x must be >= 0")
        return x * 2


class Child(Parent):
    def compute(self, x: int) -> int:
        # ❌ Precondition strengthening: new check
        if x < 10:
            raise ValueError("x must be >= 10")

        # ❌ Type narrowing
        if not isinstance(x, int):
            raise TypeError("x must be int")

        # ❌ Logical contradiction / narrowing:
        # Parent allows x >= 0 but child requires x >= 10.
        return x * 3
