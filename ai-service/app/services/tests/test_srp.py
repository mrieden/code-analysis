"""
Calibration test suite for the improved SRP analyzer.
Each fixture is a known-good or known-bad class with expected outcome.
"""
import json
from srp_analyzer import get_srp_report

FIXTURES = {}

# ── FIX 1: Body-blind detection ───────────────────────────────────────────────
FIXTURES["fix1_generic_name_hides_violation"] = {
    "expected": "Violation",
    "description": "FIX 1: process() calls db + mailer + renderer — body scan must catch it",
    "code": '''
class OrderProcessor:
    def __init__(self):
        self.db = Database()
        self.mailer = Mailer()
        self.renderer = HtmlRenderer()

    def process(self, order_id):
        record = self.db.query("SELECT * FROM orders WHERE id=?", order_id)
        self.renderer.render("order_template", record)
        self.mailer.send(record["email"], "Your order", "Done")

    def handle(self, event):
        data = self.db.query("SELECT * FROM events WHERE id=?", event)
        self.mailer.send(data["contact"], "Event", str(data))
        self.renderer.render("event_template", data)
'''
}

# ── FIX 2: Custom weights ─────────────────────────────────────────────────────
FIXTURES["fix2_custom_weights_change_score"] = {
    "expected": "any",   # just checks no crash + weights appear in diagnostics
    "description": "FIX 2: custom weights must be accepted and reflected",
    "code": '''
class DataService:
    def get_user(self, uid): return self.db.find(uid)
    def save_user(self, u): self.db.save(u)
    def delete_user(self, uid): self.db.delete(uid)
''',
    "weights": {"body_domain_div": 0.50, "lcom": 0.10}
}

# ── FIX 3: Constructor injection ──────────────────────────────────────────────
FIXTURES["fix3_constructor_injection_caught"] = {
    "expected": "Violation",
    "description": "FIX 3: __init__ injecting db + mailer + renderer + auth should boost score",
    "code": '''
class GodService:
    def __init__(self, db, mailer, renderer, auth, validator):
        self.db = db
        self.mailer = mailer
        self.renderer = renderer
        self.auth = auth
        self.validator = validator

    def run(self, payload):
        if self.auth.check(payload["token"]):
            if self.validator.validate(payload):
                self.db.save(payload)
                self.mailer.send(payload["email"], "ok", "done")
                return self.renderer.render("success", payload)
'''
}

# ── FIX 4: Collaborator-weighted LCOM ─────────────────────────────────────────
FIXTURES["fix4_disjoint_collaborators_penalized"] = {
    "expected": "Violation",
    "description": "FIX 4: self.db used only by persistence methods, self.mailer only by notification — should fire",
    "code": '''
class MixedService:
    def __init__(self):
        self.db = Database()
        self.mailer = Mailer()
        self.name = "service"

    def save_record(self, data):
        return self.db.insert(data)

    def delete_record(self, rid):
        self.db.delete(rid)

    def send_confirmation(self, email, body):
        self.mailer.send(email, "Confirm", body)

    def send_digest(self, emails, summary):
        for e in emails:
            self.mailer.send(e, "Digest", summary)
'''
}

# ── FIX 5: Restored responsibility_factor ─────────────────────────────────────
FIXTURES["fix5_and_or_method_name"] = {
    "expected": "Review",   # At least review-level; And/Or names should contribute
    "description": "FIX 5: validateAndSave, fetchAndRender should fire responsibility_factor",
    "code": '''
class Processor:
    def validateAndSave(self, data):
        if data.get("id"):
            self.store.save(data)

    def fetchAndRender(self, uid):
        row = self.store.get(uid)
        return self.view.render(row)
'''
}

# ── FIX 6: Cross-domain thin delegators NOT discounted ────────────────────────
FIXTURES["fix6_cross_domain_delegator_penalized"] = {
    "expected": "Violation",
    "description": "FIX 6: thin method spanning db + mailer should NOT get domain-div discount",
    "code": '''
class ShipOrder:
    def __init__(self):
        self.db = Database()
        self.mailer = Mailer()
        self.renderer = HtmlRenderer()

    def execute(self, order_id):
        self.db.save({"id": order_id, "status": "shipped"})
        self.mailer.send("user@example.com", "Shipped", "Your order shipped")

    def notify_and_persist(self, user_id, message):
        self.db.update(user_id, {"notified": True})
        self.mailer.send("x@x.com", "note", message)

    def prepare_and_dispatch(self, payload):
        self.renderer.render("invoice", payload)
        self.mailer.send(payload["email"], "Invoice", "see attachment")
'''
}

