import ast

class OCPDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    # هل الشرط فيه مقارنة equality على type/ kind/ action؟
    def is_type_comparison(self, node):
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            if isinstance(left, ast.Name):
                if left.id.lower() in ["type", "kind", "action", "method"]:
                    return True
        return False

    # هل الشرط عبارة عن isinstance؟
    def is_isinstance_dispatch(self, node):
        # if isinstance(x, SomeClass):
        if isinstance(node.test, ast.Call):
            func = node.test.func
            if isinstance(func, ast.Name) and func.id == "isinstance":
                return True
        return False

    # الدخول عند تعريف الكلاس
    def visit_ClassDef(self, node):
        
        for item in ast.walk(node):

            # 1) IF / ELIF checks
            if isinstance(item, ast.If):

                if self.is_type_comparison(item):
                    self.violations.append({
                        "class": node.name,
                        "line": item.lineno,
                        "type": "IF Type Dispatch",
                        "detail": "Uses if/elif to check type → breaks OCP"
                    })

                if self.is_isinstance_dispatch(item):
                    self.violations.append({
                        "class": node.name,
                        "line": item.lineno,
                        "type": "isinstance Dispatch",
                        "detail": "Uses isinstance() → likely violates OCP"
                    })

            # 2) MATCH / CASE checks
            if isinstance(item, ast.Match):
                self.violations.append({
                    "class": node.name,
                    "line": item.lineno,
                    "type": "MATCH-CASE Dispatch",
                    "detail": "Uses match-case (switch-style) → breaks OCP"
                })

        self.generic_visit(node)



def detect_ocp_violations(code: str):
    tree = ast.parse(code)
    detector = OCPDetector()
    detector.visit(tree)
    return detector.violations


# ======= Example ========
code = """
class Payment:
    def process(self, type):
        if type == "card":
            print("card")
        elif type == "paypal":
            print("paypal")

        if isinstance(type, int):
            print("bad design")

class Order:
    def calculate(self, method):
        match method:
            case "cash":
                return 10
            case "visa":
                return 5
"""

violations = detect_ocp_violations(code)
for v in violations:
    print(v)

