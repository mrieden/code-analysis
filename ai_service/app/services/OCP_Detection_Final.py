import ast
from typing import Optional

BUILTIN_TYPES = {"int", "str", "float", "list", "dict", "bool", "set", "tuple",
                "bytes", "bytearray", "complex", "frozenset", "memoryview",
                "object", "type", "None", "NoneType"}

# Variable names that strongly suggest type-dispatching
TYPE_DISPATCH_NAMES = {
    "type", "kind", "action", "method", "mode", "variant",
    "category", "strategy", "op", "operation", "cmd", "command",
    "role", "shape", "tag", "event_type", "msg_type", "request_type",
    "format", "protocol", "handler", "dispatch", "key", "name",
    "status", "state", "flag", "subtype", "msg_kind", "cls",
}

# Attribute access patterns that suggest type-dispatch
TYPE_DISPATCH_ATTRS = {
    "type", "kind", "action", "category", "variant", "op", "operation",
    "tag", "name", "__class__", "__name__", "mode", "format", "role",
    "status", "state", "subtype", "method", "protocol",
}

# Patterns that are clearly NOT OCP violations (safe isinstance uses)
_SAFE_EXCEPTION_TYPES = {
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "OSError", "IOError",
    "FileNotFoundError", "PermissionError", "StopIteration", "GeneratorExit",
    "SystemExit", "NotImplementedError", "OverflowError", "ZeroDivisionError",
    "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError",
    "ImportError", "ModuleNotFoundError", "NameError", "RecursionError",
}

# Action prefixes that strongly suggest type-routing when grouped in a single class
DISPATCH_PREFIXES = {
    "pay", "process", "parse", "handle", "export", "import", 
    "generate", "calculate", "render", "validate", "format", 
    "convert", "find", "search", "filter"
}


