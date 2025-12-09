from abc import ABC, abstractmethod

class Parent(ABC):
    @abstractmethod
    def compute(self, x: int) -> int:
        """Compute something."""
        pass


class Child(Parent):
    def compute(self, x: int) -> int:
        # No precondition strengthening.
        # No type narrowing.
        return x + 10
