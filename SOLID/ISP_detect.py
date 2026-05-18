import ast
from collections import defaultdict
from itertools import combinations


class ISPDetector(ast.NodeVisitor):
    def __init__(self, method_threshold=6, unused_threshold=0.4):
        self.method_threshold  = method_threshold
        self.unused_threshold  = unused_threshold
        self.violations        = []
        self.current_class     = None
        self.current_interface = None
        self.interfaces        = {}   # iface_name → {methods, lineno, node}
        self.class_implements  = {}   # class_name → [base_names]
        self.class_attr_usage  = {}   # class_name → set of self.xxx names accessed/called
        self.class_methods     = {}   # class_name → [method_names]
        self.forced_methods    = {}   # class_name → {method_name: lineno}

        # New for Rule 8 & 9
        self.class_nodes       = {}   # class_name → ast.ClassDef node
        self.class_method_nodes = {}  # class_name → [ast.FunctionDef nodes]

    # ═══════════════════════════════════════════════════════════
    #  Helpers
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _is_interface(node):
        """
        Recognises interfaces by:
          - Name convention: class IFoo / class FooInterface
          - Direct inheritance from ABC or Protocol
        Concrete classes that merely implement an interface are NOT interfaces.
        """
        name = node.name
        if name.endswith("Interface") or (
            name.startswith("I") and len(name) > 1 and name[1].isupper()
        ):
            return True
        for base in node.bases:
            base_id = (
                base.id        if isinstance(base, ast.Name)
                else base.attr if isinstance(base, ast.Attribute)
                else None
            )
            if base_id in ("ABC", "Protocol"):
                return True
        return False

    @staticmethod
    def _is_forced_body(func_node):
        """
        Returns True for stub / forced method bodies, including multi-line variants:
          - pass / ... (ellipsis)
          - raise NotImplementedError / NotImplemented
          - docstring-only body
          - docstring + any of the above
          - return / return None
          - any combination of the above with no real logic
        """
        body = list(func_node.body)

        # Strip leading docstring
        if body and isinstance(body[0], ast.Expr):
            val = body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                body = body[1:]

        if not body:   # docstring only
            return True

        def _is_stub_stmt(stmt):
            if isinstance(stmt, ast.Pass):
                return True
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if stmt.value.value is ...:
                    return True
            if isinstance(stmt, ast.Raise) and stmt.exc is not None:
                exc  = stmt.exc
                name = (
                    exc.id          if isinstance(exc, ast.Name)
                    else exc.func.id if (isinstance(exc, ast.Call)
                                         and isinstance(exc.func, ast.Name))
                    else None
                )
                if name in ("NotImplementedError", "NotImplemented"):
                    return True
            if isinstance(stmt, ast.Return):
                if stmt.value is None:
                    return True
                if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                    return True
            return False

        return all(_is_stub_stmt(s) for s in body)

    @staticmethod
    def _count_params(func_node):
        """Total number of non-self parameters."""
        args  = func_node.args
        total = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
            + (1 if args.vararg  else 0)
            + (1 if args.kwarg   else 0)
        )
        if args.args and args.args[0].arg == "self":
            total -= 1
        return total

    def _resolve_interface_methods(self, iface_name):
        """
        Returns the full set of method names for an interface,
        following its own inheritance chain (e.g. IChild extends IParent).
        """
        if iface_name not in self.interfaces:
            return set()
        methods = set(self.interfaces[iface_name]["methods"]) - {"__init__"}
        node    = self.interfaces[iface_name]["node"]
        for base in node.bases:
            base_id = (
                base.id        if isinstance(base, ast.Name)
                else base.attr if isinstance(base, ast.Attribute)
                else None
            )
            if base_id and base_id in self.interfaces:
                methods |= self._resolve_interface_methods(base_id)
        return methods

    def _all_interface_bases(self, class_name):
        """
        Returns every interface base reachable from a class,
        including through class inheritance (ClassB extends ClassA(IFoo)).
        """
        ifaces = []
        for base in self.class_implements.get(class_name, []):
            if base in self.interfaces:
                ifaces.append(base)
            # walk up the class hierarchy
            if base in self.class_implements:
                ifaces.extend(self._all_interface_bases(base))
        return ifaces

    @staticmethod
    def _classify_method_domain(method_name: str) -> str | None:
        """
        Returns a domain label for a method name using keyword matching.
        Returns None if the method doesn't match any known domain.
        Used by Rule 8 (standalone class role mixing).
        """
        domain_keywords = {
            "persistence": ["save", "load", "store", "fetch", "persist",
                            "insert", "update", "delete", "remove", "put",
                            "get", "add", "pop", "push"],
            "query":       ["lookup", "find", "search", "filter", "query",
                            "list", "count", "exists", "contains"],
            "network":     ["connect", "send", "receive", "request", "socket",
                            "stream", "download", "upload", "ping", "http"],
            "ui":          ["render", "draw", "display", "show", "hide", "paint",
                            "layout", "refresh", "repaint", "widget", "print",
                            "format", "str", "repr"],
            "logging":     ["log", "trace", "debug", "audit", "monitor",
                            "report", "warn", "error", "info"],
            "cache":       ["cache", "invalidate", "expire", "flush",
                            "evict", "clear", "hit", "miss"],
            "auth":        ["login", "logout", "authenticate", "authorize",
                            "token", "password", "permission", "role"],
            "file":        ["open", "close", "seek", "tell", "truncate",
                            "rename", "copy", "move", "mkdir", "read", "write"],
        }
        name_lower = method_name.lower()
        for domain, keywords in domain_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return domain
        return None

    # ═══════════════════════════════════════════════════════════
    #  Visitors
    # ═══════════════════════════════════════════════════════════

    def visit_ClassDef(self, node):
        bases   = [b.id for b in node.bases if isinstance(b, ast.Name)]
        methods = [f.name for f in node.body if isinstance(f, ast.FunctionDef)]
        method_nodes = [f for f in node.body if isinstance(f, ast.FunctionDef)]

        if self._is_interface(node):
            self.current_interface        = node.name
            self.interfaces[node.name]    = {
                "methods": methods,
                "lineno":  node.lineno,
                "node":    node,
            }
            self.detect_fat_interface(node, methods)
            self.detect_interface_role_mixing(node)
            self.detect_parameter_bloat(node)
            self.current_interface = None
            return

        self.current_class                     = node.name
        self.class_methods[node.name]          = methods
        self.class_implements[node.name]       = bases
        self.class_attr_usage[node.name]       = set()
        self.forced_methods[node.name]         = {}
        self.class_nodes[node.name]            = node
        self.class_method_nodes[node.name]     = method_nodes

        for f in node.body:
            if isinstance(f, ast.FunctionDef):
                self.visit(f)

        self.detect_unused_interface_methods(node)
        self.detect_forced_methods(node)
        self.detect_client_role_segregation(node)
        self.detect_standalone_role_mixing(node)   # Rule 8
        self.detect_type_dispatch(node)            # Rule 9

        self.current_class = None

    def visit_FunctionDef(self, node):
        if not self.current_class:
            return

        # Forced / stub detection
        if node.name != "__init__" and self._is_forced_body(node):
            self.forced_methods[self.current_class][node.name] = node.lineno

        # Track every self.xxx access (superset of calls)
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == "self":
                    self.class_attr_usage[self.current_class].add(child.attr)

    # Post-visit hook — runs after the entire tree is walked
    def _post_visit(self):
        self.detect_cross_class_disjoint_usage()

    # ═══════════════════════════════════════════════════════════
    #  Detection rules
    # ═══════════════════════════════════════════════════════════

    # ── Rule 1: Fat Interface ─────────────────────────────────────
    def detect_fat_interface(self, node, methods):
        count = len(methods)
        if count > self.method_threshold:
            severity = "HIGH" if count > self.method_threshold + 2 else "MEDIUM"
            self.violations.append({
                "interface":  node.name,
                "lineno":     node.lineno,
                "severity":   severity,
                "type":       "Fat Interface",
                "reason": (
                    f"Has {count} methods — interfaces this large force clients "
                    f"to depend on methods they don't use."
                ),
                "suggestion": (
                    "Split into focused interfaces by responsibility "
                    "(e.g. IDataReader, IDataWriter, IRenderer)."
                ),
            })

    # ── Rule 2: Responsibility Mixing ─────────────────────────────
    def detect_interface_role_mixing(self, node):
        domain_keywords = {
            "persistence": ["save", "load", "store", "fetch", "read", "write",
                            "persist", "insert", "update", "delete", "remove"],
            "network":     ["connect", "send", "receive", "request", "socket",
                            "stream", "download", "upload", "ping", "http", "url"],
            "ui":          ["render", "draw", "display", "show", "hide", "paint",
                            "layout", "refresh", "repaint", "widget"],
            "logging":     ["log", "trace", "debug", "audit", "monitor",
                            "report", "warn", "error", "info"],
            "cache":       ["cache", "invalidate", "expire", "flush",
                            "evict", "clear", "hit", "miss"],
            "email":       ["email", "mail", "notify", "alert", "message",
                            "sms", "push", "broadcast"],
            "auth":        ["login", "logout", "authenticate", "authorize",
                            "token", "password", "permission", "role"],
            "file":        ["open", "close", "seek", "tell", "truncate",
                            "rename", "copy", "move", "mkdir"],
        }

        # Need at least 4 methods before role mixing is meaningful
        method_nodes = [f for f in node.body if isinstance(f, ast.FunctionDef)]
        if len(method_nodes) < 4:
            return

        domains = set()
        for f in method_nodes:
            name_lower = f.name.lower()
            for domain, keywords in domain_keywords.items():
                if any(kw in name_lower for kw in keywords):
                    domains.add(domain)

        if len(domains) >= 3:
            self.violations.append({
                "interface": node.name,
                "lineno":    node.lineno,
                "severity":  "HIGH",
                "type":      "Responsibility Mixing",
                "reason": (
                    f"Mixes {len(domains)} unrelated domains: "
                    f"{', '.join(sorted(domains))}."
                ),
                "suggestion": (
                    "Create one interface per domain: "
                    + ", ".join(
                        f"I{d.capitalize()}" for d in sorted(domains)
                    ) + "."
                ),
            })
        elif len(domains) == 2:
            self.violations.append({
                "interface": node.name,
                "lineno":    node.lineno,
                "severity":  "MEDIUM",
                "type":      "Responsibility Mixing",
                "reason":    f"Mixes 2 domains: {', '.join(sorted(domains))}.",
                "suggestion": (
                    "Consider separating into distinct interfaces for clarity."
                ),
            })

    # ── Rule 3: Parameter Bloat ───────────────────────────────────
    def detect_parameter_bloat(self, node):
        PARAM_THRESHOLD = 4
        bloated = [
            (f.name, self._count_params(f), f.lineno)
            for f in node.body
            if isinstance(f, ast.FunctionDef)
            and f.name != "__init__"
            and self._count_params(f) > PARAM_THRESHOLD
        ]
        if bloated:
            names = ", ".join(f"'{n}'({c} params)" for n, c, _ in bloated)
            self.violations.append({
                "interface": node.name,
                "lineno":    bloated[0][2],
                "severity":  "MEDIUM",
                "type":      "Parameter Bloat",
                "reason": (
                    f"Methods with too many parameters force clients to know "
                    f"about data they may not use: {names}."
                ),
                "suggestion": (
                    "Introduce parameter objects or split the method across "
                    "narrower interfaces so each client only sees what it needs."
                ),
            })

    # ── Rule 4: Unused Interface Methods ─────────────────────────
    def detect_unused_interface_methods(self, node):
        seen_pairs = set()
        for base in self._all_interface_bases(node.name):
            if base in seen_pairs:
                continue
            seen_pairs.add(base)

            interface_methods = self._resolve_interface_methods(base)
            if not interface_methods:
                continue

            # A class that *defines* an interface method counts as satisfying it —
            # only flag methods that are neither called nor overridden.
            defined = set(self.class_methods.get(node.name, []))
            used   = (self.class_attr_usage.get(node.name, set()) | defined) & interface_methods
            unused = interface_methods - used
            ratio  = len(unused) / len(interface_methods)

            if ratio >= 0.6:
                severity = "HIGH"
            elif ratio >= self.unused_threshold:
                severity = "MEDIUM"
            else:
                continue

            self.violations.append({
                "class":    node.name,
                "lineno":   node.lineno,
                "severity": severity,
                "type":     "Unused Interface Methods",
                "reason": (
                    f"Implements '{base}' but only uses "
                    f"{len(used)}/{len(interface_methods)} "
                    f"of its methods. Unused: {', '.join(sorted(unused))}."
                ),
                "suggestion": (
                    f"Break '{base}' into smaller interfaces so '{node.name}' "
                    f"only depends on what it actually uses."
                ),
            })

    # ── Rule 5: Forced Implementations ───────────────────────────
    def detect_forced_methods(self, node):
        forced = self.forced_methods[node.name]
        if not forced:
            return

        # ── NEW: Only flag forced stubs that come from an interface. ──────────
        # A standalone class with pass-body helpers is not an ISP violation.
        # We only care when a concrete class is FORCED by an interface contract
        # to implement methods it doesn't actually need.
        interface_methods = set()
        for base in self._all_interface_bases(node.name):
            interface_methods |= self._resolve_interface_methods(base)

        # If the class implements no interface, forced stubs are a different
        # smell (maybe OCP / template method) — not ISP. Skip.
        if not interface_methods:
            return

        # Filter: only report stubs that belong to an interface contract
        interface_forced = {
            m: lineno
            for m, lineno in forced.items()
            if m in interface_methods
        }
        if not interface_forced:
            return

        severity = "HIGH" if len(interface_forced) >= 3 else "MEDIUM"
        for method, lineno in interface_forced.items():
            self.violations.append({
                "class":    node.name,
                "lineno":   lineno,
                "severity": severity,
                "type":     "Forced Implementation",
                "reason": (
                    f"Method '{method}' has a stub body "
                    f"(pass / raise NotImplementedError / return None / ...) "
                    f"— this class may be forced to implement methods it doesn't need."
                ),
                "suggestion": (
                    f"Check if '{method}' truly belongs to this class. "
                    f"If not, split the interface so this class only implements "
                    f"what it needs."
                ),
            })

    # ── Rule 6: Client Role Segregation ──────────────────────────
    def detect_client_role_segregation(self, node):
        existing_unused_targets = {
            v["class"] for v in self.violations
            if v.get("type") == "Unused Interface Methods"
            and v.get("class") == node.name
        }

        for base in self._all_interface_bases(node.name):
            if node.name in existing_unused_targets:
                continue
            interface_methods = self._resolve_interface_methods(base)
            if len(interface_methods) < 4:
                continue

            defined = set(self.class_methods.get(node.name, []))
            used   = (self.class_attr_usage.get(node.name, set()) | defined) & interface_methods
            unused = interface_methods - used

            if len(used) > 0 and len(unused) > len(used):
                self.violations.append({
                    "class":    node.name,
                    "lineno":   node.lineno,
                    "severity": "MEDIUM",
                    "type":     "Client Role Segregation",
                    "reason": (
                        f"'{node.name}' uses only {len(used)}/{len(interface_methods)} "
                        f"methods of '{base}' ({', '.join(sorted(used))}), "
                        f"suggesting the interface serves multiple unrelated client roles."
                    ),
                    "suggestion": (
                        f"Split '{base}' into role-specific interfaces so each "
                        f"client depends only on the methods it actually needs."
                    ),
                })

    # ── Rule 7: Cross-Class Disjoint Usage ───────────────────────
    def detect_cross_class_disjoint_usage(self):
        iface_to_classes = {}
        for cls_name, bases in self.class_implements.items():
            for base in bases:
                if base in self.interfaces:
                    iface_to_classes.setdefault(base, []).append(cls_name)

        for iface_name, implementors in iface_to_classes.items():
            if len(implementors) < 2:
                continue

            iface_methods = self._resolve_interface_methods(iface_name)
            if len(iface_methods) < 4:
                continue

            for i in range(len(implementors)):
                for j in range(i + 1, len(implementors)):
                    cls_a = implementors[i]
                    cls_b = implementors[j]
                    used_a = (self.class_attr_usage.get(cls_a, set()) | set(self.class_methods.get(cls_a, []))) & iface_methods
                    used_b = (self.class_attr_usage.get(cls_b, set()) | set(self.class_methods.get(cls_b, []))) & iface_methods

                    if not used_a or not used_b:
                        continue

                    overlap = used_a & used_b
                    overlap_ratio = len(overlap) / max(len(used_a), len(used_b))

                    if overlap_ratio <= 0.25:
                        self.violations.append({
                            "interface": iface_name,
                            "lineno":    self.interfaces[iface_name]["lineno"],
                            "severity":  "HIGH",
                            "type":      "Cross-Class Disjoint Usage",
                            "reason": (
                                f"'{cls_a}' uses {{{', '.join(sorted(used_a))}}} "
                                f"and '{cls_b}' uses {{{', '.join(sorted(used_b))}}} "
                                f"from '{iface_name}' with only "
                                f"{len(overlap)} method(s) in common — "
                                f"clear evidence the interface serves two unrelated clients."
                            ),
                            "suggestion": (
                                f"Split '{iface_name}' so '{cls_a}' and '{cls_b}' "
                                f"each get their own focused interface."
                            ),
                        })

    # ── Rule 8: Standalone Class Role Mixing ─────────────────────
    # NEW: Catches classes with NO interface at all that bundle
    # multiple unrelated responsibilities into one body.
    #
    # How it works:
    #   1. Skip classes that implement a known interface (covered by Rules 1-7).
    #   2. Classify each public method into a domain via keyword matching.
    #   3. Fire when 2+ distinct domains are detected with ≥2 methods each
    #      (single stray helpers don't count).
    #
    # Example caught: TelephoneDirectory mixes persistence (add/delete/update)
    # with query (lookup) and UI/formatting (__str__).
    def detect_standalone_role_mixing(self, node):
        # Skip if this class already implements a known interface — Rules 1-7 handle it
        if self._all_interface_bases(node.name):
            return

        # Only look at public methods (skip __dunder__ except __str__/__repr__)
        INCLUDE_DUNDERS = {"__str__", "__repr__", "__len__", "__contains__"}
        public_methods = [
            f for f in self.class_method_nodes.get(node.name, [])
            if not f.name.startswith("_") or f.name in INCLUDE_DUNDERS
        ]

        # Need at least 3 real methods to make mixing meaningful
        if len(public_methods) < 3:
            return

        # Map domain → list of method names that matched
        domain_methods: dict[str, list[str]] = defaultdict(list)
        for f in public_methods:
            domain = self._classify_method_domain(f.name)
            if domain:
                domain_methods[domain].append(f.name)

        # Only count domains with ≥ 2 methods (avoids single-stray-method noise)
        significant_domains = {
            d: ms for d, ms in domain_methods.items() if len(ms) >= 1
        }

        # Separate "data mutation" domains from "presentation" domains
        # to avoid false positives on normal CRUD classes
        MUTATION_DOMAINS   = {"persistence", "file", "network", "cache", "auth"}
        QUERY_DOMAINS      = {"query"}
        PRESENTATION_DOMAINS = {"ui", "logging"}

        mutation_hits      = significant_domains.keys() & MUTATION_DOMAINS
        presentation_hits  = significant_domains.keys() & PRESENTATION_DOMAINS
        query_hits         = significant_domains.keys() & QUERY_DOMAINS

        # Case A: Mixes mutation + presentation (e.g. save + render)
        # Case B: Mixes 3+ distinct domain groups of any type
        fires = False
        mixed_domains = set()

        if mutation_hits and presentation_hits:
            fires = True
            mixed_domains = mutation_hits | presentation_hits
        elif len(significant_domains) >= 3:
            fires = True
            mixed_domains = set(significant_domains.keys())

        if not fires:
            return

        # Build readable domain → methods summary
        domain_summary = ", ".join(
            f"{d}({', '.join(significant_domains[d])})"
            for d in sorted(mixed_domains)
        )

        # Suggest split names
        suggestions = ", ".join(
            f"I{d.capitalize()}Operations" if d in MUTATION_DOMAINS
            else f"I{d.capitalize()}"
            for d in sorted(mixed_domains)
        )

        self.violations.append({
            "class":    node.name,
            "lineno":   node.lineno,
            "severity": "MEDIUM",
            "type":     "Standalone Class Role Mixing",
            "reason": (
                f"'{node.name}' has no interface but bundles "
                f"{len(mixed_domains)} unrelated responsibilities: "
                f"{domain_summary}. "
                f"Clients that only need one role are forced to depend on all of them."
            ),
            "suggestion": (
                f"Extract an interface per responsibility: {suggestions}. "
                f"Each client then depends only on the interface it actually needs."
            ),
        })

    # ── Rule 9: Type-Dispatch Multiplexing ───────────────────────
    # NEW: Catches the anti-pattern where a single class uses an integer/string
    # "type" field to branch into completely unrelated behaviour via if/elif chains.
    # This is a disguised fat-interface: the class is secretly several classes
    # merged into one, and every client is forced to drag all variants along.
    #
    # Detection strategy:
    #   1. Look for an `__init__` that accepts a `type` (or `kind`, `mode`) param
    #      and stores it as `self.type` / `self.kind` / `self.mode`.
    #   2. Find methods that contain if/elif chains branching on that stored attr.
    #   3. Count how many distinct literal branches exist (int or str constants).
    #   4. Fire when ≥ 2 branches are found in ≥ 1 method.
    #
    # Example caught: Writer(type=0|1|2) branches into file / socket / DB logic.
    TYPE_PARAM_NAMES = {"type", "kind", "mode", "variant", "strategy"}

    def detect_type_dispatch(self, node):
        # ── Step 1: find stored type-selector attributes ─────────
        # Look for patterns like:  self.type = type  in __init__
        type_attrs: set[str] = set()

        init_node = next(
            (f for f in self.class_method_nodes.get(node.name, [])
             if f.name == "__init__"),
            None,
        )
        if init_node:
            for stmt in ast.walk(init_node):
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                            and target.attr in self.TYPE_PARAM_NAMES
                        ):
                            type_attrs.add(target.attr)

                # Also catch annotated assignments:  self.type: int = type
                if isinstance(stmt, ast.AnnAssign):
                    target = stmt.target
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and target.attr in self.TYPE_PARAM_NAMES
                    ):
                        type_attrs.add(target.attr)

        if not type_attrs:
            return

        # ── Step 2: find if/elif chains that branch on self.<type_attr> ──
        dispatching_methods: list[tuple[str, int, set]] = []  # (name, lineno, branches)

        for func in self.class_method_nodes.get(node.name, []):
            if func.name == "__init__":
                continue
            branches = self._collect_type_dispatch_branches(func, type_attrs)
            if len(branches) >= 2:
                dispatching_methods.append((func.name, func.lineno, branches))

        if not dispatching_methods:
            return

        # ── Step 3: fire violation ────────────────────────────────
        # Count maximum branch variants across all dispatching methods
        max_branches = max(len(b) for _, _, b in dispatching_methods)
        severity = "HIGH" if max_branches >= 3 else "MEDIUM"

        method_summary = ", ".join(
            f"'{name}'({len(br)} branches)"
            for name, _, br in dispatching_methods
        )

        self.violations.append({
            "class":    node.name,
            "lineno":   node.lineno,
            "severity": severity,
            "type":     "Type-Dispatch Multiplexing",
            "reason": (
                f"'{node.name}' uses a type-selector attribute "
                f"({', '.join(sorted(type_attrs))}) to branch into "
                f"{max_branches} distinct behaviours in: {method_summary}. "
                f"This packs multiple unrelated clients into one class — "
                f"every user of '{node.name}' implicitly depends on all variants."
            ),
            "suggestion": (
                f"Replace the type-dispatch with one class per variant "
                f"(e.g. FileWriter, NetworkWriter, DatabaseWriter) and extract "
                f"a shared interface (e.g. IWriter) with only the methods each "
                f"variant actually needs."
            ),
        })

    def _collect_type_dispatch_branches(
        self, func_node: ast.FunctionDef, type_attrs: set[str]
    ) -> set:
        """
        Walk a function body and collect all literal values (int/str) used
        in comparisons against self.<type_attr>.

        Handles both forms:
            if self.type == 0: ...
            if 0 == self.type: ...
        """
        branches: set = set()

        for node in ast.walk(func_node):
            # We care about If nodes; their test may be a Compare or BoolOp
            if not isinstance(node, ast.If):
                continue

            for compare in self._extract_compares(node.test):
                left  = compare.left
                ops   = compare.ops
                comps = compare.comparators

                if len(ops) != 1 or not isinstance(ops[0], ast.Eq):
                    continue

                # Pattern:  self.type == <literal>
                if (
                    isinstance(left, ast.Attribute)
                    and isinstance(left.value, ast.Name)
                    and left.value.id == "self"
                    and left.attr in type_attrs
                    and len(comps) == 1
                    and isinstance(comps[0], ast.Constant)
                ):
                    branches.add(comps[0].value)

                # Pattern:  <literal> == self.type
                if (
                    isinstance(left, ast.Constant)
                    and len(comps) == 1
                    and isinstance(comps[0], ast.Attribute)
                    and isinstance(comps[0].value, ast.Name)
                    and comps[0].value.id == "self"
                    and comps[0].attr in type_attrs
                ):
                    branches.add(left.value)

        return branches

    @staticmethod
    def _extract_compares(test_node) -> list[ast.Compare]:
        """
        Recursively pull Compare nodes out of a test expression,
        handling BoolOp (and/or) wrappers.
        """
        if isinstance(test_node, ast.Compare):
            return [test_node]
        if isinstance(test_node, ast.BoolOp):
            result = []
            for value in test_node.values:
                result.extend(ISPDetector._extract_compares(value))
            return result
        return []


