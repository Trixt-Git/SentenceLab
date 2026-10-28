"""Fine-grained before/after detail for the state diff.

detail(before, after) returns one of
  {"kind": "tokens", "before": [[text, op(, title)], ...], "after": [...], "caption"?}
  {"kind": "table", "cols", "rows", "caption"?, ...}
or None, meaning "no finer view, show the whole values". op is "eq" | "del" | "add";
title is the full-precision value when the shown text was rounded.
Covers lists, tuples, sets, dicts, strings, arrays (1-D and 2-D), Series, DataFrames.
"""
import re
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

MISSING = object()
CONTEXT = 2          # unchanged items kept either side of a change before collapsing
STR_CONTEXT = 6      # same, for word tokens in strings
MAX_ROWS = MAX_COLS = 8
MAX_STR = 5000
_TOKEN = re.compile(r"\w+|\s+|[^\w\s]")


# ------------------------------------------------------------------ formatting
def _isnan(x):
    return isinstance(x, (float, np.floating)) and x != x


def _num(x):
    """Short float text: repr when it is already short, else 4 significant figures."""
    if _isnan(x):
        return "NaN"
    r = repr(float(x))
    return r if len(r) <= 8 else format(float(x), ".4g")


def _show(x):
    """Text for a value inside a list/array/cell, plus a full-precision title if rounded."""
    if isinstance(x, (float, np.floating)):
        t = _num(x)
        full = repr(float(x))
        return t, (full if t != full and not _isnan(x) else None)
    if isinstance(x, np.integer):
        return str(int(x)), None
    return repr(x), None


def _same(x, y):
    if _isnan(x) and _isnan(y):
        return True
    try:
        return bool(x == y)
    except Exception:
        return repr(x) == repr(y)


# ------------------------------------------------------------------ tokens
def _tok(text, op, title=None):
    return [text, op, title] if title else [text, op]


def _collapse(items, context):
    """Shorten long runs of unchanged items to context + an ellipsis item."""
    out, run = [], []
    ell = ("…", "eq", None)

    def flush(at_start, at_end):
        if len(run) <= 2 * context + 1:
            out.extend(run)
        elif at_start and at_end:
            out.extend(run[:context] + [ell] + run[-context:])
        elif at_start:
            out.extend([ell] + run[-context:])
        elif at_end:
            out.extend(run[:context] + [ell])
        else:
            out.extend(run[:context] + [ell] + run[-context:])
        run.clear()

    for it in items:
        if it[1] == "eq":
            run.append(it)
        else:
            if run:
                flush(not out, False)
            out.append(it)
    if run:
        flush(not out, True)
    return out


def _join(items, open_, close, sep=", "):
    toks = [_tok(open_, "eq")]
    for k, it in enumerate(items):
        if k:
            toks.append(_tok(sep, "eq"))
        toks.append(_tok(*it))
    toks.append(_tok(close, "eq"))
    return toks


def _item(x, op):
    t, title = _show(x)
    return (t, op, title)


def _seq(b, a, open_, close):
    rb, ra = [repr(x) for x in b], [repr(x) for x in a]
    left, right = [], []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, rb, ra, autojunk=False).get_opcodes():
        o_b, o_a = ("eq", "eq") if op == "equal" else ("del", "add")
        left += [_item(x, o_b) for x in b[i1:i2]]
        right += [_item(x, o_a) for x in a[j1:j2]]
    return {"kind": "tokens", "before": _join(_collapse(left, CONTEXT), open_, close),
            "after": _join(_collapse(right, CONTEXT), open_, close)}


def _dict(b, a):
    def entry(k, v, op):
        t, title = _show(v)
        return (f"{k!r}: {t}", op, title)
    left, right = [], []
    for k in list(b) + [k for k in a if k not in b]:
        if k in b and k in a:
            op_b, op_a = ("eq", "eq") if repr(b[k]) == repr(a[k]) else ("del", "add")
            left.append(entry(k, b[k], op_b)); right.append(entry(k, a[k], op_a))
        elif k in b:
            left.append(entry(k, b[k], "del"))
        else:
            right.append(entry(k, a[k], "add"))
    return {"kind": "tokens", "before": _join(_collapse(left, CONTEXT), "{", "}"),
            "after": _join(_collapse(right, CONTEXT), "{", "}")}


