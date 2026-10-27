"""Grade a single learner line via AST inspection + live namespace diffing.

NOTE: executes learner code with exec/eval in-process. Local use only.
"""
import ast
import builtins
import contextlib
import copy
import io

import numpy as np
import pandas as pd

from drills import Drill

_INJECTED = {"pd": pd, "np": np}
_PREVIEW = 80


def preview(v):
    r = repr(v).replace("\n", " ")
    return r if len(r) <= _PREVIEW else r[:_PREVIEW - 1] + "…"


def describe(env):
    return [{"name": k, "type": type(v).__name__, "preview": preview(v)}
            for k, v in env.items()]


def detect_effect(node):
    """Syntactic effect of a single statement: rebind | mutate | emit | ambiguous."""
    if isinstance(node, ast.AugAssign):
        return "rebind"
    if isinstance(node, ast.Assign):
        if all(isinstance(t, ast.Subscript) for t in node.targets):
            return "mutate"
        return "rebind"
    if isinstance(node, ast.Expr):
        v = node.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "print":
            return "emit"
        if isinstance(v, ast.Call):
            return "ambiguous"  # method call: mutate (None) or emit (value)
        return "emit"
    return "other"


def _diff(before, after, ids):
    rows = []
    for k in sorted(set(before) | set(after)):
        if k not in before:
            rows.append({"name": k, "change": "added", "after": preview(after[k])})
        elif k not in after:
            rows.append({"name": k, "change": "removed", "before": preview(before[k])})
        else:
            b, a = preview(before[k]), preview(after[k])
            rebound = id(after[k]) != ids[k]
            if b != a or rebound:
                rows.append({"name": k, "change": "rebound" if rebound else "mutated",
                             "before": b, "after": a})
    return rows


def run_line(drill: Drill, code: str) -> dict:
    res = {"passed": False, "error": None, "hints": [], "stdout": "",
           "ret": None, "diff": [], "effect_used": None}
    try:
        tree = ast.parse(code.strip())
    except SyntaxError as e:
        res["error"] = f"SyntaxError: {e.msg}"
        return res
    if len(tree.body) != 1:
        res["error"] = "Write exactly one statement."
        return res
    node = tree.body[0]
    res["effect_used"] = detect_effect(node)

    env = drill.setup()
    ids = {k: id(v) for k, v in env.items()}
    before = copy.deepcopy(env)
    ns = {"__builtins__": builtins, **_INJECTED, **env}

    out, ret = io.StringIO(), None
    try:
        with contextlib.redirect_stdout(out):
            if isinstance(node, ast.Expr):
                ret = eval(compile(ast.Expression(node.value), "<drill>", "eval"), ns)
            else:
                exec(compile(tree, "<drill>", "exec"), ns)
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
        return res

    after = {k: v for k, v in ns.items() if k not in _INJECTED and k != "__builtins__"}
    res["stdout"] = out.getvalue()
    res["ret"] = None if ret is None else preview(ret)
    res["diff"] = _diff(before, after, ids)

    ok = True
    if drill.effect == "mutate" and drill.target:
        t = drill.target
        if t not in after or id(after[t]) != ids[t]:
            ok = False
            res["hints"].append(
                f"`{t}` was rebound. In-place methods return None, so assigning "
                f"their result overwrites `{t}`. Drop the assignment.")
    if drill.effect == "emit" and res["effect_used"] == "rebind":
        ok = False
        res["hints"].append("This is an Emit drill: show the value, don't bind it.")
    if drill.effect == "rebind" and res["effect_used"] != "rebind":
        ok = False
        res["hints"].append("This is a Rebind drill: the result must land in a name.")
    try:
        ok = bool(drill.verify(before, after, res["stdout"], ret)) and ok
    except Exception as e:
        ok = False
        res["hints"].append(f"State check failed: {type(e).__name__}")
    res["passed"] = ok
    if not ok and not res["hints"]:
        res["hints"].append("Ran, but the resulting state isn't what the intent asks for.")
    return res


def _norm(s):
    return "".join(s.lower().replace('"', "'").split()).strip(".") if s else "none"


def check_slots(drill: Drill, slots: dict) -> dict:
    out = {}
    for slot, accepted in drill.grammar.items():
        given = _norm(slots.get(slot, ""))
        out[slot] = given in {_norm(a).strip(".") for a in accepted} or (
            slot == "landing" and given in {"", "none", "dropped"}
            and "none" in {_norm(a) for a in accepted})
    return out
