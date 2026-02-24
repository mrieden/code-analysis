import sys
import os
import ast
import json
import tempfile
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Ensure the current directory is in the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- SRP IMPORT ---
try:
    from SOLID.SRP_Detection_Final import get_srp_report
except ImportError:
    def get_srp_report(code): return {"status": "Pass", "reason": "SRP Module not found", "suggestion": "Check SOLID folder"}

# --- CLEAN CODE IMPORT ---
try:
    from Clean_code.clean_code import analyze_code_string as get_clean_report
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback to empty structure so the frontend doesn't hang
    def get_clean_report(code): 
        return {
            "naming_quality": {"naming_score": 100, "issues": []},
            "radon": {"maintainability_index": 100, "raw_metrics": {}},
            "pylint": []
        }

# --- OCP DETECTOR ---
class OCPDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
    def visit_If(self, node):
        if isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name):
            if node.test.left.id.lower() in ["type", "kind", "action"]:
                self.violations.append({"line": node.lineno, "detail": "Type-based branching."})
        self.generic_visit(node)

def get_ocp_report(code_str: str):
    try:
        tree = ast.parse(code_str)
        detector = OCPDetector()
        detector.visit(tree)
        if not detector.violations:
            return {"status": "Pass", "reason": "No manual type-checking.", "suggestion": "N/A"}
        v = detector.violations[0]
        return {"status": "Violation", "reason": f"Line {v['line']}: {v['detail']}", "suggestion": "Use Polymorphism."}
    except: return {"status": "Pass", "reason": "Analyzer active.", "suggestion": "N/A"}

# --- LSP DETECTOR ---
class LSPDetector(ast.NodeVisitor):
    def __init__(self):
        self.classes = {}
        self.inheritance = {}
        self.current_class = None
        self.violations = []
    def visit_ClassDef(self, node):
        self.classes[node.name] = node
        self.inheritance[node.name] = [b.id for b in node.bases if isinstance(b, ast.Name)]
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None
    def visit_FunctionDef(self, node):
        if self.current_class is None: return
        parents = self.inheritance.get(self.current_class, [])
        for parent in parents:
            if parent in self.classes:
                parent_methods = {p.name: p for p in self.classes[parent].body if isinstance(p, ast.FunctionDef)}
                if node.name in parent_methods:
                    self.compare_methods(node, parent_methods[node.name], parent)
        self.generic_visit(node)
    def compare_methods(self, child, parent, parent_name):
        c_args, p_args = len(child.args.args)-1, len(parent.args.args)-1
        if c_args != p_args:
            self.violations.append(f"Line {child.lineno}: Argument mismatch ({c_args} vs {p_args}) in '{child.name}'.")

def get_lsp_report(code_str: str):
    try:
        tree = ast.parse(code_str)
        det = LSPDetector()
        det.visit(tree)
        if not det.violations: return {"status": "Pass", "reason": "Contracts maintained.", "suggestion": "N/A"}
        return {"status": "Violation", "reason": det.violations[0], "suggestion": "Match parent signatures."}
    except: return {"status": "Pass", "reason": "Ready.", "suggestion": "N/A"}

# --- ISP DETECTOR ---
class ISPDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
    def visit_ClassDef(self, node):
        for f in node.body:
            if isinstance(f, ast.FunctionDef):
                if len(f.body) == 1 and isinstance(f.body[0], (ast.Pass, ast.Raise)):
                    self.violations.append({"class": node.name, "reason": f"Method {f.name} looks forced (empty/pass)."})
        self.generic_visit(node)

def get_isp_report(code_str: str):
    try:
        tree = ast.parse(code_str)
        det = ISPDetector()
        det.visit(tree)
        if not det.violations: return {"status": "Pass", "reason": "Lean interfaces.", "suggestion": "N/A"}
        v = det.violations[0]
        return {"status": "Violation", "reason": f"{v['class']}: {v['reason']}", "suggestion": "Split the interface."}
    except: return {"status": "Pass", "reason": "Ready.", "suggestion": "N/A"}

# --- DIP DETECTOR ---
class DipAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.current_class = None
        self.violations = []
    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None
    def visit_FunctionDef(self, node):
        if node.name == "__init__" and self.current_class is not None:
            for arg in node.args.args[1:]:
                if arg.annotation:
                    typename = self._extract_type_name(arg.annotation)
                    if self._is_concrete(typename):
                        self.violations.append(f"Line {arg.lineno}: '{self.current_class}' depends on concrete class '{typename}'.")
        self.generic_visit(node)
    def _extract_type_name(self, annotation):
        if isinstance(annotation, ast.Name): return annotation.id
        if isinstance(annotation, ast.Attribute): return annotation.attr
        return None
    def _is_concrete(self, typename):
        if not typename: return False
        return not (typename.startswith("I") or typename.endswith("Base") or typename.endswith("ABC"))