# ------------------------------------------------------------------ strings
def _visible_ws(s):
    return s.replace(" ", "·").replace("\n", "⏎").replace("\t", "→")


def _merge_tiny(ops, tb, ta):
    """Absorb unchanged whitespace/one-punctuation gaps between two changes."""
    segs = []                                   # (op, btokens, atokens)
    for op, i1, i2, j1, j2 in ops:
        segs.append(["eq" if op == "equal" else "chg", tb[i1:i2], ta[j1:j2]])
    for k in range(1, len(segs) - 1):
        s = segs[k]
        tiny = len(s[1]) == 1 and not s[1][0].strip("  \t\n") or (
            len(s[1]) == 1 and re.fullmatch(r"[^\w\s]", s[1][0]))
        if s[0] == "eq" and tiny and segs[k - 1][0] == "chg" and segs[k + 1][0] == "chg":
            s[0] = "chg"
    merged = []
    for s in segs:                              # merge adjacent segments of the same kind
        if merged and merged[-1][0] == s[0]:
            merged[-1][1] += s[1]; merged[-1][2] += s[2]
        else:
            merged.append([s[0], list(s[1]), list(s[2])])
    return merged


def _str(b, a):
    if max(len(b), len(a)) > MAX_STR:
        return None
    tb, ta = _TOKEN.findall(b), _TOKEN.findall(a)
    segs = _merge_tiny(SequenceMatcher(None, tb, ta, autojunk=False).get_opcodes(), tb, ta)
    left, right, changed = [], [], 0
    for kind, sb, sa in segs:
        if kind == "eq":
            left.append(("eq", sb)); right.append(("eq", sa))
        else:
            left.append(("del", sb)); right.append(("add", sa))
            changed += sum(1 for t in sa if t.strip())

    def render(parts):
        out = []
        for op, toks in parts:
            text = "".join(toks)
            if op == "eq" and len(toks) > 2 * STR_CONTEXT + 1:
                head, tail = "".join(toks[:STR_CONTEXT]), "".join(toks[-STR_CONTEXT:])
                is_first, is_last = parts[0][1] is toks, parts[-1][1] is toks
                text = ("" if is_first else head) + "…" + ("" if is_last else tail)
            elif op != "eq" and not text.strip():
                text = _visible_ws(text)
            if text:
                out.append(_tok(text, op))
        return [_tok("'", "eq")] + out + [_tok("'", "eq")]

    cap = f"{changed} word{'s' if changed != 1 else ''} changed" if changed else "whitespace changed"
    return {"kind": "tokens", "before": render(left), "after": render(right), "caption": cap}


# ------------------------------------------------------------------ arrays
def _array1d(b, a):
    same = [_same(x, y) for x, y in zip(b, a)]
    left = [_item(x, "eq" if s else "del") for x, s in zip(b, same)]
    right = [_item(y, "eq" if s else "add") for y, s in zip(a, same)]
    return {"kind": "tokens", "before": _join(_collapse(left, CONTEXT), "[", "]"),
            "after": _join(_collapse(right, CONTEXT), "[", "]")}


def _grid(b, a):
    """2-D grid of the after-array; changed cells marked when shapes match."""
    same_shape = b is not MISSING and b.shape == a.shape
    rows, total = [], 0
    for r in range(a.shape[0]):
        cells = []
        for c in range(a.shape[1]):
            t, title = _show(a[r, c].item() if hasattr(a[r, c], "item") else a[r, c])
            if same_shape and not _same(b[r, c], a[r, c]):
                old_t, old_full = _show(b[r, c].item() if hasattr(b[r, c], "item") else b[r, c])
                cells.append([t, "add", f"was {old_full or old_t}"]); total += 1
            else:
                cells.append([t, "eq", title] if title else [t, "eq"])
        rows.append({"label": str(r), "status": "eq", "cells": cells})
    shown = [{**r, "cells": r["cells"][:MAX_COLS]} for r in rows[:MAX_ROWS]]
    visible = sum(c[1] == "add" for r in shown for c in r["cells"])
    cap = None if same_shape else (
        f"shape {tuple(b.shape)} → {tuple(a.shape)}" if b is not MISSING else None)
    return {"kind": "table", "cols": [str(c) for c in range(a.shape[1])][:MAX_COLS],
            "cols_more": max(a.shape[1] - MAX_COLS, 0), "rows": shown,
            "rows_more": max(a.shape[0] - MAX_ROWS, 0),
            "hidden_changes": total - visible, "caption": cap}


