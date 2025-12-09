import ast
import os
import inspect

def exc_name_from_raise(node: ast.Raise) -> str:
    """Extract exception name from raise statement."""
    if node.exc is None:
        return ""
    
    if isinstance(node.exc, ast.Name):
        return node.exc.id
    elif isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
        return node.exc.func.id
    elif isinstance(node.exc, ast.Attribute):
        return node.exc.attr
    elif isinstance(node.exc, ast.Subscript):
        # Handle cases like Exception[Type]
        if isinstance(node.exc.value, ast.Name):
            return node.exc.value.id
    return ""

class AbstractClassHelper:
    @staticmethod
    def is_abstract_method(node: ast.FunctionDef) -> bool:
        
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id == "abstractmethod":
                return True
            if isinstance(d, ast.Attribute) and d.attr == "abstractmethod":
                return True

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            return True

        for n in ast.walk(node):
            if isinstance(n, ast.Raise):
                name = exc_name_from_raise(n)
                if name == "NotImplementedError":
                    return True

        doc = ast.get_docstring(node)
        if doc:
            low = doc.lower()
            if any(word in low for word in ("abstract", "must implement", "override", "implement me")):
                return True

        return False

    @staticmethod
    def is_abstract_class(node: ast.ClassDef) -> bool:
        # 1. Inherits from ABC or abc.ABC or metaclass=ABCMeta
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ("ABC", "ABCMeta"):
                return True
            if isinstance(base, ast.Attribute) and base.attr in ("ABC", "ABCMeta"):
                return True

        # 2. Has at least one abstract method by heuristic
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if AbstractClassHelper.is_abstract_method(item):
                    return True

        return False

class LSPDetector(ast.NodeVisitor):
    def __init__(self):
        self.classes = {}      
        self.inheritance = {}  
        self.current_class = None
        self.violations = []
        self.abstract_classes = set()

    def add_violation(self, node, msg):
        self.violations.append(f"Line {node.lineno}: {msg}")

    # Parse Class Definitions
    def visit_ClassDef(self, node):
        self.classes[node.name] = node
        parents = [b.id for b in node.bases if isinstance(b, ast.Name)]
        self.inheritance[node.name] = parents
        
        # Check if this is an abstract class
        if AbstractClassHelper.is_abstract_class(node):
            self.abstract_classes.add(node.name)
        
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    # Parse Function Definitions
    def visit_FunctionDef(self, node):
        if self.current_class is None:
            return
        
        cls = self.classes[self.current_class]
        parents = self.inheritance.get(self.current_class, [])

        # Check overridden methods
        for parent in parents:
            if parent in self.classes:
                parent_methods = {
                    p.name: p for p in self.classes[parent].body 
                    if isinstance(p, ast.FunctionDef)
                }

                if node.name in parent_methods:
                    parent_method = parent_methods[node.name]
                    self.compare_methods(node, parent_method, parent)

        self.generic_visit(node)

    
    def compare_methods(self, child, parent, parent_name):
        # Enhanced LSP checks with abstract class awareness
        
        # Check if parent method is abstract
        parent_is_abstract = AbstractClassHelper.is_abstract_method(parent)
        
        # Check parameter count
        child_args = len(child.args.args) - 1  # -1 to exclude 'self'
        parent_args = len(parent.args.args) - 1

        if child_args != parent_args:
            self.add_violation(
                child,
                f"LSP: '{child.name}' overrides parent '{parent_name}' "
                f"with different parameter count ({child_args} vs {parent_args})."
            )

        # Check return type annotations
        c_ret = ast.unparse(child.returns) if child.returns else None
        p_ret = ast.unparse(parent.returns) if parent.returns else None

        if c_ret != p_ret:
            if p_ret is not None:
                self.add_violation(
                    child,
                    f"LSP: '{child.name}' changes return type "
                    f"from '{p_ret}' to '{c_ret}'."
                )

        # Check if child raises NotImplementedError when parent is not abstract
        if not parent_is_abstract:
            for n in ast.walk(child):
                if isinstance(n, ast.Raise):
                    if isinstance(n.exc, ast.Call) and getattr(n.exc.func, "id", "") == "NotImplementedError":
                        self.add_violation(
                            child,
                            f"LSP: '{child.name}' raises NotImplementedError "
                            f"while overriding non-abstract parent method."
                        )
        
        # Detect new exceptions not raised in parent (only for non-abstract parent methods)
        if not parent_is_abstract:
            parent_exceptions = set()
            for n in ast.walk(parent):
                if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                    exc_name = getattr(n.exc.func, "id", None)
                    if exc_name:
                        parent_exceptions.add(exc_name)
            
            child_exceptions = set()
            for n in ast.walk(child):
                if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                    exc_name = getattr(n.exc.func, "id", None)
                    if exc_name:
                        child_exceptions.add(exc_name)
            
            # Check for new exceptions introduced in child
            new_exceptions = child_exceptions - parent_exceptions
            for exc in new_exceptions:
                self.add_violation(
                    child,
                    f"LSP: '{child.name}' introduces new exception '{exc}' "
                    f"not present in parent method."
                )


def analyze_file(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    detector = LSPDetector()
    detector.visit(tree)

    return detector.violations



def analyze_project(folder):
    results = {}
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".py"):
                file_path = os.path.join(root, f)
                issues = analyze_file(file_path)
                if issues:
                    results[file_path] = issues
    return results



if __name__ == "__main__":
    project = input("Enter project folder path: ").strip()
    result = analyze_project(project)

    if not result:
        print("No LSP violations detected ✔")
    else:
        print("\n=== LSP Violations Detected ===")
        for file, violations in result.items():
            print(f"\nFile: {file}")
            for v in violations:
                print("  -", v)