def get_dip_report(code_str: str):
    try:
        tree = ast.parse(code_str)
        analyzer = DipAnalyzer()
        analyzer.visit(tree)
        if not analyzer.violations:
            return {"status": "Pass", "reason": "Abstractions used.", "suggestion": "N/A"}
        return {"status": "Violation", "reason": analyzer.violations[0], "suggestion": "Inject an Interface instead."}
    except: return {"status": "Pass", "reason": "Ready.", "suggestion": "N/A"}

# --- COMPLEXITY ANALYZER ---
class UniversalComplexityAnalyzer(ast.NodeVisitor):
    def __init__(self, lines):
        self.max_depth = 0
        self.current_depth = 0
        self.space_depth = 0

    def visit_For(self, node):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        
        # Check if there is an assignment or append inside this loop
        # to justify a Space Complexity increase
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Attribute) and sub_node.attr in ['append', 'add', 'extend']:
                self.space_depth = max(self.space_depth, self.current_depth)
            if isinstance(sub_node, ast.ListComp) or isinstance(sub_node, ast.DictComp):
                self.space_depth = max(self.space_depth, self.current_depth)

        self.generic_visit(node)
        self.current_depth -= 1

    def analyze(self):
        time_res = f"O(N^{self.max_depth})" if self.max_depth > 0 else "O(1)"
        # Now Space is dynamic based on nesting depth of data operations
        space_res = f"O(N^{self.space_depth})" if self.space_depth > 0 else "O(1)"
        return {"time_complexity": time_res, "space_complexity": space_res}
# --- CORE LOGIC ---
app = FastAPI()

def analyze_code_payload(code_str: str):
    try:
        # 1. Basic validation
        if not code_str.strip():
            return {
                "time_complexity": "O(1)", 
                "space_complexity": "O(1)",
                "solid_report": {}, 
                "clean_report": {},
                "total_violations": 0
            }
            
        print("--- DEBUG: Starting Analysis ---")
        
        # 2. Complexity Analysis
        tree = ast.parse(code_str)
        complexity_analyzer = UniversalComplexityAnalyzer(code_str.split('\n'))
        complexity_analyzer.visit(tree)
        results = complexity_analyzer.analyze()
        print("DEBUG: Complexity Done")
        
        # 3. SOLID Section
        s_data = get_srp_report(code_str)
        o_data = get_ocp_report(code_str)
        l_data = get_lsp_report(code_str)
        i_data = get_isp_report(code_str)
        d_data = get_dip_report(code_str)
        
        results["solid_report"] = {
            "S": s_data, "O": o_data, "L": l_data, "I": i_data, "D": d_data
        }
        print("DEBUG: SOLID Done")
        
        # 4. Clean Code Section
        # We wrap this specifically so a crash here doesn't kill the whole response
        try:
            print("DEBUG: Calling Clean Code Engine...")
            results["clean_report"] = get_clean_report(code_str)
            print("DEBUG: Clean Code Done")
        except Exception as clean_err:
            print(f"DEBUG: Clean Code Sub-module Error: {clean_err}")
            results["clean_report"] = {"error": "Module failed", "naming_quality": {"naming_score": 0, "issues": []}}
        
        # 5. Stats
        results["total_violations"] = sum(1 for v in [s_data, o_data, l_data, i_data, d_data] if v.get("status") == "Violation")
        
        print("--- DEBUG: Analysis Complete. Sending to Frontend ---")
        return results

    except Exception as e:
        # If we hit this, the JSON sent to the frontend will NOT have "clean_report", 
        # causing your React "results.clean_report" to be undefined and crash.
        print(f"CRITICAL Analysis Error: {e}")
        return {
            "error": str(e),
            "solid_report": {},
            "clean_report": {}, # Keep keys present to prevent frontend crashes
            "total_violations": 0
        }

@app.websocket("/ws/analyze")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket Connected!") # Check if this prints
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            code = payload.get("code", "")
            
            # This line is the engine
            report = analyze_code_payload(code)
            
            # Send it back
            await websocket.send_json(report)
            print("Response sent to Frontend!") # Check if this prints
    except WebSocketDisconnect:
        print("WebSocket Disconnected")