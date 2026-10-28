"""Fine-grained before/after detail for the state diff.

Each helper returns {"kind": "tokens", "before": [[text, op], ...], "after": [...]}
(op is "eq" | "del" | "add") or {"kind": "table", ...}; None means "no finer view,
show the whole values". Kept deliberately small: lists, tuples, sets, dicts, short
strings, 1-D arrays and DataFrames.
"""
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

MISSING = object()
CONTEXT = 2          # equal items kept either side of a change before collapsing
MAX_ROWS = MAX_COLS = 8
MAX_STR = 60


def _collapse(tokens):
    """Shorten long runs of unchanged items to context + "…"."""
    out, run = [], []

    def flush(at_start, at_end):
        n = len(run)
        if n <= 2 * CONTEXT + 1:
            out.extend(run)
        elif at_start and at_end:
            out.extend(run[:CONTEXT] + [("…", "eq", True)] + run[-CONTEXT:])
        elif at_start:
            out.extend([("…", "eq", True)] + run[-CONTEXT:])
        elif at_end:
            out.extend(run[:CONTEXT] + [("…", "eq", True)])
        else:
            out.extend(run[:CONTEXT] + [("…", "eq", True)] + run[-CONTEXT:])
        run.clear()

    for t in tokens:
        if t[1] == "eq":
            run.append(t)
        else:
            if run:
                flush(not out, False)
            out.append(t)
    if run:
        flush(not out, True)
    return out


def _join(items, open_, close, sep=", "):
    toks = [[open_, "eq"]]
    for k, (text, op, _) in enumerate(items):
        if k:
            toks.append([sep, "eq"])
        toks.append([text, op])
    toks.append([close, "eq"])
    return toks


def _seq(b, a, open_, close):
    rb, ra = [repr(x) for x in b], [repr(x) for x in a]
    sm = SequenceMatcher(None, rb, ra, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            left += [(x, "eq", True) for x in rb[i1:i2]]
            right += [(x, "eq", True) for x in ra[j1:j2]]
        else:
            left += [(x, "del", True) for x in rb[i1:i2]]
            right += [(x, "add", True) for x in ra[j1:j2]]
    return {"kind": "tokens", "before": _join(_collapse(left), open_, close),
            "after": _join(_collapse(right), open_, close)}


def _dict(b, a):
    left, right = [], []
    for k in list(b) + [k for k in a if k not in b]:
        if k in b and k in a:
            same = repr(b[k]) == repr(a[k])
            left.append((f"{k!r}: {b[k]!r}", "eq" if same else "del", True))
            right.append((f"{k!r}: {a[k]!r}", "eq" if same else "add", True))
        elif k in b:
            left.append((f"{k!r}: {b[k]!r}", "del", True))
        else:
            right.append((f"{k!r}: {a[k]!r}", "add", True))
    return {"kind": "tokens", "before": _join(_collapse(left), "{", "}"),
            "after": _join(_collapse(right), "{", "}")}


def _str(b, a):
    if max(len(b), len(a)) > MAX_STR:
        return None
    sm = SequenceMatcher(None, b, a, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            left.append([b[i1:i2], "eq"]); right.append([a[j1:j2], "eq"])
        else:
            if i2 > i1: left.append([b[i1:i2], "del"])
            if j2 > j1: right.append([a[j1:j2], "add"])
    return {"kind": "tokens", "before": [["'", "eq"]] + left + [["'", "eq"]],
            "after": [["'", "eq"]] + right + [["'", "eq"]]}


def _array(b, a):
    if b.shape != a.shape or b.ndim != 1:
        return None
    same = [bool(np.array_equal(x, y, equal_nan=_isfloat(x, y))) for x, y in zip(b, a)]
    left = [(repr(x.item()), "eq" if s else "del", True) for x, s in zip(b, same)]
    right = [(repr(y.item()), "eq" if s else "add", True) for y, s in zip(a, same)]
    return {"kind": "tokens", "before": _join(_collapse(left), "[", "]"),
            "after": _join(_collapse(right), "[", "]")}


def _isfloat(*xs):
    return all(np.issubdtype(np.asarray(x).dtype, np.floating) for x in xs)


def _cell(v):
    return "NaN" if isinstance(v, float) and v != v else str(v)


def _frame(b, a):
    """Row/column aware table. b may be MISSING (a brand-new frame)."""
    if b is MISSING:
        b = a.iloc[0:0]
    cols = list(b.columns) + [c for c in a.columns if c not in b.columns]
    ib, ia = list(b.index), list(a.index)
    rows = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, ib, ia, autojunk=False).get_opcodes():
        if op == "equal":
            for p, q in zip(range(i1, i2), range(j1, j2)):
                cells = []
                for c in cols:
                    inb, ina = c in b.columns, c in a.columns
                    vb = b.iloc[p][c] if inb else MISSING
                    va = a.iloc[q][c] if ina else MISSING
                    changed = (vb is MISSING) != (va is MISSING) or (
                        vb is not MISSING and _cell(vb) != _cell(va))
                    cells.append([_cell(va if ina else vb), "add" if changed else "eq"])
                rows.append({"label": str(ia[q]), "status": "eq", "cells": cells})
            continue
        for p in range(i1, i2):
            rows.append({"label": str(ib[p]), "status": "del",
                         "cells": [[_cell(b.iloc[p][c]) if c in b.columns else "", "del"]
                                   for c in cols]})
        for q in range(j1, j2):
            rows.append({"label": str(ia[q]), "status": "add",
                         "cells": [[_cell(a.iloc[q][c]) if c in a.columns else "", "add"]
                                   for c in cols]})
    more = max(len(rows) - MAX_ROWS, 0)
    return {"kind": "table", "cols": [str(c) for c in cols][:MAX_COLS],
            "cols_more": max(len(cols) - MAX_COLS, 0),
            "rows": [{**r, "cells": r["cells"][:MAX_COLS]} for r in rows[:MAX_ROWS]],
            "rows_more": more}


def detail(b, a):
    try:
        if isinstance(a, pd.DataFrame) and (b is MISSING or isinstance(b, pd.DataFrame)):
            return _frame(b, a)
        if b is MISSING:
            return None
        if isinstance(a, list) and isinstance(b, list):
            return _seq(b, a, "[", "]")
        if isinstance(a, tuple) and isinstance(b, tuple):
            return _seq(b, a, "(", ")")
        if isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset)):
            return _seq(sorted(b, key=repr), sorted(a, key=repr), "{", "}")
        if isinstance(a, dict) and isinstance(b, dict):
            return _dict(b, a)
        if isinstance(a, str) and isinstance(b, str):
            return _str(b, a)
        if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            return _array(b, a)
    except Exception:
        return None
    return None