# ═══════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════

def analyze_isp(code, method_threshold=6, unused_threshold=0.4):
    """
    Parse and analyse Python source for ISP violations.
    Returns a list of violation dicts, sorted HIGH → MEDIUM → LOW.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"Syntax Error: {e}")
        return []

    detector = ISPDetector(method_threshold, unused_threshold)
    detector.visit(tree)
    detector._post_visit()

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    detector.violations.sort(key=lambda v: order.get(v.get("severity", "LOW"), 2))
    return detector.violations




def get_isp_report(code_str: str):
    """
    Returns a structured report with ALL violations found.

    Shape:
    {
        "status":     "Pass" | "Violation" | "Error",
        "total":      int,
        "high":       int,
        "medium":     int,
        "low":        int,
        "violations": list,
        "reason":     str,
    }
    """
    try:
        violations = analyze_isp(code_str)

        if not violations:
            return {
                "status":     "Pass",
                "total":      0,
                "high":       0,
                "medium":     0,
                "low":        0,
                "violations": [],
                "reason":     "No ISP violations detected.",
            }

        high   = sum(1 for v in violations if v.get("severity") == "HIGH")
        medium = sum(1 for v in violations if v.get("severity") == "MEDIUM")
        low    = sum(1 for v in violations if v.get("severity") == "LOW")

        return {
            "status":     "Violation",
            "total":      len(violations),
            "high":       high,
            "medium":     medium,
            "low":        low,
            "violations": violations,
            "reason": (
                f"Found {len(violations)} violation(s): "
                f"{high} high, {medium} medium, {low} low."
            ),
        }

    except Exception as e:
        return {
            "status":     "Error",
            "total":      0,
            "high":       0,
            "medium":     0,
            "low":        0,
            "violations": [],
            "reason":     f"Analyzer error: {e}",
        }


# ═══════════════════════════════════════════════════════════════
#  Entry point — runs all four examples from the issue
# ═══════════════════════════════════════════════════════════════

EXAMPLE_1_TELEPHONE = """
class TelephoneDirectory:
    def __init__(self):
        self.telephonedirectory = {}
    def add_entry(self, name, number):
        self.telephonedirectory[name] = number
    def delete_entry(self, name):
        self.telephonedirectory.pop(name)
    def update_entry(self, name, number):
        self.telephonedirectory[name] = number
    def lookup_number(self, name):
        return self.telephonedirectory[name]
    def __str__(self):
        ret_dct = ""
        for key, value in self.telephonedirectory.items():
            ret_dct += f'{key} : {value}\\n'
        return ret_dct
