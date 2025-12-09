class Parent:
    def get_value(self) -> int:
        return 5


class Child(Parent):
    def get_value(self) -> str:  # ❌ return type changed
        return "hello"
