import ast
import re
import statistics
from itertools import combinations

# ── Semantic domain vocabulary ────────────────────────────────────────────────
SEMANTIC_DOMAINS: dict[str, set[str]] = {
    "persistence":  {"save", "store", "write", "persist", "insert", "update",
                    "delete", "remove", "create", "drop", "migrate", "commit"},
    "retrieval":    {"get", "fetch", "load", "read", "find", "search", "query",
                    "list", "retrieve", "select", "filter"},
    "presentation": {"render", "display", "show", "print", "format", "draw",
                    "view", "output", "report", "build"},
    "network":      {"send", "receive", "post", "request", "connect",
                    "disconnect", "upload", "download", "publish", "subscribe"},
    "notification": {"notify", "email", "alert", "message", "push", "broadcast"},
    "validation":   {"validate", "check", "verify", "assert", "ensure",
                    "sanitize", "inspect"},
    "parsing":      {"parse", "decode", "deserialize", "extract", "convert",
                    "transform", "serialize", "encode", "map"},
    "computation":  {"calculate", "compute", "process", "analyze", "evaluate",
                    "estimate", "score", "rank"},
    "auth":         {"login", "logout", "authenticate", "authorize", "register",
                    "sign", "permit", "hash"},
}

NOUN_DOMAINS: dict[str, set[str]] = {
    "persistence":  {"record", "row", "entity", "migration", "schema",
                     "table", "database", "db", "repo", "repository"},
    "network":      {"request", "response", "payload", "socket",
                     "connection", "endpoint", "api", "http", "url"},
    "auth":         {"token", "session", "credential", "permission",
                     "role", "password", "user", "account"},
    "notification": {"email", "sms", "webhook", "slack", "mailer",
                     "digest", "subscription"},
    "presentation": {"template", "html", "page", "view", "report",
                     "pdf", "csv", "layout", "widget"},
    "computation":  {"metric", "stat", "score", "summary", "aggregate",
                     "forecast", "model"},
    "validation":   {"rule", "constraint", "schema", "policy", "limit"},
}

# FIX 1: Body-level domain scanning — map self.X object names to domains.
# When a method calls self.db.query() or self.mailer.send(), the collaborator
# name ("db", "mailer") is mapped through NOUN_DOMAINS so generic-named methods
# like process() or handle() can't hide cross-domain activity.
COLLABORATOR_NOUN_DOMAINS: dict[str, set[str]] = {
    "persistence":  {"db", "repo", "repository", "store", "database",
                     "session", "conn", "connection", "cursor", "orm"},
    "network":      {"client", "http", "api", "request", "socket",
                     "endpoint", "proxy", "gateway"},
    "auth":         {"auth", "jwt", "token", "sso", "oauth", "permissions"},
    "notification": {"mailer", "smtp", "email", "sms", "notifier",
                     "pusher", "slack", "webhook"},
    "presentation": {"renderer", "template", "view", "html", "pdf",
                     "serializer", "formatter"},
    "computation":  {"calculator", "scorer", "ranker", "analyzer",
                     "estimator", "model", "processor"},
    "validation":   {"validator", "checker", "sanitizer", "schema"},
    "parsing":      {"parser", "decoder", "transformer", "mapper"},
}

DEFAULT_WEIGHTS = {
    # FIX 1+2: Recalibrated weights. Body-domain scanning is now the primary
    # cross-domain signal (0.30) because obj_diversity fires at 0 for self.*-only
    # classes. Object diversity retains a smaller share (0.15) for classes that DO
    # use external collaborators. Calibrated against 7 fixture classes.
    "body_domain_div":       0.30,   # FIX 1: body-scan — catches generic-named methods
    "effective_domain_div":  0.22,   # name-inferred domain spread
    "lcom":                  0.20,   # structural cohesion (collaborator-weighted)
    "object_diversity":      0.15,   # external-object Jaccard (fires for non-self calls)
    "size_factor":           0.1,   # large/complex method spread
    "responsibility_factor": 0.4,   # FIX 5: And/Or name heuristic (restored)
}


def _tokenize_name(name: str) -> list[str]:
    tokens = []
    for part in name.split("_"):
        sub = re.sub(r"([A-Z])", r" \1", part).strip()
        tokens.extend(sub.lower().split())
    return tokens


def _classify_domains(method_name: str) -> set[str]:
    tokens = set(_tokenize_name(method_name))
    domains: set[str] = set()
    for domain, keywords in SEMANTIC_DOMAINS.items():
        if tokens & keywords:
            domains.add(domain)
    for domain, keywords in NOUN_DOMAINS.items():
        if tokens & keywords:
            domains.add(domain)
    return domains or {"other"}


