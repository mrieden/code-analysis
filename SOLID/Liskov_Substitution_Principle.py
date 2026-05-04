import ast


def exc_name_from_raise(node: ast.Raise) -> str:
    """Extract exception name from raise statement."""
    if node.exc is None:
        return ""

    if isinstance(node.exc, ast.Name):
        return node.exc.id

    elif isinstance(node.exc, ast.Call):
        if isinstance(node.exc.func, ast.Name):
            return node.exc.func.id

        elif isinstance(node.exc.func, ast.Attribute):
            return node.exc.func.attr

    elif isinstance(node.exc, ast.Attribute):
        return node.exc.attr

    elif isinstance(node.exc, ast.Subscript):
        if isinstance(node.exc.value, ast.Name):
            return node.exc.value.id

    return ""


class AbstractClassHelper:

    ABSTRACT_DECORATORS = {
        "abstractmethod",
        "abstractproperty",
        "abstractclassmethod",
        "abstractstaticmethod",
    }

    @staticmethod
    def is_abstract_method(node: ast.FunctionDef) -> bool:

        # decorator checks
        for d in node.decorator_list:

            if isinstance(d, ast.Name):
                if d.id in AbstractClassHelper.ABSTRACT_DECORATORS:
                    return True

            if isinstance(d, ast.Attribute):
                if d.attr in AbstractClassHelper.ABSTRACT_DECORATORS:
                    return True

        # empty body patterns
        if len(node.body) == 1:

            stmt = node.body[0]

            if isinstance(stmt, ast.Pass):
                return True

            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                return True

            if (
                isinstance(stmt, ast.Return)
                and isinstance(stmt.value, ast.Name)
                and stmt.value.id == "NotImplemented"
            ):
                return True

        # raise NotImplementedError
        for n in ast.walk(node):
            if isinstance(n, ast.Raise):
                if exc_name_from_raise(n) == "NotImplementedError":
                    return True

        # docstring hints
        doc = ast.get_docstring(node)

        if doc:
            low = doc.lower()

            triggers = [
                "not implemented",
                "abstract method",
                "subclasses should implement",
                "to be implemented by subclass",
                "abstract",
                "must implement",
                "override",
                "implement me",
            ]

            if any(t in low for t in triggers):
                return True

        return False

    @staticmethod
    def is_abstract_class(node: ast.ClassDef) -> bool:

        for base in node.bases:

            if isinstance(base, ast.Name):
                if base.id in ("ABC", "ABCMeta"):
                    return True

            if isinstance(base, ast.Attribute):
                if base.attr in ("ABC", "ABCMeta"):
                    return True

        for item in node.body:

            if isinstance(item, ast.FunctionDef):

                if AbstractClassHelper.is_abstract_method(item):
                    return True

        return False