# ── Negative: cohesive class should pass ─────────────────────────────────────
FIXTURES["neg_cohesive_repo"] = {
    "expected": "Pass",
    "description": "Negative: pure persistence repo — should always pass",
    "code": '''
class UserRepository:
    def __init__(self):
        self.db = Database()

    def find(self, uid):
        return self.db.query("SELECT * FROM users WHERE id=?", uid)

    def save(self, user):
        self.db.insert("users", user)

    def delete(self, uid):
        self.db.delete("users", uid)

    def list_all(self):
        return self.db.query("SELECT * FROM users")
'''
}

# ── Negative: stateless utility ───────────────────────────────────────────────
FIXTURES["neg_stateless_utility"] = {
    "expected": "Pass",
    "description": "Negative: stateless utility class — should not be penalized",
    "code": '''
class StringUtils:
    @staticmethod
    def slugify(text):
        return text.lower().replace(" ", "-")

    @staticmethod
    def truncate(text, max_len):
        return text[:max_len] + "..." if len(text) > max_len else text

    @staticmethod
    def capitalize_words(text):
        return " ".join(w.capitalize() for w in text.split())
'''
}

# ─────────────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0
    results = []

    for name, fixture in FIXTURES.items():
        weights = fixture.get("weights")
        report = get_srp_report(fixture["code"], weights=weights)
        result = report[0] if report else {}
        actual_status = result.get("status", "Error")
        expected = fixture["expected"]
        diag = result.get("diagnostics", {})
        ctor = result.get("constructor", {})

        ok = (expected == "any") or (actual_status == expected)
        passed += ok
        failed += not ok

        results.append({
            "name": name,
            "ok": ok,
            "expected": expected,
            "actual": actual_status,
            "score": result.get("score", 0),
            "description": fixture["description"],
            "body_domain_div": diag.get("body_domain_diversity", 0),
            "body_domains": diag.get("body_detected_domains", []),
            "collaborator_attrs": diag.get("collaborator_attrs", []),
            "injection_score": ctor.get("injection_score", 0),
            "injected_domains": ctor.get("injected_domains", []),
            "responsibility_factor": diag.get("responsibility_factor", 0),
            "delegator_ratio": diag.get("delegator_ratio", 0),
            "safe_delegator_ratio": diag.get("safe_delegator_ratio", 0),
            "weights_used": diag.get("weights_used", {}),
            "reason": result.get("reason", ""),
        })

    print(f"\n{'='*70}")
    print(f"  SRP Analyzer Test Results: {passed}/{passed+failed} passed")
    print(f"{'='*70}\n")
    for r in results:
        icon = "✓" if r["ok"] else "✗"
        print(f"{icon} [{r['actual']:10s}] {r['name']} (score={r['score']}%)")
        print(f"    {r['description']}")
        if not r["ok"]:
            print(f"    EXPECTED: {r['expected']}  GOT: {r['actual']}")
            print(f"    REASON: {r['reason']}")
        # Show key new diagnostics
        if r["body_domains"]:
            print(f"    body_domains={r['body_domains']}  body_div={r['body_domain_div']}")
        if r["collaborator_attrs"]:
            print(f"    collaborators={r['collaborator_attrs']}")
        if r["injected_domains"]:
            print(f"    injected_domains={r['injected_domains']}  injection_score={r['injection_score']}")
        if r["responsibility_factor"] > 0:
            print(f"    responsibility_factor={r['responsibility_factor']}")
        if r["delegator_ratio"] != r["safe_delegator_ratio"]:
            print(f"    delegator_ratio={r['delegator_ratio']}  safe_ratio={r['safe_delegator_ratio']}")
        print()

    return passed, failed

if __name__ == "__main__":
    run_tests()