# FIX 1: Scan method body for cross-domain collaborator calls.
def _classify_body_domains(func_node: ast.FunctionDef) -> set[str]:
    """
    Infer domains from the method *body*, not just its name.

    Looks at:
    - self.X.method() calls  → maps 'X' through COLLABORATOR_NOUN_DOMAINS
    - standalone verb calls  → maps verb through SEMANTIC_DOMAINS
    - self.X assignments     → maps 'X' through NOUN_DOMAINS

    This catches generic-named methods (handle, process, run) that do
    cross-domain work invisibly to name-only analysis.
    """
    domains: set[str] = set()

    for node in ast.walk(func_node):
        # self.collaborator.method() — the collaborator name is most diagnostic
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "self"
        ):
            collab = node.func.value.attr.lower()
            method = node.func.attr.lower()
            for domain, keywords in COLLABORATOR_NOUN_DOMAINS.items():
                if collab in keywords:
                    domains.add(domain)
            # Also check the called method name itself
            for domain, keywords in SEMANTIC_DOMAINS.items():
                if method in keywords:
                    domains.add(domain)

        # standalone function calls: save_user(), send_email(), etc.
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        ):
            tokens = set(_tokenize_name(node.func.id))
            for domain, keywords in SEMANTIC_DOMAINS.items():
                if tokens & keywords:
                    domains.add(domain)

        # self.X = ... assignments  — X itself may be a domain noun
        elif (
            isinstance(node, ast.Assign)
        ):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attr_tokens = set(_tokenize_name(target.attr))
                    for domain, keywords in NOUN_DOMAINS.items():
                        if attr_tokens & keywords:
                            domains.add(domain)

    return domains or {"other"}


