"""
lsp_contract_checker.py

Static analyzer to detect Liskov Substitution Principle (LSP) violations and
contract issues in Python code:
 - Abstract class/method detection
 - Signature mismatches
 - Return-type changes / postcondition weakening
 - New exceptions introduced
 - Precondition strengthening (type checks, comparisons, early returns)
 - Numeric constraint extraction and logical contradictions / input-range narrowing

Usage:
    python lsp_contract_checker.py /path/to/python/project
"""

import ast
import os
import sys
import json
from typing import Dict, List, Tuple, Any, Optional, Set

# ---------------------------------------------------------------------
# Helpers: safe unparse (works on Python 3.9+). If ast.unparse not available,
# fall back to simple repr.
# ---------------------------------------------------------------------
def safe_unparse(node):
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        try:
            return ast.dump(node)
        except Exception:
            return str(node)

def exc_name_from_raise(node: ast.Raise) -> Optional[str]:
    # Try to get raised exception name from ast.Raise
    # Cases: raise ValueError("x") => node.exc is Call with func Name/Attribute
    exc = node.exc
    if exc is None:
        return None
    # If it's a Call, get func
    func = exc.func if isinstance(exc, ast.Call) else exc
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return safe_unparse(func)

# ---------------------------------------------------------------------
# Abstract Detection
# ---------------------------------------------------------------------
class AbstractClassHelper:
    @staticmethod
    def is_abstract_method(node: ast.FunctionDef) -> bool:
        # 1. Decorated with @abstractmethod (Name or Attribute)
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id == "abstractmethod":
                return True
            if isinstance(d, ast.Attribute) and d.attr == "abstractmethod":
                return True

        # 2. Method body is a single 'pass'
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            return True

        # 3. Method raises NotImplementedError anywhere
        for n in ast.walk(node):
            if isinstance(n, ast.Raise):
                name = exc_name_from_raise(n)
                if name == "NotImplementedError":
                    return True

        # 4. Docstring hints
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

