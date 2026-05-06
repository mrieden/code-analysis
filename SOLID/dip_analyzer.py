import ast
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

_BUILTIN_TYPES: frozenset[str] = frozenset({
    "str", "int", "float", "bool", "bytes", "list", "dict",
    "tuple", "set", "frozenset", "None", "Any", "Optional",
    "Union", "Type", "Callable", "Awaitable", "Coroutine",
    "Generator", "Iterator", "Iterable", "Sequence", "Mapping",
    "MutableMapping", "MutableSequence", "ClassVar", "Final",
})

_ABSTRACT_PREFIXES: tuple[str, ...] = ("I",)
_ABSTRACT_SUFFIXES: tuple[str, ...] = ("Base", "ABC", "Abstract", "Protocol", "Interface")


def _extract_type_name(annotation: ast.expr) -> str | None:
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        return _extract_type_name(annotation.value)
    return None


def _build_class_registry(tree: ast.Module) -> tuple[set[str], set[str]]:
    abstract_classes: set[str] = set()
    concrete_classes: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        inherits_from_abstract = any(
            (isinstance(base, ast.Name) and base.id in ("ABC", "Protocol"))
            or (isinstance(base, ast.Attribute) and base.attr in ("ABC", "Protocol"))
            for base in node.bases
        )

        has_abstract_method = any(
            isinstance(item, ast.FunctionDef)
            and any(
                (isinstance(d, ast.Name) and d.id == "abstractmethod")
                or (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
                for d in item.decorator_list
            )
            for item in node.body
        )

        if inherits_from_abstract or has_abstract_method:
            abstract_classes.add(node.name)
        else:
            concrete_classes.add(node.name)

    return abstract_classes, concrete_classes


def _is_concrete(typename: str | None, abstract_classes: set[str], concrete_classes: set[str]) -> bool:
    if not typename:
        return False
    if typename in _BUILTIN_TYPES:
        return False
    if typename in abstract_classes:
        return False
    if typename in concrete_classes:
        return True
    if any(typename.startswith(p) for p in _ABSTRACT_PREFIXES):
        return False
    if any(typename.endswith(s) for s in _ABSTRACT_SUFFIXES):
        return False
    return True


class DipAnalyzer(ast.NodeVisitor):
    __slots__ = ("filename", "current_class", "violations", "abstract_classes", "concrete_classes")

    def __init__(self, filename: str, abstract_classes: set[str], concrete_classes: set[str]) -> None:
        self.filename = filename
        self.current_class: str | None = None
        self.violations: list[tuple[str, int, int, str]] = []
        self.abstract_classes = abstract_classes
        self.concrete_classes = concrete_classes

    def _check(self, typename: str | None, line: int, col: int, rule: str, message: str) -> None:
        if self._is_concrete(typename):
            self.violations.append((self.filename, line, col, f"{rule} {message}"))

    def _is_concrete(self, typename: str | None) -> bool:
        return _is_concrete(typename, self.abstract_classes, self.concrete_classes)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        previous = self.current_class
        self.current_class = node.name
        self._check_class_inheritance(node)
        self.generic_visit(node)
        self.current_class = previous

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.current_class is not None:
            self._check_method_args(node)
            self._check_return_type(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self.current_class is not None:
            typename = _extract_type_name(node.annotation)
            self._check(
                typename, node.lineno, node.col_offset,
                "DIP004",
                f"Class '{self.current_class}' has attribute annotated with concrete class '{typename}'."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_class is not None:
            typename = _extract_type_name(node.func)
            if typename and typename != self.current_class:
                self._check(
                    typename, node.lineno, node.col_offset,
                    "DIP003",
                    f"Class '{self.current_class}' directly instantiates concrete class '{typename}'."
                )
        self.generic_visit(node)

    def _check_class_inheritance(self, node: ast.ClassDef) -> None:
        for base in node.bases:
            typename = _extract_type_name(base)
            if typename and typename not in ("ABC", "Protocol") and self._is_concrete(typename):
                self.violations.append((
                    self.filename, node.lineno, node.col_offset,
                    f"DIP005 Class '{node.name}' inherits from concrete class '{typename}'."
                ))

    def _check_method_args(self, node: ast.FunctionDef) -> None:
        args = node.args.args[1:] if node.name == "__init__" else node.args.args
        rule = "DIP001" if node.name == "__init__" else "DIP002"

        for arg in args:
            if arg.annotation is None:
                continue
            typename = _extract_type_name(arg.annotation)
            self._check(
                typename, arg.lineno, arg.col_offset,
                rule,
                f"Class '{self.current_class}' depends on concrete class '{typename}' in '{node.name}'. Use an abstraction instead."
            )

    def _check_return_type(self, node: ast.FunctionDef) -> None:
        if node.returns is None:
            return
        typename = _extract_type_name(node.returns)
        self._check(
            typename, node.lineno, node.col_offset,
            "DIP006",
            f"Method '{node.name}' in '{self.current_class}' returns concrete class '{typename}'."
        )


def analyze_file(path: str) -> list[tuple[str, int, int, str]]:
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []
    abstract_classes, concrete_classes = _build_class_registry(tree)
    analyzer = DipAnalyzer(path, abstract_classes, concrete_classes)
    analyzer.visit(tree)
    return analyzer.violations


def analyze_directory(folder: str, *, max_workers: int | None = None) -> list[tuple[str, int, int, str]]:
    py_files = [
        os.path.join(root, fname)
        for root, _, files in os.walk(folder)
        for fname in files
        if fname.endswith(".py")
    ]

    results: list[tuple[str, int, int, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(analyze_file, p): p for p in py_files}
        for future in as_completed(futures):
            results.extend(future.result())

    results.sort(key=lambda v: (v[0], v[1]))
    return results


def get_dip_report(code_str: str) -> dict[str, str]:
    try:
        tree = ast.parse(code_str)
    except SyntaxError as exc:
        return {
            "status": "Error",
            "reason": f"Syntax error: {exc}",
            "suggestion": "Fix the syntax error before running the DIP analyser.",
        }

    abstract_classes, concrete_classes = _build_class_registry(tree)
    analyzer = DipAnalyzer("<string>", abstract_classes, concrete_classes)
    analyzer.visit(tree)

    if not analyzer.violations:
        return {
            "status": "Pass",
            "reason": "No concrete class dependencies detected.",
            "suggestion": "N/A",
        }

    _, line, _, msg = analyzer.violations[0]
    return {
        "status": "Violation",
        "reason": f"Line {line}: {msg}",
        "suggestion": "Inject an abstraction (interface/abstract class) instead of a concrete class.",
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dip_analyzer.py <file_or_directory>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    violations = analyze_directory(target) if os.path.isdir(target) else analyze_file(target)

    if not violations:
        print("No DIP violations found.")
    else:
        for file, line, col, msg in violations:
            print(f"{file}:{line}:{col}: {msg}")
        sys.exit(1)
