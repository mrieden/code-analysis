import ast
import re
import pprint

class SRPAnalyzerEnhanced(ast.NodeVisitor):
    def __init__(self):
        self.report = {}

    def visit_ClassDef(self, node):
        class_name = node.name
        methods_info = []

        for n in node.body:
            if isinstance(n, ast.FunctionDef):
                method_name = n.name
                objects_used = set()

                for stmt in ast.walk(n):
                    if isinstance(stmt, ast.Call):
                        if isinstance(stmt.func, ast.Attribute) and isinstance(stmt.func.value, ast.Name):
                            objects_used.add(stmt.func.value.id)
                        elif isinstance(stmt.func, ast.Name):
                            objects_used.add(stmt.func.id)

                responsibilities = re.split('_|And|Or', method_name)
                responsibilities = [r.lower() for r in responsibilities if r]

                description = f"Method '{method_name}' has responsibilities: {', '.join(responsibilities)}"

                methods_info.append({
                    "name": method_name,
                    "objects_used": objects_used,
                    "responsibilities": responsibilities,
                    "description": description
                })

        all_responsibilities = set(r for m in methods_info for r in m["responsibilities"])
        total_objects = sum(len(m["objects_used"]) for m in methods_info)

        responsibility_factor = max(0, len(all_responsibilities) - 1) / len(all_responsibilities) if all_responsibilities else 0
        object_factor = max(0, total_objects - len(methods_info)) / total_objects if total_objects else 0

        srp_violation_score = min(1, responsibility_factor + object_factor)

        self.report[class_name] = {
            "num_methods": len(methods_info),
            "methods": [m["name"] for m in methods_info],
            "objects_used": [m["objects_used"] for m in methods_info],
            "responsibilities": all_responsibilities,
            "methods_description": [m["description"] for m in methods_info],
            "srp_violation_score": round(srp_violation_score * 100, 1)
        }

        self.generic_visit(node)


def check_srp_percentage(code):
    tree = ast.parse(code)
    analyzer = SRPAnalyzerEnhanced()
    analyzer.visit(tree)
    return analyzer.report


def read_code_from_file(filename):
    with open(filename, "r") as f:
        return f.read()


file_to_check = "Code_Detected.py"

my_code = read_code_from_file(file_to_check)

report = check_srp_percentage(my_code)

pprint.pprint(report)
