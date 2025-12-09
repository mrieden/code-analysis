import ast

class SRPDetectorRefined(ast.NodeVisitor):
    def __init__(self, method_threshold=5, dependency_threshold=2):
        self.violations = []
        self.method_threshold = method_threshold
        self.dependency_threshold = dependency_threshold
        self.current_class = None
        self.class_dependencies = {}
        self.method_actions = {}
        self.constructor_attrs = set()

    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.constructor_attrs = set()
        method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]

        # Rule 1: Too many methods
        if len(method_names) > self.method_threshold:
            self.violations.append({
                "class": node.name,
                "reason": f"Has {len(method_names)} methods (threshold {self.method_threshold})."
            })

        # Initialize dependency set for this class
        self.class_dependencies[node.name] = set()

        # Visit methods
        for n in node.body:
            if isinstance(n, ast.FunctionDef):
                self.visit(n)

        # Rule 2: Too many distinct dependencies (excluding constructor)
        deps = self.class_dependencies[node.name] - self.constructor_attrs
        if len(deps) > self.dependency_threshold:
            self.violations.append({
                "class": node.name,
                "reason": f"Class uses multiple components: {', '.join(deps)}."
            })

        # Rule 3: Methods mixing multiple unrelated actions
        for m, actions in self.method_actions.items():
            # Ignore harmless sub-steps like datetime.now() or multiple prints
            main_actions = set(a for a in actions if a not in ("now", "print_helper"))
            if len(main_actions) > 1:
                self.violations.append({
                    "class": node.name,
                    "reason": f"Method {m} mixes multiple actions: {', '.join(main_actions)}."
                })

        self.current_class = None

    def visit_FunctionDef(self, node):
        actions = set()

        # Track constructor-injected collaborators
        if node.name == "__init__":
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            self.constructor_attrs.add(target.attr)

        for child in ast.walk(node):
            # Track self dependencies
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id == "self":
                if self.current_class:
                    self.class_dependencies[self.current_class].add(child.attr)

            # Track method calls
            if isinstance(child, ast.Call):
                # Delegation detection
                if isinstance(child.func, ast.Attribute):
                    current = child.func
                    while isinstance(current, ast.Attribute):
                        current = current.value
                    if isinstance(current, ast.Name) and current.id == "self":
                        actions.add("delegation")
                        continue

                # Standard function detection
                fname = None
                if isinstance(child.func, ast.Name):
                    fname = child.func.id.lower()
                elif isinstance(child.func, ast.Attribute):
                    fname = child.func.attr.lower()

                if fname:
                    if fname in ("open", "write"):
                        actions.add("file_io")
                    elif fname == "print":
                        actions.add("print_helper")  # harmless sub-step
                    elif fname == "dumps" or fname == "json":
                        actions.add("formatting")
                    elif fname == "now":
                        actions.add("now")  # ignore as harmless
                    else:
                        actions.add(fname)

                # Scan string constants for semantic hints
                for arg in getattr(child, "args", []):
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        text = arg.value.lower()
                        if any(k in text for k in ["save", "database", "insert"]):
                            actions.add("database")
                        if any(k in text for k in ["send", "email", "notify"]):
                            actions.add("email")
                        if any(k in text for k in ["log", "success", "audit"]):
                            actions.add("logging")

        self.method_actions[node.name] = actions
        self.generic_visit(node)


def analyze_code(code, method_threshold=5, dependency_threshold=2):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"Syntax Error in your code: {e}")
        return []
    detector = SRPDetectorRefined(method_threshold, dependency_threshold)
    detector.visit(tree)
    return detector.violations


if __name__ == "__main__":
    sample_code = '''
class UserManager:
    def __init__(self, db, emailer):
        self.db = db
        self.emailer = emailer
        self.cache = {}

    def save_user(self, user):
        self.db.insert(user)
        print("User saved!")
        self.emailer.send("Welcome!", user.email)

    def log_action(self, msg):
        print("LOG:", msg)

    def update_user(self, user):
        self.db.update(user)
        print("Updated")
'''

    violations = analyze_code(sample_code)
    print(violations)

    