def _attr_chain(node: ast.expr) -> str:
    """Flatten an Attribute/Name access chain into a dotted string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_attr_chain(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        func = _attr_chain(node.func)
        return f"{func}(...)"
    return ""


def _is_exception_isinstance(node: ast.If) -> bool:
    """Return True if this isinstance check is inside an except block pattern."""
    test = node.test
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        test = test.operand
    if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
            and test.func.id == "isinstance"):
        return False
    if len(test.args) < 2:
        return False
    type_arg = test.args[1]
    names = []
    if isinstance(type_arg, ast.Tuple):
        names = [e.id for e in type_arg.elts if isinstance(e, ast.Name)]
    elif isinstance(type_arg, ast.Name):
        names = [type_arg.id]
    return all(n in _SAFE_EXCEPTION_TYPES or n in BUILTIN_TYPES for n in names)


def _extract_compare_names(node: ast.Compare) -> list[str]:
    """Return all Name/Attribute ids referenced in a comparison."""
    parts = [node.left] + list(node.comparators)
    result = []
    for p in parts:
        if isinstance(p, ast.Name):
            result.append(p.id.lower())
        elif isinstance(p, ast.Attribute):
            result.append(p.attr.lower())
    return result


class OCPDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations: list[dict] = []
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        # Use a stack to track variables per scope
        self._type_var_scopes: list[set[str]] = [set()]

    @property
    def _type_vars(self) -> set[str]:
        """Get type variables for the current scope."""
        return self._type_var_scopes[-1]


    def _report(self, node: ast.AST, v_type: str, severity: str, detail: str = ""):
        self.violations.append({
            "class": self.current_class,
            "function": self.current_function,
            "line": node.lineno,
            "type": v_type,
            "severity": severity,
            "detail": detail,
        })

    # ---- individual pattern checks ------------------------------------ #


    def _check_enum_dispatch(self, node: ast.If) -> bool:
        """if status == Status.RUNNING:"""
        if not isinstance(node.test, ast.Compare):
            return False
            
        parts = [node.test.left] + list(node.test.comparators)
        has_enum_like = False
        has_dispatch_var = False
        
        for part in parts:
            if isinstance(part, ast.Attribute) and isinstance(part.value, ast.Name):
                # E.g., Status.RUNNING -> 'Status' is capitalized
                if part.value.id[0].isupper() and part.value.id not in BUILTIN_TYPES:
                    has_enum_like = True
            elif isinstance(part, ast.Name) and (part.id in TYPE_DISPATCH_NAMES or part.id in self._type_vars):
                has_dispatch_var = True
                
        if has_enum_like and has_dispatch_var:
            self._report(node, "Enum Dispatch", "medium",
                        "Branching based on an Enum or Class constant. Consider the State or Strategy pattern.")
            return True
        return False

    def _check_name_type_dispatch(self, node: ast.If) -> bool:
        """if <dispatch_name> == / in / != / is ..."""
        test = node.test

        # Unwrap BoolOp: (kind == 'a' or kind == 'b') — each branch is a dispatch
        if isinstance(test, ast.BoolOp) and isinstance(test.op, (ast.Or, ast.And)):
            triggered = False
            for val in test.values:
                if isinstance(val, ast.Compare):
                    names = _extract_compare_names(val)
                    if any(n in TYPE_DISPATCH_NAMES or n in self._type_vars for n in names):
                        triggered = True
                        break
            if triggered:
                self._report(node, "IF Name Dispatch (BoolOp)", "high",
                            "Boolean chain of type-name comparisons — suggests type-based dispatch")
                return True

        if not isinstance(test, ast.Compare):
            return False

        names = _extract_compare_names(test)

        # Check direct name match
        if any(n in TYPE_DISPATCH_NAMES for n in names):
            severity = "high"
            self._report(node, "IF Name Dispatch", severity,
                        f"Condition branches on '{next(n for n in names if n in TYPE_DISPATCH_NAMES)}'"
                        " — suggests type-based dispatch")
            return True

        # Check tracked type-carrying variables
        if any(n in self._type_vars for n in names):
            self._report(node, "IF Tracked-Type Var Dispatch", "high",
                        f"Branches on variable that carries type/kind info: "
                        f"{next(n for n in names if n in self._type_vars)!r}")
            return True

        return False

    def _check_isinstance_dispatch(self, node: ast.If) -> bool:
        """if isinstance(x, SomeConcreteClass): — skip safe exception types and builtins."""
        if _is_exception_isinstance(node):
            return False

        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == "isinstance"):
            return False
        if len(test.args) < 2:
            return False
        type_arg = test.args[1]
        if isinstance(type_arg, ast.Tuple):
            types = [elt for elt in type_arg.elts if isinstance(elt, ast.Name)]
            non_builtin = [t.id for t in types
                        if t.id not in BUILTIN_TYPES and t.id not in _SAFE_EXCEPTION_TYPES]
        elif isinstance(type_arg, ast.Name):
            non_builtin = ([] if type_arg.id in BUILTIN_TYPES
                        or type_arg.id in _SAFE_EXCEPTION_TYPES else [type_arg.id])
        else:
            non_builtin = []
        if non_builtin:
            self._report(node, "isinstance Dispatch", "high",
                        f"Dispatches on concrete type(s): {', '.join(non_builtin)}")
            return True
        return False

    def _check_type_call_comparison(self, node: ast.If) -> bool:
        """if type(x) == SomeClass / if type(x).__name__ == 'Foo'"""
        test = node.test
        if not isinstance(test, ast.Compare):
            return False
        parts = [test.left] + list(test.comparators)
        for part in parts:
            chain = _attr_chain(part)
            if ".__class__" in chain or ".__name__" in chain:
                self._report(node, "type() / __class__ Dispatch", "high",
                            "Compares __class__/__name__ — hard-coded type check")
                return True
            if (isinstance(part, ast.Call)
                    and isinstance(part.func, ast.Name)
                    and part.func.id == "type"):
                self._report(node, "type() Dispatch", "high",
                            "Uses type() comparison for branching")
                return True
        # Also catch: x.__class__.__name__ == "Foo"
        for part in parts:
            if isinstance(part, ast.Attribute) and part.attr == "__name__":
                inner = part.value
                if isinstance(inner, ast.Attribute) and inner.attr == "__class__":
                    self._report(node, "__class__.__name__ Dispatch", "high",
                                "Compares __class__.__name__ string — brittle type check")
                    return True
        return False

    def _check_hasattr_dispatch(self, node: ast.If) -> bool:
        """if hasattr(x, 'some_method'): — duck-type dispatch"""
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        if (isinstance(test, ast.Call)
                and isinstance(test.func, ast.Name)
                and test.func.id == "hasattr"):
            self._report(node, "hasattr Dispatch", "medium",
                        "Uses hasattr() to branch on capability — consider protocol/ABC instead")
            return True
        return False

    def _check_getattr_dispatch(self, node: ast.If) -> bool:
        """if getattr(x, 'type', None) == 'foo':"""
        test = node.test
        if not isinstance(test, ast.Compare):
            return False
        left = test.left
        if (isinstance(left, ast.Call)
                and isinstance(left.func, ast.Name)
                and left.func.id == "getattr"):
            args = left.args
            if len(args) >= 2 and isinstance(args[1], ast.Constant):
                attr_name = str(args[1].value).lower()
                if attr_name in TYPE_DISPATCH_ATTRS:
                    self._report(node, "getattr Dispatch", "medium",
                                f"Uses getattr() on '{attr_name}' for branching")
                    return True
        return False

    def _check_callable_dispatch(self, node: ast.If) -> bool:
        """if callable(x): — dispatch on callability"""
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        if (isinstance(test, ast.Call)
                and isinstance(test.func, ast.Name)
                and test.func.id == "callable"):
            self._report(node, "callable() Dispatch", "medium",
                        "Uses callable() to branch on capability — consider a protocol or ABC")
            return True
        return False

    def _check_issubclass_dispatch(self, node: ast.If) -> bool:
        """if issubclass(T, SomeBase): — metaclass-level type dispatch"""
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == "issubclass"):
            return False
        if len(test.args) < 2:
            return False
        type_arg = test.args[1]
        if isinstance(type_arg, ast.Tuple):
            names = [e.id for e in type_arg.elts if isinstance(e, ast.Name)]
        elif isinstance(type_arg, ast.Name):
            names = [type_arg.id]
        else:
            names = []
        non_builtin = [n for n in names if n not in BUILTIN_TYPES]
        if non_builtin:
            self._report(node, "issubclass Dispatch", "high",
                        f"issubclass() dispatch on {', '.join(non_builtin)} — "
                        "prefer abstract base classes / registration")
            return True
        return False

    def _check_string_startswith_type(self, node: ast.If) -> bool:
        """if x.type.startswith('foo') or x.kind.startswith(...) — partial-string type dispatch"""
        test = node.test
        if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                and test.func.attr in ("startswith", "endswith")):
            return False
        chain = _attr_chain(test.func.value)
        last_attr = chain.split(".")[-1].lower() if "." in chain else chain.lower()
        if last_attr in TYPE_DISPATCH_ATTRS:
            self._report(node, "startswith/endswith Type Dispatch", "medium",
                        f"Partial-string dispatch on '{last_attr}' via {test.func.attr}() "
                        "— consider polymorphism or enum")
            return True
        return False

    def _check_elif_chain(self, node: ast.If) -> int:
        """Count elif depth; long chains are a strong OCP smell."""
        depth = 0
        current = node
        while current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            depth += 1
            current = current.orelse[0]
        return depth
    
    def _check_property_inspection(self, node: ast.If) -> bool:
        """
        Catches 'Tell, Don't Ask' violations: if obj.properties['color'] == 'red':
        Inspecting internal data structures instead of using polymorphism.
        """
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand

        if not isinstance(test, ast.Compare):
            return False

        # Look at what is being compared
        parts = [test.left] + list(test.comparators)
        for part in parts:
            # Catch dictionary lookups on object attributes: obj.properties['Key']
            if isinstance(part, ast.Subscript) and isinstance(part.value, ast.Attribute):
                attr_name = part.value.attr.lower()
                # If they are digging into standard data-holding attributes
                if attr_name in {"properties", "data", "attributes", "config", "meta", "info"}:
                    self._report(node, "Property Inspection (Tell, Don't Ask)", "high",
                                f"Inspecting '{part.value.attr}' externally to make decisions. "
                                "Push this logic inside the class as a method.")
                    return True
        return False

    # ------------------------------------------------------------------ #
    # Assignment tracking — find variables that carry type info            #
    # e.g. kind = obj.type  or  action = msg["action"]                    #
    # ------------------------------------------------------------------ #

    def _track_type_assignment(self, node: ast.Assign):
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            varname = target.id.lower()
            val = node.value

            # Direct: kind = obj.type / obj.kind
            if isinstance(val, ast.Attribute) and val.attr.lower() in TYPE_DISPATCH_ATTRS:
                self._type_vars.add(varname)
            # Subscript: action = msg["type"] / msg["kind"]
            elif isinstance(val, ast.Subscript):
                sl = val.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    if sl.value.lower() in TYPE_DISPATCH_ATTRS:
                        self._type_vars.add(varname)
            # getattr call: kind = getattr(obj, "type", None)
            elif (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id == "getattr" and len(val.args) >= 2
                and isinstance(val.args[1], ast.Constant)
                and str(val.args[1].value).lower() in TYPE_DISPATCH_ATTRS):
                self._type_vars.add(varname)
            # Variable name itself is a dispatch name: type = ..., kind = ...
            elif varname in TYPE_DISPATCH_NAMES:
                self._type_vars.add(varname)

    # ------------------------------------------------------------------ #
    # visitors                                                             #
    # ------------------------------------------------------------------ #

    def visit_ClassDef(self, node: ast.ClassDef):
        prev = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef):
            prev_fn = self.current_function
            self.current_function = node.name

            self._type_var_scopes.append(set())

            self.generic_visit(node)

            self._type_var_scopes.pop()
            self.current_function = prev_fn

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign):
        self._track_type_assignment(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        matched = (
            self._check_name_type_dispatch(node)
            or self._check_isinstance_dispatch(node)
            or self._check_type_call_comparison(node)
            or self._check_hasattr_dispatch(node)
            or self._check_getattr_dispatch(node)
            or self._check_callable_dispatch(node)
            or self._check_issubclass_dispatch(node)
            or self._check_string_startswith_type(node)
        )

        # Long elif chains are an OCP smell regardless of what they test
        if not matched:
            depth = self._check_elif_chain(node)
            if depth >= 2:
                severity = "high" if depth >= 4 else "medium"
                self._report(node, "Long elif Chain", severity,
                            f"elif chain of depth {depth} — consider polymorphism or a dispatch table")

        self.generic_visit(node)

    def visit_Match(self, node: ast.Match):
        """match/case — flag type-dispatch subjects; allow pure data-literal patterns."""
        subject_name = ""
        if isinstance(node.subject, ast.Name):
            subject_name = node.subject.id.lower()
        elif isinstance(node.subject, ast.Attribute):
            subject_name = node.subject.attr.lower()

        all_constants = all(
            isinstance(case.pattern, ast.MatchValue)
            and isinstance(case.pattern.value, ast.Constant)
            for case in node.cases
            if not isinstance(case.pattern, ast.MatchAs)  # ignore wildcard
        )

        # Class patterns in match — always an OCP violation
        has_class_pattern = any(
            isinstance(case.pattern, ast.MatchClass)
            for case in node.cases
        )

        if has_class_pattern:
            self._report(node, "MATCH-CASE Class Pattern Dispatch", "high",
                        "match-case with class patterns — use polymorphism or singledispatch")
            self.generic_visit(node)
            return

        is_type_subject = (subject_name in TYPE_DISPATCH_NAMES
                        or subject_name in self._type_vars)

        if is_type_subject or not all_constants:
            severity = "high" if is_type_subject else "medium"
            self._report(node, "MATCH-CASE Dispatch", severity,
                        f"match-case on '{subject_name or '?'}' — "
                        + ("type-dispatch variable" if is_type_subject
                            else ("mixed patterns" if not all_constants else "constant dispatch")))
        elif all_constants and len(node.cases) >= 3:
            # Even all-constant match with many arms is a mild OCP smell
            self._report(node, "MATCH-CASE Dispatch", "medium",
                        f"match-case with {len(node.cases)} constant arms — "
                        "consider a dispatch table")

        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict):
        """Detect type-keyed dispatch dicts: {Dog: handle_dog, Cat: handle_cat}"""
        if not node.keys:
            return
        class_name_keys = [
            k for k in node.keys
            if isinstance(k, ast.Name) and k.id and k.id[0].isupper() and k.id not in BUILTIN_TYPES
        ]
        if len(class_name_keys) >= 2:
            names = ", ".join(k.id for k in class_name_keys[:4])
            self._report(node, "Type Dispatch Dict", "medium",
                        f"Dict keyed on class names ({names}...) — possible type-dispatch table")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        """Detect dispatch dicts accessed as: HANDLERS[type(obj)] or HANDLERS[obj.type]"""
        # HANDLERS[type(x)] or DISPATCH[x.__class__]
        sl = node.slice
        if isinstance(sl, ast.Call) and isinstance(sl.func, ast.Name) and sl.func.id == "type":
            self._report(node, "Dict Subscript type() Dispatch", "high",
                        "Dict indexed by type(obj) — replace with polymorphism or singledispatch")
        elif isinstance(sl, ast.Attribute) and sl.attr in TYPE_DISPATCH_ATTRS:
            # e.g. handlers[obj.type] — only flag if the dict name looks dispatch-like
            val_chain = _attr_chain(node.value).lower()
            if any(k in val_chain for k in ("handler", "dispatch", "registry", "router",
                                            "factory", "map", "table", "lookup")):
                self._report(node, "Dict Subscript Attr Dispatch", "medium",
                            f"Dict indexed by .{sl.attr} attribute — consider polymorphism")
        self.generic_visit(node)
    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name

        # --- NEW HEURISTIC: Method Name Routing ---
        # Look for multiple methods sharing a dispatch prefix (e.g., pay_debit, pay_credit)
        method_prefixes = {}
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and not item.name.startswith("__"):
                parts = item.name.split('_')
                if len(parts) > 1:
                    prefix = parts[0].lower()
                    
                    # If it's a common dispatch word (like 'pay' or 'parse')
                    if prefix in DISPATCH_PREFIXES:
                        method_prefixes.setdefault(prefix, []).append(item.name)
                    # Catch 'find_by_x', 'search_by_y' specifically for repositories/libraries
                    elif len(parts) >= 3 and parts[1] == "by":
                        combined_prefix = f"{prefix}_by"
                        method_prefixes.setdefault(combined_prefix, []).append(item.name)

        # Flag the class if it has 2 or more methods doing the same action for different types
        for prefix, names in method_prefixes.items():
            if len(names) >= 2:
                self._report(node, "Method Name Routing", "high",
                             f"Class '{node.name}' has type-specific methods ({', '.join(names[:3])}...). "
                             "Adding a new type requires modifying this class. Use the Strategy pattern, "
                             "the Specification pattern, or polymorphism instead.")
        # ------------------------------------------

        self.generic_visit(node)
        self.current_class = prev_class

    def _in_isinstance_context(self, node: ast.Call) -> bool:
        """Heuristic: type() call that's an arg to isinstance is not a dispatch."""
        return False  # AST parent traversal not available; handled in visit_If

    # ------------------------------------------------------------------ #
    # Module-level: scan for assignment of type-dispatch variable names    #
    # ------------------------------------------------------------------ #

    def visit_Module(self, node: ast.Module):
        # Pre-scan module for assignments that look like type-dispatch setup
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                self._track_type_assignment(child)
        self.generic_visit(node)


