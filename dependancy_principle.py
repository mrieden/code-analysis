import ast
import os

class DipAnalyzer(ast.NodeVisitor):

    def __init__(self, filename):
        self.filename = filename
        self.current_class = None
        self.violations = []

    def visit_ClassDef(self, node):
        # بيلقط أي Class في المشروع
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        # بيسمع لأي Constructor
        if node.name == "__init__" and self.current_class is not None:

            # بيمشي على كل باراميتر ويتأكد إنه مش Concrete Class
            for arg in node.args.args[1:]:  # skip self
                if arg.annotation:
                    typename = self._extract_type_name(arg.annotation)

                    # لو النوع Concrete يدينا Violation
                    if self._is_concrete(typename):
                        self.violations.append(
                            (
                                self.filename,
                                arg.lineno,
                                arg.col_offset,
                                f"DIP001 Class '{self.current_class}' depends on concrete class '{typename}'. Use an abstraction instead."
                            )
                        )

        self.generic_visit(node)

    # بنطلع اسم النوع من الـ annotation
    def _extract_type_name(self, annotation):
        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Attribute):
            return annotation.attr
        return None

    # تحديد إذا كان النوع Concrete (مش Interface ولا Abstract)
    def _is_concrete(self, typename):
        if typename is None:
            return False
        if typename.startswith("I"):
            return False
        if typename.endswith("Base") or typename.endswith("ABC"):
            return False
        return True

# analyzer لملف واحد 
def analyze_file(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    analyzer = DipAnalyzer(path)
    analyzer.visit(tree)
    return analyzer.violations

# analyzer لمجلد كامل 
def analyze_directory(folder):
    results = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".py"):
                results.extend(analyze_file(os.path.join(root, file)))
    return results


if __name__ == "__main__":
    import sys
    target = sys.argv[1]
   # //لو Path  حلّل كل الملفات
    # //لو File واحد حلله ع طول  
    violations = (
        analyze_directory(target)
        if os.path.isdir(target)
        else analyze_file(target)
    )

    for file, line, col, msg in violations:
        print(f"{file}:{line}:{col}: {msg}")
# توضيح في بايثون مفيش roslyn فهنستخدم ast analyzer

# test run: python dependancy_principle.py dependecy_test.py