class LSPDetector(ast.NodeVisitor):

    BUILTIN_TYPES = {
        "object": [],
        "int": ["object"],
        "float": ["object"],
        "str": ["object"],
        "bool": ["object"],
        "list": ["object"],
        "dict": ["object"],
        "tuple": ["object"],
        "set": ["object"],
    }

    def __init__(self):

        self.classes = {}
        self.inheritance = {}
        self.current_class = None

        self.violations = []

        self.abstract_classes = set()



    def add_violation(self, node, msg, severity="Medium"):

        self.violations.append(
            {
                "line": getattr(node, "lineno", -1),
                "severity": severity,
                "message": msg,
            }
        )

    def get_source(self, node):

        try:
            return ast.unparse(node)
        except:
            return ""


    def get_all_parents(self, cls_name):

        result = set()

        for parent in self.inheritance.get(cls_name, []):

            result.add(parent)

            result.update(self.get_all_parents(parent))

        return result

    def is_subtype(self, child_type, parent_type):

        if child_type == parent_type:
            return True

        if child_type is None or parent_type is None:
            return False

        # builtin hierarchy
        if child_type in self.BUILTIN_TYPES:
            if parent_type in self.BUILTIN_TYPES[child_type]:
                return True

        # user-defined hierarchy
        all_parents = self.get_all_parents(child_type)

        return parent_type in all_parents



    def extract_signature(self, func_node):

        args = func_node.args

        positional = args.args[1:]  # skip self

        return {
            "positional": [a.arg for a in positional],
            "kwonly": [a.arg for a in args.kwonlyargs],
            "defaults": len(args.defaults),
            "vararg": args.vararg.arg if args.vararg else None,
            "kwarg": args.kwarg.arg if args.kwarg else None,
            "annotations": {
                a.arg: self.get_source(a.annotation)
                for a in positional
                if a.annotation
            },
        }


    def visit_ClassDef(self, node):

        self.classes[node.name] = node

        parents = []

        for b in node.bases:

            if isinstance(b, ast.Name):
                parents.append(b.id)

            elif isinstance(b, ast.Attribute):
                parents.append(b.attr)

        self.inheritance[node.name] = parents

        if AbstractClassHelper.is_abstract_class(node):
            self.abstract_classes.add(node.name)

        self.current_class = node.name

        self.generic_visit(node)

        self.current_class = None

    def visit_FunctionDef(self, node):

        self._process_function(node)

    def visit_AsyncFunctionDef(self, node):

        self._process_function(node)


    def _process_function(self, node):

        if self.current_class is None:
            return

        all_parents = self.get_all_parents(self.current_class)

        for parent_name in all_parents:

            if parent_name not in self.classes:
                continue

            parent_class = self.classes[parent_name]

            parent_methods = {
                p.name: p
                for p in parent_class.body
                if isinstance(
                    p,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
            }

            if node.name in parent_methods:

                parent_method = parent_methods[node.name]

                self.compare_methods(
                    node,
                    parent_method,
                    parent_name,
                )

        self.generic_visit(node)



    def compare_methods(
        self,
        child,
        parent,
        parent_name,
    ):

        parent_is_abstract = (
            AbstractClassHelper.is_abstract_method(parent)
        )

        child_sig = self.extract_signature(child)
        parent_sig = self.extract_signature(parent)

        # positional parameter count
        if len(child_sig["positional"]) != len(parent_sig["positional"]):

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' overrides "
                    f"'{parent_name}' with different "
                    f"parameter count."
                ),
                "High",
            )

        # keyword-only parameters
        if child_sig["kwonly"] != parent_sig["kwonly"]:

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' changes "
                    f"keyword-only parameters."
                ),
            )

        # defaults
        if child_sig["defaults"] < parent_sig["defaults"]:

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' removes "
                    f"default parameters from parent."
                ),
            )

        # *args
        if child_sig["vararg"] != parent_sig["vararg"]:

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' changes "
                    f"*args usage."
                ),
            )

        # **kwargs
        if child_sig["kwarg"] != parent_sig["kwarg"]:

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' changes "
                    f"**kwargs usage."
                ),
            )


        for param in parent_sig["annotations"]:

            p_type = parent_sig["annotations"].get(param)

            c_type = child_sig["annotations"].get(param)

            if p_type and c_type:

                # child must accept broader types
                if (
                    c_type != p_type
                    and not self.is_subtype(
                        p_type,
                        c_type,
                    )
                ):

                    self.add_violation(
                        child,
                        (
                            f"LSP: parameter '{param}' "
                            f"in '{child.name}' violates "
                            f"contravariance "
                            f"('{p_type}' -> '{c_type}')."
                        ),
                        "High",
                    )

        c_return = (
            self.get_source(child.returns)
            if child.returns
            else None
        )

        p_return = (
            self.get_source(parent.returns)
            if parent.returns
            else None
        )

        if p_return and c_return:

            if not self.is_subtype(
                c_return,
                p_return,
            ):

                self.add_violation(
                    child,
                    (
                        f"LSP: '{child.name}' changes "
                        f"return type "
                        f"from '{p_return}' "
                        f"to '{c_return}'."
                    ),
                    "High",
                )


        def decorator_names(func):

            names = set()

            for d in func.decorator_list:

                if isinstance(d, ast.Name):
                    names.add(d.id)

                elif isinstance(d, ast.Attribute):
                    names.add(d.attr)

            return names

        child_decorators = decorator_names(child)
        parent_decorators = decorator_names(parent)

        important = {"staticmethod", "classmethod"}

        if (
            child_decorators & important
            != parent_decorators & important
        ):

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' changes "
                    f"method binding type "
                    f"(staticmethod/classmethod)."
                ),
            )


        if not parent_is_abstract:

            for n in ast.walk(child):

                if isinstance(n, ast.Raise):

                    exc_name = exc_name_from_raise(n)

                    if exc_name == "NotImplementedError":

                        self.add_violation(
                            child,
                            (
                                f"LSP: '{child.name}' "
                                f"raises NotImplementedError "
                                f"while overriding "
                                f"concrete parent method."
                            ),
                            "High",
                        )


        if not parent_is_abstract:

            parent_exceptions = set()

            child_exceptions = set()

            for n in ast.walk(parent):

                if isinstance(n, ast.Raise):

                    exc = exc_name_from_raise(n)

                    if exc:
                        parent_exceptions.add(exc)

            for n in ast.walk(child):

                if isinstance(n, ast.Raise):

                    exc = exc_name_from_raise(n)

                    if exc:
                        child_exceptions.add(exc)

            new_exceptions = (
                child_exceptions
                - parent_exceptions
            )

            for exc in new_exceptions:

                self.add_violation(
                    child,
                    (
                        f"LSP: '{child.name}' introduces "
                        f"new exception '{exc}'."
                    ),
                )


        # detect always-raising methods
        if len(child.body) == 1:

            stmt = child.body[0]

            if isinstance(stmt, ast.Raise):

                self.add_violation(
                    child,
                    (
                        f"LSP: '{child.name}' only raises "
                        f"an exception and removes "
                        f"parent behavior."
                    ),
                    "High",
                )

        # detect strengthened preconditions
        for n in ast.walk(child):

            if isinstance(n, ast.Assert):

                self.add_violation(
                    child,
                    (
                        f"LSP: '{child.name}' introduces "
                        f"additional assertions "
                        f"(stronger preconditions)."
                    ),
                )

            if isinstance(n, ast.If):

                for body_stmt in n.body:

                    if isinstance(body_stmt, ast.Raise):

                        self.add_violation(
                            child,
                            (
                                f"LSP: '{child.name}' may "
                                f"introduce stricter runtime "
                                f"checks."
                            ),
                        )

        parent_has_return = any(
            isinstance(n, ast.Return)
            and n.value is not None
            for n in ast.walk(parent)
        )

        child_has_return = any(
            isinstance(n, ast.Return)
            and n.value is not None
            for n in ast.walk(child)
        )

        if parent_has_return and not child_has_return:

            self.add_violation(
                child,
                (
                    f"LSP: '{child.name}' removes "
                    f"non-None return behavior."
                ),
                "High",
            )


def analyze_code(code_str):

    tree = ast.parse(code_str)

    detector = LSPDetector()

    detector.visit(tree)

    return detector.violations


def get_lsp_report(code_str: str):

    try:

        tree = ast.parse(code_str)

        detector = LSPDetector()

        detector.visit(tree)

        if not detector.violations:

            return {
                "status": "Pass",
                "reason": (
                    "Subclasses maintain "
                    "LSP compatibility."
                ),
                "suggestion": "N/A",
            }

        first = detector.violations[0]

        return {
            "status": "Violation",
            "reason": first["message"],
            "severity": first["severity"],
            "line": first["line"],
            "suggestion": (
                "Keep subclass behavior compatible "
                "with parent contracts."
            ),
        }

    except Exception as e:

        return {
            "status": "Error",
            "reason": str(e),
            "suggestion": (
                "Check parser compatibility."
            ),
        }


if __name__ == "__main__":

    code = """

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

"""

    violations = analyze_code(code)

    for v in violations:
        print(v)