# ------------------------------------------------------------------ #
# Public API                                                          #
# ------------------------------------------------------------------ #

def detect_ocp_violations_from_file(filename: str) -> list[dict]:
    with open(filename, "r", encoding="utf-8") as f:
        code = f.read()
    tree = ast.parse(code)
    detector = OCPDetector()
    detector.visit(tree)
    return detector.violations


def get_ocp_report(code_str: str) -> dict:
    """
    Returns a single-violation summary dict compatible with the original API,
    plus a `violations` key listing all found issues.
    """
    try:
        tree = ast.parse(code_str)
        detector = OCPDetector()
        detector.visit(tree)

        if not detector.violations:
            return {
                "status": "Pass",
                "reason": "No type-based dispatching detected.",
                "violations": [],
            }

        high = [v for v in detector.violations if v["severity"] == "high"]
        top = high[0] if high else detector.violations[0]

        location = f"line {top['line']}"
        if top["class"]:
            location += f" in class {top['class']}"
        if top["function"]:
            location += f" / {top['function']}()"

        return {
            "status": "Violation",
            "reason": f"{location} [{top['type']}]: {top['detail']}",
            "violations": detector.violations,
        }
    except SyntaxError as e:
        return {
            "status": "Error",
            "reason": f"Syntax error: {e}",
            "violations": [],
        }
    except Exception as e:
        return {
            "status": "Pass",
            "reason": "no violations detected ",
            "violations": [],
        }