def _array(b, a):
    if a.ndim == 2 and (b is MISSING or b.ndim == 2):
        return _grid(b, a)
    if b is not MISSING and b.shape == a.shape and a.ndim == 1:
        return _array1d(b, a)
    return None


def _rect(x):
    return (isinstance(x, list) and x and all(isinstance(r, list) for r in x)
            and len({len(r) for r in x}) == 1 and len(x[0]) > 0
            and all(not isinstance(v, (list, dict, set, tuple)) for r in x for v in r))


def _obj_array(x):
    arr = np.empty((len(x), len(x[0])), dtype=object)
    for i, r in enumerate(x):
        for j, v in enumerate(r):
            arr[i, j] = v
    return arr


# ------------------------------------------------------------------ frames
def _cell(v):
    t, title = _show(v) if isinstance(v, (float, np.floating, np.integer)) else (str(v), None)
    return [t] if not title else [t, title]


def _frame(b, a, caption=None):
    """Row/column aware table. b may be MISSING (a brand-new frame)."""
    if b is MISSING:
        b = a.iloc[0:0]
    cols = list(b.columns) + [c for c in a.columns if c not in b.columns]
    ib, ia = list(b.index), list(a.index)

    def cells_of(df, p, op):
        out = []
        for c in cols:
            if c in df.columns:
                t = _cell(df.iloc[p][c]); out.append([t[0], op] + t[1:])
            else:
                out.append(["", op])
        return out

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
                        vb is not MISSING and not _same(vb, va))
                    t = _cell(va if ina else vb)
                    cell = [t[0], "add" if changed else "eq"] + t[1:]
                    if changed and vb is not MISSING:
                        cell = [t[0], "add", f"was {_cell(vb)[0]}"]
                    cells.append(cell)
                rows.append({"label": str(ia[q]), "status": "eq", "cells": cells})
            continue
        for p in range(i1, i2):
            rows.append({"label": str(ib[p]), "status": "del", "cells": cells_of(b, p, "del")})
        for q in range(j1, j2):
            rows.append({"label": str(ia[q]), "status": "add", "cells": cells_of(a, q, "add")})
    return {"kind": "table", "cols": [str(c) for c in cols][:MAX_COLS],
            "cols_more": max(len(cols) - MAX_COLS, 0),
            "rows": [{**r, "cells": r["cells"][:MAX_COLS]} for r in rows[:MAX_ROWS]],
            "rows_more": max(len(rows) - MAX_ROWS, 0), "caption": caption}


def _series(b, a):
    name = a.name if a.name is not None else "value"
    cap = None
    if b is not MISSING and b.dtype != a.dtype:
        cap = f"dtype {b.dtype} → {a.dtype}"
    return _frame(MISSING if b is MISSING else b.to_frame(name), a.to_frame(name), cap)


# ------------------------------------------------------------------ entry point
def detail(b, a):
    try:
        if isinstance(a, pd.DataFrame) and (b is MISSING or isinstance(b, pd.DataFrame)):
            return _frame(b, a)
        if isinstance(a, pd.Series) and (b is MISSING or isinstance(b, pd.Series)):
            return _series(b, a)
        if isinstance(a, np.ndarray) and (b is MISSING or isinstance(b, np.ndarray)):
            return _array(b, a)
        if b is MISSING:
            return None
        if _rect(a) and _rect(b) and (len(a), len(a[0])) == (len(b), len(b[0])):
            return _grid(_obj_array(b), _obj_array(a))
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
    except Exception:
        return None
    return None