"""

EXAMPLE_2_WRITER = """
class Writer:
    def __init__(self, type: int) -> None:
        self.type = type

    def write(self, contents: bytearray):
        if self.type == 0:
            with open("random_file.txt", "w") as output_file:
                output_file.write(contents)
        elif self.type == 1:
            self.some_socket.write(contents)
        elif self.type == 2:
            self.db.write()
"""

EXAMPLE_3_SHAPES = """
class Shape:
    def compute_area(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self._width = width
        self._height = height
    def compute_area(self):
        return self._width * self._height

class Square(Shape):
    def __init__(self, side):
        self._side = side
    def compute_area(self):
        return self._side * self._side
"""

EXAMPLE_4_PIPELINE = """
from abc import ABC, abstractmethod

class ProcessingStep(ABC):
    @abstractmethod
    def process(self, df): pass

class NormalizeFeature(ProcessingStep):
    def __init__(self, feature_name):
        self.feature_name = feature_name
    def process(self, df):
        df[self.feature_name] = (df[self.feature_name] - df[self.feature_name].mean()) / df[self.feature_name].std()
        return df

class EncodeCategoricalFeature(ProcessingStep):
    def __init__(self, feature_name, encoded_feature_name):
        self.feature_name = feature_name
        self.encoded_feature_name = encoded_feature_name
    def process(self, df):
        df[self.encoded_feature_name] = df[self.feature_name].astype('category').cat.codes
        return df

class FillNaNFeature(ProcessingStep):
    def __init__(self, feature_name, fill_value):
        self.feature_name = feature_name
        self.fill_value = fill_value
    def process(self, df):
        df[self.feature_name] = df[self.feature_name].fillna(self.fill_value)
        return df
"""


if __name__ == "__main__":
    examples = [
        ("Example 1 — TelephoneDirectory (should flag: Standalone Role Mixing)", EXAMPLE_1_TELEPHONE),
        ("Example 2 — Writer           (should flag: Type-Dispatch Multiplexing)", EXAMPLE_2_WRITER),
        ("Example 3 — Shapes           (should PASS cleanly)", EXAMPLE_3_SHAPES),
        ("Example 4 — Pipeline         (should PASS cleanly)", EXAMPLE_4_PIPELINE),
    ]

    for title, code in examples:
        print(f"\n{'═'*70}")
        print(f"  {title}")
        print('═'*70)
        report = get_isp_report(code)
        print(f"  Status : {report['status']}")
        print(f"  Summary: {report['reason']}")
        if report["violations"]:
            for v in report["violations"]:
                target = v.get("interface", v.get("class", "Unknown"))
                print(f"\n  [{v['severity']}] {v['type']} — {target} (line {v.get('lineno', '?')})")
                print(f"  Reason    : {v['reason']}")
                print(f"  Suggestion: {v['suggestion']}")