
class Payment:
    def process(self, type):
        if type == "card":
            print("Processing card")
        elif type == "paypal":
            print("Processing paypal")

        if isinstance(type, int):
            print("Built-in type check")

        if isinstance(type, Payment):
            print("Non-built-in type check")

class Order:
    def calculate(self, method):
        match method:
            case "cash":
                return 10
            case "visa":
                return 5
            case _:
                return 0

class Shipping:
    def get_cost(self, kind):
        if kind == "express":
            return 20
        elif kind == "standard":
            return 10

class Inventory:
    def check(self, action):
        if action == "add":
            print("Adding item")
        elif action == "remove":
            print("Removing item")

        if isinstance(action, str):
            print("Built-in string check")

class Order:
    def calculate(self, method):
        if method == "cash":
            return 10
        elif method == "visa":
            return 5
        else:
            return 0

