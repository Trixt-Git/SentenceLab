"""Grade a single learner line via AST inspection + live namespace diffing.

NOTE: executes learner code with exec/eval in-process. Local use only.
"""
import ast
import re
import builtins
import contextlib
import copy
import io

import numpy as np
import pandas as pd

from diffdetail import MISSING, detail
from drills import Drill

_INJECTED = {"pd": pd, "np": np}
_PREVIEW = 80
NOTES = {"rebound": "{name} now holds a different object",
         "mutated": "{name} still holds the same object; what is inside changed",
         "added": "{name} is a new name"}


def _is_estimator(v):
    return hasattr(v, "get_params") and hasattr(v, "fit")


def _fitted(v):
    return any(k.endswith("_") and not k.startswith("__") for k in vars(v))


def preview(v):
    if _is_estimator(v):
        if not _fitted(v):
            return f"{type(v).__name__} (not fitted)"
        for attr in ("mean_", "coef_"):         # a learned value, so refits are visible
            if hasattr(v, attr):
                first = float(np.asarray(getattr(v, attr)).ravel()[0])
                return f"{type(v).__name__} (fitted, {attr}[0]={first:.4g})"
        return f"{type(v).__name__} (fitted)"
    r = repr(v).replace("\n", " ")
    return r if len(r) <= _PREVIEW else r[:_PREVIEW - 1] + "…"


def _state_preview(v):
    if isinstance(v, pd.DataFrame):
        return f"({v.shape[0]}×{v.shape[1]})\n" + v.head(6).to_string()
    if isinstance(v, np.ndarray):
        return f"{v.shape} {v.dtype}"
    if _is_estimator(v):
        return "(fitted)" if _fitted(v) else "(not fitted)"
    return preview(v)


def describe(env):
    return [{"name": k, "type": type(v).__name__, "preview": _state_preview(v)}
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
            rows.append({"name": k, "change": "added", "after": preview(after[k]),
                         "note": NOTES["added"].format(name=k),
                         "detail": detail(MISSING, after[k])})
        elif k not in after:
            rows.append({"name": k, "change": "removed", "before": preview(before[k])})
        else:
            b, a = preview(before[k]), preview(after[k])
            rebound = id(after[k]) != ids[k]
            if b != a or rebound:
                rows.append({"name": k, "change": "rebound" if rebound else "mutated",
                             "before": b, "after": a,
                             "note": NOTES["rebound" if rebound else "mutated"].format(name=k),
                             "detail": detail(before[k], after[k])})
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
    res["ret"] = None if ret is None else (
        ret.head(6).to_string() if isinstance(ret, pd.DataFrame) else preview(ret))
    res["diff"] = _diff(before, after, ids)

    ok = True
    if drill.effect == "mutate" and drill.target:
        t = drill.target
        if t not in after or id(after[t]) != ids[t]:
            ok = False
            res["hints"].append(
                f"`{t}` now holds None, not your data. This verb changes the data itself and "
                f"produces no result (None), and `{t} =` stored that nothing over your data. "
                f"Drop the `{t} =`.")
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


_IDENT = re.compile(r"[A-Za-z_]\w*")


def check_blanks(blanks, answers):
    """answers: one accepted-list per blank; "<name>" accepts any identifier."""
    out = []
    for given, accepted in zip(blanks, answers):
        g = given.strip()
        out.append(("<name>" in accepted and bool(_IDENT.fullmatch(g)))
                   or _norm(g) in {_norm(a) for a in accepted})
    return out


def probe_runs(setup, *lines):
    """Run lines against fresh copies of setup(); return diff/stdout/ret/error each."""
    probe = Drill(id="probe", domain="", intent="", setup=setup, effect="any",
                  grammar={}, reference_line="", verify=lambda *a: True)
    out = []
    for ln in lines:
        r = run_line(probe, ln)
        out.append({"line": ln, **{k: r[k] for k in ("diff", "stdout", "ret", "error")}})
    return out