# ---------------------------------------------------------------------
# LSP Detector (integrated)
# ---------------------------------------------------------------------
class LSPDetector(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.classes: Dict[str, ast.ClassDef] = {}
        self.inheritance: Dict[str, List[str]] = {}
        self.current_class: Optional[str] = None
        self.violations: List[str] = []
        self.abstract_classes: Set[str] = set()

    def add_violation(self, node: ast.AST, msg: str):
        lineno = getattr(node, "lineno", "?")
        self.violations.append(f"{self.filename}:{lineno}: {msg}")

    # ---- Visit classes ----
    def visit_ClassDef(self, node: ast.ClassDef):
        name = node.name
        self.classes[name] = node

        # record simple parent names (Name or Attribute)
        parents = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                parents.append(b.id)
            elif isinstance(b, ast.Attribute):
                # e.g., abc.ABC
                parents.append(b.attr)
            else:
                parents.append(safe_unparse(b))
        self.inheritance[name] = parents

        # detect abstract classes
        if AbstractClassHelper.is_abstract_class(node):
            self.abstract_classes.add(name)

        # process methods with context
        prev = self.current_class
        self.current_class = name
        self.generic_visit(node)
        self.current_class = prev

    # ---- Visit functions (methods) ----
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.current_class is None:
            # module-level function
            return

        cls = self.current_class
        parents = self.inheritance.get(cls, [])
        for parent in parents:
            # only compare if parent defined in same file's AST map (cross-file not supported)
            parent_node = self.classes.get(parent)
            if not parent_node:
                continue
            parent_methods = {p.name: p for p in parent_node.body if isinstance(p, ast.FunctionDef)}
            if node.name in parent_methods:
                parent_method = parent_methods[node.name]
                self.check_lsp_rules(child=node, parent=parent_method, parent_name=parent)
        # continue
        self.generic_visit(node)

    # -----------------------------------------------------------------
    # Core LSP rule checks
    # -----------------------------------------------------------------
    def check_lsp_rules(self, child: ast.FunctionDef, parent: ast.FunctionDef, parent_name: str):
        # If parent method is abstract, overriding is allowed (no signature change warnings),
        # but we still might want to check pre/postconditions in some heuristics.
        parent_is_abstract = AbstractClassHelper.is_abstract_method(parent)

        # 1. Signature mismatch (ignore if parent is abstract)
        if not parent_is_abstract:
            c_args = len(child.args.args) - 1  # exclude self
            p_args = len(parent.args.args) - 1
            if c_args != p_args:
                self.add_violation(
                    child,
                    (f"LSP VIOLATION: Method '{child.name}' in class '{self.current_class}' "
                    f"changes parameter count compared to parent '{parent_name}' ({p_args} → {c_args}).")
                )

        # 2. Return type annotation / contract weakening
        try:
            p_ret = safe_unparse(parent.returns)
            c_ret = safe_unparse(child.returns)
        except Exception:
            p_ret = None
            c_ret = None

        if (p_ret is not None) and (p_ret != c_ret):
            # If parent had a return annotation, child changing it is suspicious
            self.add_violation(
                child,
                (f"LSP VIOLATION: Method '{child.name}' return type changed from parent '{parent_name}': "
                f"{p_ret} → {c_ret}.")
            )

        # 3. Exceptions introduced
        parent_excs = self._collect_exception_names(parent)
        child_excs = self._collect_exception_names(child)
        for exc in child_excs:
            if exc == "NotImplementedError":
                # raising NotImplemented while overriding a concrete parent is violation
                if not parent_is_abstract:
                    self.add_violation(
                        child,
                        f"LSP VIOLATION: Method '{child.name}' raises NotImplementedError while overriding concrete parent '{parent_name}'."
                    )
                # if parent abstract, allowed
                continue
            if exc and exc not in parent_excs:
                self.add_violation(
                    child,
                    (f"LSP VIOLATION: Method '{child.name}' introduces new exception '{exc}' "
                     f"not raised by parent '{parent_name}'.")
                )

        # 4. Precondition strengthening detection (type checks, comparisons, early returns)
        self.detect_precondition_strengthening(child, parent, parent_name)

        # 5. Numeric constraints: logical contradictions and range narrowing
        self.detect_logical_contradictions(child, parent, parent_name)
        self.detect_input_range_narrowing(child, parent, parent_name)

        # 6. Postcondition weakening (returns)
        self.detect_postcondition_weakening(child, parent, parent_name)

    # -----------------------------------------------------------------
    # Exception helpers
    # -----------------------------------------------------------------
    def _collect_exception_names(self, func: ast.FunctionDef) -> Set[str]:
        names = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Raise):
                nm = exc_name_from_raise(n)
                if nm:
                    names.add(nm)
        return names

    # -----------------------------------------------------------------
    # Precondition extraction and detection
    # -----------------------------------------------------------------
    def extract_preconditions(self, func: ast.FunctionDef) -> List[Tuple[str, str]]:
        """
        Returns list of tuples (kind, repr) where kind in {'if', 'typecheck', 'return', 'raise'}.
        """
        preconds = []
        for node in ast.walk(func):
            if isinstance(node, ast.If):
                # use test string
                test_str = safe_unparse(node.test)
                preconds.append(("if", test_str))
                # check if this if leads to immediate return/raise inside the same branch
                for sub in node.body:
                    if isinstance(sub, ast.Raise):
                        preconds.append(("raise", exc_name_from_raise(sub) or safe_unparse(sub)))
                    if isinstance(sub, ast.Return) and sub.value is None:
                        preconds.append(("return", "early_return"))
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    preconds.append(("typecheck", safe_unparse(node)))
            if isinstance(node, ast.Return):
                if node.value is None:
                    preconds.append(("return", "return_none"))
            if isinstance(node, ast.Raise):
                nm = exc_name_from_raise(node)
                preconds.append(("raise", nm or safe_unparse(node)))
        return preconds

    def detect_precondition_strengthening(self, child: ast.FunctionDef, parent: ast.FunctionDef, parent_name: str):
        child_pre = set(self.extract_preconditions(child))
        parent_pre = set(self.extract_preconditions(parent))

        # If child has preconditions that parent does not have, flag them.
        added = child_pre - parent_pre
        for kind, text in added:
            # ignore trivial 'raise' equal to parent raising same exception (already compared above)
            msg = (f"LSP VIOLATION: Method '{child.name}' in '{self.current_class}' adds a precondition "
                f"({kind}: {text}) not present in parent '{parent_name}'.")
            self.add_violation(child, msg)

    # -----------------------------------------------------------------
    # Numeric constraint extraction + logical contradiction detection
    # -----------------------------------------------------------------
    def extract_numeric_constraints(self, func: ast.FunctionDef) -> Dict[str, Dict[str, List[float]]]:
        """
        Extracts very simple numeric comparisons into a structure:
            { var_name: {"lt": [vals], "le": [...], "gt": [...], "ge": [...]} }
        Only handles patterns like `x < 10`, `x >= 0`, `0 <= x <= 5` (single comparator).
        """
        constraints: Dict[str, Dict[str, List[float]]] = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Compare):
                # Only handle simple left being Name and comparator being Constant
                # and at most one comparator (no chain comparisons here to keep simple)
                if isinstance(node.left, ast.Name) and len(node.comparators) == 1:
                    var = node.left.id
                    comp = node.comparators[0]
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, (int, float)):
                        val = float(comp.value)
                        op_name = type(node.ops[0]).__name__  # e.g., Lt, Gt, LtE, GtE, Eq
                        if var not in constraints:
                            constraints[var] = {"lt": [], "le": [], "gt": [], "ge": []}
                        if op_name == "Lt":
                            constraints[var]["lt"].append(val)
                        elif op_name == "LtE":
                            constraints[var]["le"].append(val)
                        elif op_name == "Gt":
                            constraints[var]["gt"].append(val)
                        elif op_name == "GtE":
                            constraints[var]["ge"].append(val)
                # Also handle comparator on right (e.g., 0 <= x)
                if isinstance(node.comparators[0], ast.Name) and isinstance(node.left, ast.Constant):
                    var = node.comparators[0].id
                    comp = node.left
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, (int, float)):
                        val = float(comp.value)
                        op_name = type(node.ops[0]).__name__
                        if var not in constraints:
                            constraints[var] = {"lt": [], "le": [], "gt": [], "ge": []}
                        # Flip operators semantics for left-constant forms
                        if op_name == "Lt":
                            # left < var  => var > left
                            constraints[var]["gt"].append(val)
                        elif op_name == "LtE":
                            constraints[var]["ge"].append(val)
                        elif op_name == "Gt":
                            constraints[var]["lt"].append(val)
                        elif op_name == "GtE":
                            constraints[var]["le"].append(val)
        return constraints

    def detect_logical_contradictions(self, child: ast.FunctionDef, parent: ast.FunctionDef, parent_name: str):
        p_cons = self.extract_numeric_constraints(parent)
        c_cons = self.extract_numeric_constraints(child)

        # For each variable constrained by child and parent, check narrowing direction
        for var, cdict in c_cons.items():
            if var not in p_cons:
                # child imposes numeric constraints where parent had none -> narrowing
                self.add_violation(
                    child,
                    (f"LSP VIOLATION: Method '{child.name}' introduces numeric constraints on '{var}' "
                    f"but parent '{parent_name}' had no numeric constraints for it.")
                )
                continue
            pdict = p_cons[var]
            # check upper bounds: child's minimum upper-bound must be >= parent's minimum upper-bound (less strict)
            # we interpret: smaller upper bound => narrower domain (e.g., child lt -10 vs parent lt 0 is narrower)
            if cdict["lt"] and pdict["lt"]:
                # take most restrictive (minimum) of upper bounds
                c_ub = min(cdict["lt"])
                p_ub = min(pdict["lt"])
                if c_ub < p_ub:
                    self.add_violation(
                        child,
                        (f"LSP VIOLATION: Child narrows allowed upper-bound for '{var}' "
                        f"({c_ub} < {p_ub}) compared to parent '{parent_name}').")
                    )
            if cdict["le"] and pdict["le"]:
                c_ub = min(cdict["le"])
                p_ub = min(pdict["le"])
                if c_ub < p_ub:
                    self.add_violation(
                        child,
                        (f"LSP VIOLATION: Child narrows allowed upper-bound (<=) for '{var}' "
                        f"({c_ub} < {p_ub}) compared to parent '{parent_name}').")
                    )

            # check lower bounds: child's maximum lower-bound must be <= parent's maximum lower-bound (less strict)
            if cdict["gt"] and pdict["gt"]:
                c_lb = max(cdict["gt"])
                p_lb = max(pdict["gt"])
                if c_lb > p_lb:
                    self.add_violation(
                        child,
                        (f"LSP VIOLATION: Child raises required lower-bound for '{var}' "
                        f"({c_lb} > {p_lb}) compared to parent '{parent_name}').")
                    )
            if cdict["ge"] and pdict["ge"]:
                c_lb = max(cdict["ge"])
                p_lb = max(pdict["ge"])
                if c_lb > p_lb:
                    self.add_violation(
                        child,
                        (f"LSP VIOLATION: Child raises required lower-bound (>=) for '{var}' "
                        f"({c_lb} > {p_lb}) compared to parent '{parent_name}').")
                    )

    # -----------------------------------------------------------------
    # Type narrowing detection
    # -----------------------------------------------------------------
    def extract_type_constraints(self, func: ast.FunctionDef) -> Dict[str, str]:
        """
        Extracts simple isinstance checks: returns map var_name -> type_expr (string)
        Only keeps the last seen type check for each variable for simplicity.
        """
        types: Dict[str, str] = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                if len(node.args) >= 2:
                    var_expr = safe_unparse(node.args[0])
                    type_expr = safe_unparse(node.args[1])
                    types[var_expr] = type_expr
        return types

    def detect_input_range_narrowing(self, child: ast.FunctionDef, parent: ast.FunctionDef, parent_name: str):
        # Numeric constraints handled elsewhere; handle type narrowing here
        c_types = self.extract_type_constraints(child)
        p_types = self.extract_type_constraints(parent)
        for var, ctype in c_types.items():
            if var not in p_types:
                # child introduces a type restriction where parent had none
                self.add_violation(
                    child,
                    (f"LSP VIOLATION: Child method '{child.name}' introduces type restriction '{var}: {ctype}' "
                    f"not present in parent '{parent_name}').")
                )
            else:
                ptype = p_types[var]
                if ctype != ptype:
                    self.add_violation(
                        child,
                        (f"LSP VIOLATION: Child method '{child.name}' refines type of '{var}' from '{ptype}' to '{ctype}' "
                        f"which may be a narrowing compared to parent '{parent_name}').")
                    )

    # -----------------------------------------------------------------
    # Postcondition (return) analysis
    # -----------------------------------------------------------------
    def extract_return_patterns(self, func: ast.FunctionDef) -> Dict[str, bool]:
        """
        Detects simple return patterns: whether function ever returns None explicitly,
        whether it has any returns at all.
        """
        patterns = {"has_return": False, "none_return": False}
        for node in ast.walk(func):
            if isinstance(node, ast.Return):
                patterns["has_return"] = True
                if node.value is None:
                    patterns["none_return"] = True
        return patterns

    def detect_postcondition_weakening(self, child: ast.FunctionDef, parent: ast.FunctionDef, parent_name: str):
        # If parent return annotation exists and child changes it — already flagged above.
        # Additional check: child returns None in some code path while parent never does.
        p_patterns = self.extract_return_patterns(parent)
        c_patterns = self.extract_return_patterns(child)
        if (not p_patterns["none_return"]) and c_patterns["none_return"]:
            self.add_violation(
                child,
                (f"LSP VIOLATION: Child method '{child.name}' may return None in some paths, "
                 f"but parent '{parent_name}' never returns None (weakens postcondition).")
            )

