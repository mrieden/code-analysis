class Bird:
    def fly(self, speed: int) -> int:
        return speed

class Penguin(Bird):
    # ❌ 1. Parameter count changed → LSP violation
    def fly(self) -> int:
        return 0

class Vehicle:
    def move(self) -> int:
        return 1

class Car(Vehicle):
    # ❌ 2. Return type changed → LSP violation
    def move(self) -> str:
        return "moving"

class Shape:
    def draw(self) -> None:
        pass

class Line(Shape):
    # ❌ 3. Raise NotImplementedError → LSP violation
    def draw(self) -> None:
        raise NotImplementedError

class Loader:
    def load(self) -> None:
        pass

class UnsafeLoader(Loader):
    # ❌ 4. New exception type introduced
    def load(self) -> None:
        raise ValueError("bad data")
