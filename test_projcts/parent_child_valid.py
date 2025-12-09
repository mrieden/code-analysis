class Animal:
    def speak(self) -> str:
        return "generic sound"

class Dog(Animal):
    def speak(self) -> str:
        return "woof"
