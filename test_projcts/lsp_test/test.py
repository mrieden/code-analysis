

from abc import ABC, abstractmethod

class Animal:
    def process(self, x:int) -> object:
        return x

class Dog(Animal):

    def process(self, x:str) -> str:

        if x == "":
            raise ValueError()

        return x

class BadDog(Animal):

    def process(self, x, y):
        raise NotImplementedError()

class A:
    @classmethod
    def test(cls):
        pass

class B(A):
    def test(self):
        pass
