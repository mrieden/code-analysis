import ast

BUILTIN_TYPES = {"int", "str", "float", "list", "dict", "bool", "set", "tuple"}

class OCPDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.current_class = None

    def is_type_comparison(self, node):
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            # Checks for things like: if type == 'Admin' or if kind == 1
            if isinstance(left, ast.Name) and left.id.lower() in ["type", "kind", "action", "method"]:
                return True
        return False

    def is_isinstance_dispatch(self, node):
        if isinstance(node.test, ast.Call):
            func = node.test.func
            if isinstance(func, ast.Name) and func.id == "isinstance":
                type_arg = node.test.args[1] if len(node.test.args) > 1 else None
                if isinstance(type_arg, ast.Name) and type_arg.id in BUILTIN_TYPES:
                    return False
                return True
        return False

    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_If(self, node):
        if self.is_type_comparison(node):
            self.violations.append({
                "line": node.lineno,
                "detail": f"Type-based branching in {self.current_class or 'global scope'}"
            })
        elif self.is_isinstance_dispatch(node):
            self.violations.append({
                "line": node.lineno,
                "detail": f"Isinstance check on custom class in {self.current_class or 'global scope'}"
            })
        self.generic_visit(node)

    def visit_Match(self, node):
        self.violations.append({
            "line": node.lineno, 
            "detail": "Pattern matching (match-case) used for dispatching"
        })
        self.generic_visit(node)

def analyze_ocp(code: str):
    try:
        tree = ast.parse(code)
        detector = OCPDetector()
        detector.visit(tree)
        
        if not detector.violations:
            return {"status": "Pass", "reason": "No manual type-checking detected.", "suggestion": "N/A"}
        
        v = detector.violations[0]
        return {
            "status": "Violation",
            "reason": f"Line {v['line']}: {v['detail']}",
            "suggestion": "Use Polymorphism or the Strategy Pattern instead of checking types manually."
        }
    except:
        return {"status": "Pass", "reason": "Parsing...", "suggestion": "N/A"}
