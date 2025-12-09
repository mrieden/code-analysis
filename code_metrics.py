import subprocess
import json
import os
import tempfile
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from radon.raw import analyze


import ast
import re

def naming_quality_metrics(code: str):
    naming_issues = []
    score = 100  # Start with perfect score

    try:
        tree = ast.parse(code)
    except Exception as e:
        return {
            "error": f"Failed to parse code: {e}",
            "naming_score": 0,
            "issues": []
        }

    snake_case = re.compile(r'^[a-z_][a-z0-9_]*$')
    constant_case = re.compile(r'^[A-Z_][A-Z0-9_]*$')
    class_case = re.compile(r'^[A-Z][a-zA-Z0-9]+$')

    # ------------------------------------------------------------
    # Helper to record issues
    # ------------------------------------------------------------
    def add_issue(name, lineno, kind, rule):
        nonlocal score
        naming_issues.append({
            "name": name,
            "line": lineno,
            "type": kind,
            "violation": rule
        })
        score -= 5  # each violation costs 5 points

    # ------------------------------------------------------------
    # Walk through AST and check names
    # ------------------------------------------------------------
    for node in ast.walk(tree):

        # -------------------- FUNCTIONS -------------------------
        if isinstance(node, ast.FunctionDef):
            if not snake_case.match(node.name):
                add_issue(node.name, node.lineno, "function", "Function names should be snake_case")

        # -------------------- CLASSES ---------------------------
        elif isinstance(node, ast.ClassDef):
            if not class_case.match(node.name):
                add_issue(node.name, node.lineno, "class", "Class names should be CamelCase")

        # -------------------- VARIABLES -------------------------
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):

                    # CONSTANTS: UPPERCASE
                    if constant_case.match(target.id):
                        continue

                    # snake_case variables
                    if not snake_case.match(target.id):
                        add_issue(target.id, node.lineno, "variable", "Variable names should be snake_case")

        # -------------------- ARGUMENTS -------------------------
        elif isinstance(node, ast.arg):
            if node.arg != "self" and not snake_case.match(node.arg):
                add_issue(node.arg, node.lineno, "argument", "Argument names should be snake_case")

    # Final score clamp
    score = max(0, min(100, score))

    return {
        "naming_score": score,
        "issues": naming_issues
    }



def analyze_code_string(code_string):
    results = {}

    results["naming_quality"] = naming_quality_metrics(code)


    # === RADON METRICS ===
    try:
        complexity_blocks = cc_visit(code_string)
        print("Complexity Blocks:")
        print(complexity_blocks)
        print("\n\n\n")

        complexity_blocks = sorted(
            complexity_blocks,
            key=lambda b: getattr(b, "lineno", 0)
        )

        formatted_complexity = []
        for block in complexity_blocks:
            formatted_complexity.append({
                "name": getattr(block, "name", None),
                "complexity": getattr(block, "complexity", None),
                "lineno": getattr(block, "lineno", None),
                "col_offset": getattr(block, "col_offset", None),
                "endline": getattr(block, "endline", None),
                "classname": getattr(block, "classname", None),
                "type": getattr(block, "type", None),
                "number_of_methods": len(getattr(block,"methods",None)) if getattr(block,"methods",None) else 0,
            })

        
        halstead_result = h_visit(code_string)
        print("Halstead Result:")
        print(halstead_result)
        print("\n\n\n")
        total_halstead_metrics = []

        total_halstead_metrics = {
            "h1": halstead_result.total.h1,
            "h2": halstead_result.total.h2,
            "N1": halstead_result.total.N1,
            "N2": halstead_result.total.N2,
            "vocabulary": halstead_result.total.vocabulary,
            "length": halstead_result.total.length,
            "calculated_length": halstead_result.total.calculated_length,
            "volume": halstead_result.total.volume,
            "difficulty": halstead_result.total.difficulty,
            "effort": halstead_result.total.effort,
            "time": halstead_result.total.time,
            "bugs": halstead_result.total.bugs,
        }

        halstead_metrics = []
        for func in halstead_result.functions:
            halstead_metrics.append({
                "name": func[0],
                "h1": func[1].h1,
                "h2": func[1].h2,
                "N1": func[1].N1,
                "N2": func[1].N2,
                "vocabulary": func[1].vocabulary,
                "length": func[1].length,
                "calculated_length": func[1].calculated_length,
                "volume": func[1].volume,
                "difficulty": func[1].difficulty,
                "effort": func[1].effort,
                "time": func[1].time,
                "bugs": func[1].bugs,
            })




        raw = analyze(code_string)
        print("Raw Metrics:")
        print(raw)
        raw_metrics = {
            "total_lines_of_code": raw.loc,
            "logical_lines_of_code": raw.lloc,
            "source_lines_of_code": raw.sloc,
            "comments": raw.comments,
            "multi_line_string": raw.multi,
            "blank": raw.blank,
            "single_comments": raw.single_comments,
        }

        results["radon"] = {
            "complexity": formatted_complexity,
            "maintainability_index": mi_visit(code_string, True),
            "total_haIstead_metrics": total_halstead_metrics,
            "halstead_metrics":halstead_metrics,
            "raw_metrics": raw_metrics,
        }

    except Exception as e:
        results["radon"] = {"error": f"Radon failed: {e}"}

    # === PYLINT METRICS ===
    try:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
        temp.write(code_string)
        temp.close()

        pylint_result = subprocess.run(
            ["pylint", temp.name, "-f", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        pylint_json = pylint_result.stdout.strip()
        results["pylint"] = json.loads(pylint_json if pylint_json else "[]")

        os.remove(temp.name)

    except Exception as e:
        results["pylint"] = {"error": f"Pylint failed: {e}"}

    return results


if __name__ == "__main__":
    code = """
class Animal:
    def speak(self) -> str:
        return "generic sound"

class Dog(Animal):
    def speak(self) -> str:
        return "woof"
"""

    metrics = analyze_code_string(code)

    print("\n\n===== 📊 FINAL METRICS =====")
    print(json.dumps(metrics, indent=4))