# ---------------------------------------------------------------------
# File / Project analysis functions
# ---------------------------------------------------------------------
def analyze_file(path: str) -> Dict[str, List[str]]:
    """
    Parse the file, analyze for LSP violations among classes defined in the same file.
    Returns dictionary: {filename: [violations...]}
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return {path: [f"ERROR reading file: {e}"]}

    try:
        tree = ast.parse(source, filename=path)
    except Exception as e:
        return {path: [f"ERROR parsing file: {e}"]}

    detector = LSPDetector(path)
    detector.visit(tree)
    return {path: detector.violations} if detector.violations else {}

def analyze_project(folder: str) -> Dict[str, List[str]]:
    results: Dict[str, List[str]] = {}
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                out = analyze_file(path)
                if out:
                    # out is either {} or {path: [violations]}
                    if path in out:
                        results[path] = out[path]
    return results

# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def pretty_print_results(results: Dict[str, List[str]]):
    if not results:
        print("✔ No LSP / contract violations detected by heuristics.")
        return
    print("\n=== LSP / Contract Violations Detected ===\n")
    for file, issues in results.items():
        print(f"In file: {file}")
        for issue in issues:
            print("  -", issue)
        print()

if __name__ == "__main__":
    project = input("Enter project folder path: ").strip()
    result = analyze_project(project)

    pretty_print_results(result)

