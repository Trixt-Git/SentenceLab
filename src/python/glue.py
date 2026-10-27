"""Glue between the Web Worker and python/checker.py. JSON in, JSON out, so no Python object reaches JS.

checker.py is shipped unchanged; everything the app needs beyond it lives here:
  blank(line, part)            -> the line with one top-level part replaced by ____ (for L4)
  ref_effects(setup, reference) -> the names and effects of the reference, in words the UI can use
"""
import ast, json, sys

sys.path.insert(0, "/home/pyodide")
import checker

PARTS = ("subject", "verb", "details", "landing")


def _op_span(b, left_end, right_start, sym):
    """Byte span of the operator `sym` in the text between two operands (brackets and spaces may surround it)."""
    mid = b[left_end:right_start].decode()
    i = mid.find(sym)
    if i < 0:
        return None
    a = left_end + len(mid[:i].encode())
    return a, a + len(sym.encode())


def _spans(line):
    """{part: (start, end)} byte spans of the top-level parts that can be blanked in a one-line statement."""
    if "\n" in line:
        return {}
    node = ast.parse(line).body[0]
    b = line.encode()
    sp = {}
    if isinstance(node, ast.Assign):
        last = node.targets[-1]
        eq = b.find(b"=", last.end_col_offset)
        a, z = node.targets[0].col_offset, eq + 1
        while z < len(b) and b[z:z + 1] == b" ":
            z += 1
        sp["landing"] = (a, z)
        expr = node.value
    elif isinstance(node, ast.AugAssign):
        t, v = node.target, node.value
        sp["subject"] = (t.col_offset, t.end_col_offset)
        sym = checker.OPS.get(type(node.op).__name__, "?") + "="
        verb = _op_span(b, t.end_col_offset, v.col_offset, sym)
        if verb:
            sp["verb"] = verb
        sp["details"] = (v.col_offset, v.end_col_offset)
        return sp
    elif isinstance(node, ast.Expr):
        expr = node.value
    else:
        return sp

    if isinstance(expr, ast.Call):
        f = expr.func
        if isinstance(f, ast.Attribute):
            sp["subject"] = (f.value.col_offset, f.value.end_col_offset)
            dot = b.find(b".", f.value.end_col_offset)
            sp["verb"] = (dot, f.end_col_offset)
        else:
            sp["verb"] = (f.col_offset, f.end_col_offset)
        args = list(expr.args) + list(expr.keywords)
        if args:
            sp["details"] = (min(a.col_offset for a in args), max(a.end_col_offset for a in args))
    elif isinstance(expr, ast.Subscript):
        sp["subject"] = (expr.value.col_offset, expr.value.end_col_offset)
        sp["details"] = (expr.slice.col_offset, expr.slice.end_col_offset)
    elif isinstance(expr, (ast.BinOp, ast.Compare)):
        left = expr.left
        right = expr.right if isinstance(expr, ast.BinOp) else expr.comparators[0]
        op = expr.op if isinstance(expr, ast.BinOp) else expr.ops[0]
        sp["subject"] = (left.col_offset, left.end_col_offset)
        sp["details"] = (right.col_offset, right.end_col_offset)
        verb = _op_span(b, left.end_col_offset, right.col_offset, checker.OPS.get(type(op).__name__, "?"))
        if verb:
            sp["verb"] = verb
    return sp


def blank(line, part):
    """Replace one top-level part with ____. Returns None when the line has no such part (a bare call has no
    landing, `len(x)` has no subject, a lookup's verb is just brackets), so the caller moves on to the next part."""
    try:
        span = _spans(line).get(part)
    except SyntaxError:
        return None
    if not span:
        return None
    b = line.encode()
    a, z = span
    blanked = (b[:a] + b"____" + (b" " if part == "landing" else b"") + b[z:]).decode()
    return {"blanked": blanked, "part": part, "answer": b[a:z].decode().strip()}


def ref_effects(setup, reference):
    r = checker.run(setup, reference)
    if r["setup_error"] or r["error"]:
        return {"effects": [], "rebound": [], "mutated": [], "error": (r["setup_error"] or r["error"])["message"]}
    return {"effects": checker.effects(r), "rebound": r["rebound"], "mutated": r["mutated"],
            "deleted": r["deleted"], "error": None}


def call(name, payload):
    a = json.loads(payload)
    if name == "check":
        r = checker.check_all(a["setups"], a["reference"], a["answer"], a.get("options"))
    elif name == "validate":
        r = checker.validate(a["setups"], a["reference"], a.get("traps", []), a.get("options"))
    elif name == "parts":
        r = checker.parts(a["line"])
    elif name == "bench":
        r = checker.bench(a["setup"], a.get("line", ""))
    elif name == "blank":
        r = blank(a["line"], a["part"])
    elif name == "effects":
        r = ref_effects(a["setup"], a["reference"])
    else:
        raise ValueError("unknown request: " + name)
    return json.dumps(r, allow_nan=False)