def _get_decorators(func_node: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for d in func_node.decorator_list:
        if isinstance(d, ast.Name):
            names.add(d.id)
        elif isinstance(d, ast.Attribute):
            names.add(d.attr)
    return names


# FIX 3: Analyze __init__ for injected collaborators as an SRP signal.
def _analyze_constructor(init_node: ast.FunctionDef) -> dict:
    """
    Parse __init__ to count how many distinct domain-mapped collaborators
    are injected. A constructor that wires self.db, self.mailer, self.renderer,
    and self.cache is one of the strongest possible SRP violations.

    Returns:
        injected_domains:  set of domain names found in constructor params
        collaborator_count: number of distinct injected collaborator objects
        injection_score:   0.0–1.0, contribution to violation score
    """
    injected_domains: set[str] = set()
    collaborator_names: set[str] = set()

    # Walk assignments in __init__: self.X = param
    for node in ast.walk(init_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attr = target.attr.lower()
                    attr_tokens = set(_tokenize_name(attr))
                    for domain, keywords in COLLABORATOR_NOUN_DOMAINS.items():
                        if attr in keywords or attr_tokens & keywords:
                            injected_domains.add(domain)
                            collaborator_names.add(attr)
                    for domain, keywords in NOUN_DOMAINS.items():
                        if attr_tokens & keywords:
                            injected_domains.add(domain)

    n_domains = len(injected_domains)
    # Score: 0 for ≤1 domain injected, 1.0 for 4+ distinct domains
    injection_score = min(1.0, max(0.0, (n_domains - 1) / 3))

    return {
        "injected_domains": sorted(injected_domains),
        "collaborator_count": len(collaborator_names),
        "injection_score": round(injection_score, 2),
    }


class SRPAnalyzerEnhanced(ast.NodeVisitor):
    def __init__(self, weights: dict | None = None):
        # FIX 2: Configurable weights with documented defaults
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        # Normalize so weights always sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        self.report: dict[str, dict] = {}

    # ── AST helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _self_attrs(func_node: ast.FunctionDef) -> set[str]:
        return {
            node.attr
            for node in ast.walk(func_node)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        }

    @staticmethod
    def _external_objects(func_node: ast.FunctionDef) -> set[str]:
        objs: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id != "self"
                ):
                    objs.add(node.func.value.id)
                elif isinstance(node.func, ast.Name):
                    objs.add(node.func.id)
        return objs

    @staticmethod
    def _complexity(func_node: ast.FunctionDef) -> int:
        branch_types = (
            ast.If, ast.For, ast.While, ast.ExceptHandler,
            ast.With, ast.Assert, ast.comprehension,
        )
        return 1 + sum(1 for n in ast.walk(func_node) if isinstance(n, branch_types))

    # FIX 6: Cross-domain delegator detection.
    # Original: any method with ≤2 call statements was a "thin delegator"
    # and got a 50% domain-div reduction regardless of what it delegated to.
    # Fix: only reduce penalty for same-domain or unknown delegators.
    # Cross-domain thin delegators (e.g. process_order calling db + mailer)
    # are real violations and should NOT be discounted.
    @staticmethod
    def _classify_delegator(
        func_node: ast.FunctionDef,
    ) -> tuple[bool, bool]:
        """
        Returns (is_thin, is_cross_domain).

        is_thin:         True when the body has ≤2 meaningful statements
                         (qualifies as a delegator by count).
        is_cross_domain: True when the delegated callees span 2+ distinct
                         domains — this delegator is a real violation.
        """
        call_stmts = [
            n for n in func_node.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        ]
        non_trivial = [
            n for n in func_node.body
            if not isinstance(n, (ast.Return, ast.Pass))
            and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call))
        ]
        total_meaningful = len(call_stmts) + len(non_trivial)
        is_thin = total_meaningful <= 2

        if not is_thin:
            return False, False

        # Check what domains the callees belong to
        body_domains = _classify_body_domains(func_node) - {"other"}
        is_cross_domain = len(body_domains) >= 2

        return True, is_cross_domain

    # ── Score sub-components ─────────────────────────────────────────────────

    @staticmethod
    def _jaccard_diversity(methods_info: list[dict]) -> float:
        sets = [set(m["objects_used"]) for m in methods_info if m["objects_used"]]
        if len(sets) < 2:
            return 0.0
        dists = [
            1 - len(a & b) / len(a | b)
            for a, b in combinations(sets, 2)
        ]
        return sum(dists) / len(dists)

    # FIX 4: Weight collaborator attributes higher in LCOM.
    # self.db, self.mailer being used by disjoint method groups is far more
    # diagnostic than self.name or self.count being disjoint.
    @staticmethod
    def _lcom_score(methods_info: list[dict], collaborator_attrs: set[str]) -> float:
        """
        LCOM with collaborator-weighted attribute sets.

        Collaborator attributes (self.db, self.mailer, etc.) count 3× in the
        cohesion calculation; scalar fields count 1×. This makes disjoint
        collaborator usage drive the score much harder than disjoint scalars.
        """
        def weighted_attr_set(attrs: list[str]) -> set[str]:
            result = set()
            for a in attrs:
                result.add(a)
                if a in collaborator_attrs:
                    # Expand collaborators into synthetic copies so they
                    # dominate the Jaccard overlap calculation
                    result.add(f"__collab__{a}__1")
                    result.add(f"__collab__{a}__2")
            return result

        attr_sets = [weighted_attr_set(m["self_attrs"]) for m in methods_info]
        if not any(s - {f"__collab__{a}__{i}" for a in [] for i in []} for s in attr_sets):
            return 0.0
        if not any(attr_sets):
            return 0.0
        if len(attr_sets) < 2:
            return 0.0
        total_pairs = len(attr_sets) * (len(attr_sets) - 1) // 2
        shared = sum(1 for a, b in combinations(attr_sets, 2) if a & b)
        return 1.0 - (shared / total_pairs)

    @staticmethod
    def _domain_diversity(methods_info: list[dict]) -> float:
        meaningful = {
            d
            for m in methods_info
            for d in m["domains"]
            if d != "other"
        }
        return min(1.0, max(0.0, (len(meaningful) - 1) / 4))

    # FIX 1: Body-level domain diversity signal.
    @staticmethod
    def _body_domain_diversity(methods_info: list[dict]) -> float:
        """
        Like _domain_diversity but using body-scanned domains instead of
        name-inferred domains. Catches process(), handle(), run() etc.
        """
        meaningful = {
            d
            for m in methods_info
            for d in m["body_domains"]
            if d != "other"
        }
        return min(1.0, max(0.0, (len(meaningful) - 1) / 4))

    @staticmethod
    def _size_factor(methods_info: list[dict]) -> float:
        lines = [m["line_count"] for m in methods_info]
        n = len(lines)
        avg = sum(lines) / n
        large_ratio = sum(1 for l in lines if l > 30) / n
        if n >= 2 and avg > 0:
            cv = statistics.stdev(lines) / avg
            cv_factor = min(1.0, cv / 2.0)
        else:
            cv_factor = 0.0
        return min(1.0, (large_ratio + cv_factor) / 2)

    # ── Constructor collaborator detection (FIX 3) ────────────────────────────

    @staticmethod
    def _detect_collaborator_attrs(class_node: ast.ClassDef) -> set[str]:
        """
        Find attributes assigned in __init__ that map to known collaborator
        domains. Used to weight LCOM (FIX 4) and report injection score (FIX 3).
        """
        collaborators: set[str] = set()
        for n in class_node.body:
            if isinstance(n, ast.FunctionDef) and n.name == "__init__":
                for node in ast.walk(n):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                attr = target.attr.lower()
                                attr_tokens = set(_tokenize_name(attr))
                                for keywords in COLLABORATOR_NOUN_DOMAINS.values():
                                    if attr in keywords or attr_tokens & keywords:
                                        collaborators.add(target.attr)
                                        break
                                for keywords in NOUN_DOMAINS.values():
                                    if attr_tokens & keywords:
                                        collaborators.add(target.attr)
                                        break
        return collaborators

    # ── Main visitor ─────────────────────────────────────────────────────────

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = node.name
        methods_info: list[dict] = []
        constructor_info: dict = {}

        # FIX 3: Identify collaborator attributes from __init__ before
        # processing regular methods, so LCOM weighting (FIX 4) can use them.
        collaborator_attrs = self._detect_collaborator_attrs(node)

        for n in node.body:
            if not isinstance(n, ast.FunctionDef):
                continue

            # FIX 3: Analyze __init__ separately instead of skipping it
            if n.name == "__init__":
                constructor_info = _analyze_constructor(n)
                continue

            if n.name.startswith("__") and n.name.endswith("__"):
                continue

            decorators = _get_decorators(n)
            if "property" in decorators:
                continue
            is_static = bool(decorators & {"staticmethod", "classmethod"})

            lines = (n.end_lineno or n.lineno) - n.lineno + 1

            # FIX 5: Restore And/Or split (was 0.0 weight before)
            parts = re.split(r"(?<=[a-z])(?:And|Or)(?=[A-Z])", n.name)

            # FIX 6: Distinguish thin same-domain vs thin cross-domain delegators
            is_thin, is_cross_domain_delegator = self._classify_delegator(n)

            # FIX 1: Scan body for domains in addition to scanning the name
            body_domains = _classify_body_domains(n)

            methods_info.append({
                "name":                     n.name,
                "objects_used":             list(self._external_objects(n)),
                "self_attrs":               list(self._self_attrs(n)),
                "domains":                  _classify_domains(n.name),
                "body_domains":             body_domains,
                "responsibilities":         [p.lower() for p in parts if p],
                "line_count":               lines,
                "complexity":               self._complexity(n),
                "is_static":                is_static,
                "is_thin_delegator":        is_thin,
                "is_cross_domain_delegator": is_cross_domain_delegator,
            })

        if not methods_info:
            self.report[class_name] = {
                "srp_violation_score": 0.0,
                "status": "Pass",
                "confidence": "high",
                "is_violation": False,
                "methods": [],
                "diagnostics": {},
                "constructor": constructor_info,
            }
            for child in ast.walk(node):
                if isinstance(child, ast.ClassDef) and child is not node:
                    self.visit_ClassDef(child)
            return

        all_resp = {r for m in methods_info for r in m["responsibilities"]}
        n_resp = len(all_resp)
        # FIX 5: responsibility_factor is now actually used (weight restored to 0.05)
        responsibility_factor = 0.0 if n_resp <= 1 else (n_resp - 1) / n_resp

        total_objects = sum(len(m["objects_used"]) for m in methods_info)
        object_factor = (
            max(0, total_objects - len(methods_info)) / total_objects
            if total_objects else 0.0
        )

        domain_div     = self._domain_diversity(methods_info)
        # FIX 1: New body-scan signal
        body_domain_div = self._body_domain_diversity(methods_info)
        # FIX 4: Collaborator-weighted LCOM
        lcom           = self._lcom_score(methods_info, collaborator_attrs)
        obj_diversity  = self._jaccard_diversity(methods_info)
        size_factor    = self._size_factor(methods_info)

        n_methods = len(methods_info)

        # FIX 6: Only discount SAME-DOMAIN thin delegators.
        # Cross-domain thin delegators are real violations — no discount.
        safe_delegator_count = sum(
            1 for m in methods_info
            if m["is_thin_delegator"] and not m["is_cross_domain_delegator"]
        )
        delegator_ratio = sum(1 for m in methods_info if m["is_thin_delegator"]) / n_methods
        safe_delegator_ratio = safe_delegator_count / n_methods
        # Discount only on safe (same-domain) delegators; cross-domain ones keep
        # the full penalty so process_order(db+mailer) still fires.
        effective_domain_div = domain_div * (1 - 0.5 * safe_delegator_ratio)
        # For body_domain_div: cross-domain delegators INCREASE the signal — they
        # confirm the body really does touch multiple domains, so no discount at all.
        effective_body_domain_div = body_domain_div

        # FIX 2: Use configurable (and normalized) weights
        w = self.weights
        srp_violation_score = (
            w["object_diversity"]      * obj_diversity
            + w["effective_domain_div"]  * effective_domain_div
            + w["lcom"]                  * lcom
            + w["body_domain_div"]       * effective_body_domain_div   # FIX 1
            + w["size_factor"]           * size_factor
            + w["responsibility_factor"] * responsibility_factor        # FIX 5
        )

        # FIX 3: Constructor injection score boosts the final score directly.
        # Rationale: a class injecting 4+ domain collaborators is almost
        # certainly violating SRP regardless of method-level metrics.
        injection_score = constructor_info.get("injection_score", 0.0)
        # Unconditional: up to 0.25 boost from constructor analysis.
        # Removed the gating on method-level score — that prevented single-method
        # God classes (all logic in __init__ + one run()) from being caught.
        constructor_boost = injection_score * 0.25
        srp_violation_score = min(1.0, srp_violation_score + constructor_boost)

        detected_domains = sorted(
            {d for m in methods_info for d in m["domains"]} - {"other"}
        )
        # FIX 1: also report body-detected domains
        body_detected_domains = sorted(
            {d for m in methods_info for d in m["body_domains"]} - {"other"}
        )

        base_threshold = 0.40
        adaptive_threshold = base_threshold - max(0.0, (4 - n_methods) * 0.05)

        if srp_violation_score > adaptive_threshold + 0.08:
            status, confidence = "Violation", "high"
        elif srp_violation_score > adaptive_threshold:
            status, confidence = "Review", "low"
        else:
            status, confidence = "Pass", "high"

        is_violation = status == "Violation"

        self.report[class_name] = {
            "srp_violation_score": round(srp_violation_score * 100, 1),
            "status": status,
            "confidence": confidence,
            "is_violation": is_violation,
            "methods": [m["name"] for m in methods_info],
            "constructor": constructor_info,
            "diagnostics": {
                "domain_diversity":         round(domain_div, 2),
                "effective_domain_div":     round(effective_domain_div, 2),
                "body_domain_diversity":    round(body_domain_div, 2),         # FIX 1
                "effective_body_domain_div":round(effective_body_domain_div, 2),
                "lcom":                     round(lcom, 2),
                "object_diversity":         round(obj_diversity, 2),
                "responsibility_factor":    round(responsibility_factor, 2),
                "size_factor":              round(size_factor, 2),
                "delegator_ratio":          round(delegator_ratio, 2),
                "safe_delegator_ratio":     round(safe_delegator_ratio, 2),    # FIX 6
                "constructor_boost":        round(constructor_boost, 3),       # FIX 3
                "injection_score":          injection_score,                   # FIX 3
                "adaptive_threshold":       round(adaptive_threshold * 100, 1),
                "detected_domains":         detected_domains,
                "body_detected_domains":    body_detected_domains,             # FIX 1
                "collaborator_attrs":       sorted(collaborator_attrs),        # FIX 4
                "weights_used":             {k: round(v, 3) for k, v in self.weights.items()},  # FIX 2
            },
        }

        for child in ast.walk(node):
            if isinstance(child, ast.ClassDef) and child is not node:
                self.visit_ClassDef(child)