def _suggestion_for(v_type: str) -> str:
    suggestions = {
        "IF Name Dispatch":                     "Replace if/elif chains with polymorphism — move behaviour into subclasses or a strategy object.",
        "IF Name Dispatch (BoolOp)":            "Boolean chains of type comparisons are a dispatch table in disguise — use a dict or polymorphism.",
        "IF Tracked-Type Var Dispatch":         "Variable carries type/kind info; replace branching on it with polymorphism or a dispatch dict.",
        "isinstance Dispatch":                  "Use polymorphism or register-based dispatch (functools.singledispatch) instead of isinstance().",
        "issubclass Dispatch":                  "issubclass() dispatch belongs in a registry; use ABCs or singledispatch instead.",
        "type() Dispatch":                      "Avoid comparing type() directly; use isinstance() at most, or better, polymorphism.",
        "type() / __class__ Dispatch":          "Avoid __class__ comparisons; rely on polymorphism or ABCs.",
        "__class__.__name__ Dispatch":          "String-based class name checks are fragile; use isinstance() or polymorphism.",
        "hasattr Dispatch":                     "Define a shared interface/Protocol so callers don't need to inspect capabilities.",
        "callable() Dispatch":                  "Use a Protocol with __call__ rather than checking callability at runtime.",
        "getattr Dispatch":                     "Centralise type metadata in a base class rather than probing attributes at call sites.",
        "startswith/endswith Type Dispatch":    "Partial-string type matching is brittle; use an enum or subclass hierarchy.",
        "Long elif Chain":                      "Long elif chains are hard to extend; replace with a dispatch table or polymorphic calls.",
        "MATCH-CASE Dispatch":                  "Match-case over types/roles violates OCP; prefer visitor pattern or singledispatch.",
        "MATCH-CASE Class Pattern Dispatch":    "Class pattern match-case is an explicit type dispatch; use the Visitor pattern or singledispatch.",
        "Type Dispatch Dict":                   "A class-keyed dict is a manual vtable; consider using singledispatch or subclass registration.",
        "Dict Subscript type() Dispatch":       "Indexing a dict by type(obj) is a dispatch table — use singledispatch or polymorphism.",
        "Dict Subscript Attr Dispatch":         "Routing through a dict keyed on .type/.kind — consider polymorphism or a registry.",
    }
    return suggestions.get(v_type, "Use polymorphism or strategy pattern instead of type-based branching.")