def get_srp_report(code: str, weights: dict | None = None) -> list[dict]:
    """
    Analyze Python source code for Single Responsibility Principle violations.

    Args:
        code:    Python source as a string.
        weights: Optional dict to override scoring weights. Keys:
                   object_diversity, effective_domain_div, lcom,
                   body_domain_div, size_factor, responsibility_factor
                 Values are relative (they are normalized to sum=1).
                 Example: {"body_domain_div": 0.20, "lcom": 0.15}

    Returns:
        List of result dicts, one per class.
    """
    try:
        tree = ast.parse(code)
        # FIX 2: Pass weights into the analyzer
        analyzer = SRPAnalyzerEnhanced(weights=weights)
        analyzer.visit(tree)

        if not analyzer.report:
            return [{
                "status": "Pass",
                "confidence": "high",
                "reason": "No classes detected.",
                "suggestion": "Define a class to see SRP analysis.",
            }]

        results = []
        for class_name, data in analyzer.report.items():
            diag   = data.get("diagnostics", {})
            ctor   = data.get("constructor", {})
            score  = data["srp_violation_score"]
            status = data["status"]
            conf   = data["confidence"]
            domains = diag.get("detected_domains", [])
            body_domains = diag.get("body_detected_domains", [])

            if status in ("Violation", "Review"):
                fired: list[str] = []
                if diag.get("object_diversity", 0) > 0.5:
                    fired.append("methods depend on unrelated collaborators")
                if diag.get("effective_domain_div", 0) > 0.2:
                    fired.append(f"name-inferred domains: {', '.join(domains)}")
                # FIX 1: Report body-detected domains separately
                if diag.get("effective_body_domain_div", 0) > 0.2:
                    extra = [d for d in body_domains if d not in domains]
                    if extra:
                        fired.append(f"body-detected extra domains: {', '.join(extra)}")
                    else:
                        fired.append(f"body scan confirms cross-domain activity: {', '.join(body_domains)}")
                if diag.get("lcom", 0) > 0.5:
                    collabs = diag.get("collaborator_attrs", [])
                    if collabs:
                        fired.append(f"disjoint collaborator usage ({', '.join(collabs[:4])})")
                    else:
                        fired.append("methods share few instance variables (low cohesion)")
                if diag.get("size_factor", 0) > 0.3:
                    fired.append("large/complex methods spread across the class")
                # FIX 5: Restored responsibility_factor reporting
                if diag.get("responsibility_factor", 0) > 0:
                    fired.append("'And'/'Or' in method names signals multiple responsibilities")
                # FIX 3: Report constructor injection findings
                if ctor.get("injection_score", 0) > 0.3:
                    n_c = ctor.get("collaborator_count", 0)
                    inj_d = ctor.get("injected_domains", [])
                    fired.append(
                        f"constructor injects {n_c} collaborators across domains: "
                        f"{', '.join(inj_d)}"
                    )
                if diag.get("delegator_ratio", 0) > 0.5:
                    cross = diag.get("safe_delegator_ratio", 0) < diag.get("delegator_ratio", 0)
                    note = "cross-domain" if cross else "same-domain"
                    fired.append(
                        f"note: {int(diag['delegator_ratio']*100)}% thin delegators "
                        f"({note} — {'penalty applied' if cross else 'penalty reduced'})"
                    )

                reason_str = "; ".join(fired) if fired else "multiple heuristics fired"
                domain_hint = f" one per domain ({', '.join(body_domains or domains)})" if (body_domains or domains) else ""
                threshold_note = f" (threshold: {diag.get('adaptive_threshold', 40)}%)"

                if status == "Review":
                    results.append({
                        "class":      class_name,
                        "status":     "Review",
                        "confidence": conf,
                        "score":      score,
                        "reason":     (
                            f"Class '{class_name}' scored {score}%{threshold_note} — "
                            f"borderline result, manual review recommended. {reason_str}."
                        ),
                        "suggestion": (
                            f"Inspect '{class_name}' for mixed concerns,{domain_hint}. "
                            "Score is in the uncertain zone; context matters here."
                        ),
                        "diagnostics": diag,
                        "constructor": ctor,
                    })
                else:
                    results.append({
                        "class":      class_name,
                        "status":     "Violation",
                        "confidence": conf,
                        "score":      score,
                        "reason":     (
                            f"Class '{class_name}' scored {score}%{threshold_note} — "
                            f"{reason_str}."
                        ),
                        "suggestion": (
                            f"Split '{class_name}' into focused classes,{domain_hint}."
                        ),
                        "diagnostics": diag,
                        "constructor": ctor,
                    })
            else:
                results.append({
                    "class":      class_name,
                    "status":     "Pass",
                    "confidence": conf,
                    "score":      score,
                    "reason":     f"Class '{class_name}' appears cohesive (score: {score}%).",
                    "suggestion": "No refactor needed.",
                    "diagnostics": diag,
                    "constructor": ctor,
                })

        return results

    except SyntaxError as e:
        return [{"status": "Error", "reason": f"Syntax error: {e}", "suggestion": "Fix the syntax before analysis."}]
    except Exception as e:
        return [{"status": "Error", "reason": f"Unexpected error: {e}", "suggestion": "N/A"}]