"""Sentence Lab checker v2 — runs inside Pyodide (Web Worker). Reference implementation.

check(setup, reference, answer, options=None)      -> result dict for one setup
check_all(setups, reference, answer, options=None) -> first failing setup's result, else the last passing one
  options: {"ignore_order": bool}  (per note; default False)
validate(setups, reference, traps, options=None)   -> list of authoring errors (empty = note is usable)
A correct result may carry "style": advice when the line works but isn't the preferred form.
parts(line)                          -> nested dict for the sentence diagram
"""
import ast, builtins, contextlib, copy, io, math, numbers, pickle, random, sys, types, warnings

SKIP_TYPES = (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)
ITER_TYPES = (types.GeneratorType, map, filter, zip, enumerate, reversed,
              type(iter([])), type(iter(())), type(iter("")), type(iter(range(0))), type(iter({})))
REL, ABS = 1e-9, 1e-12


# ---------- equality ----------

def _is_bool(x):
    t = type(x)
    return isinstance(x, bool) or (t.__module__ == "numpy" and t.__name__ in ("bool", "bool_"))


def _is_num(x):
    return isinstance(x, numbers.Number) and not _is_bool(x)


def _pickle_equal(a, b):
    try:
        return pickle.dumps(a) == pickle.dumps(b)
    except Exception:
        return False


def same(a, b, _seen=None):
    """Value equality for learner answers: NaN == NaN, float tolerance, numpy/python scalars
    interchangeable, pandas/numpy aware, fitted estimators by params + fitted attributes."""
    if a is b:
        return True
    _seen = _seen if _seen is not None else set()
    key = (id(a), id(b))
    if key in _seen:                      # self-referencing structures
        return True
    _seen.add(key)

    if _is_bool(a) or _is_bool(b):
        return _is_bool(a) and _is_bool(b) and bool(a) == bool(b)
    if _is_num(a) and _is_num(b):
        try:
            fa, fb = complex(a), complex(b)
        except Exception:
            return False
        if any(math.isnan(v) for v in (fa.real, fa.imag)) or any(math.isnan(v) for v in (fb.real, fb.imag)):
            return all(math.isnan(v) for v in (fa.real, fb.real)) if fa.imag == fb.imag == 0 else False
        return math.isclose(fa.real, fb.real, rel_tol=REL, abs_tol=ABS) and \
            math.isclose(fa.imag, fb.imag, rel_tol=REL, abs_tol=ABS)

    pd = sys.modules.get("pandas")
    if pd is not None and isinstance(a, (pd.DataFrame, pd.Series, pd.Index)):
        if type(a) is not type(b) and not (isinstance(a, pd.Index) and isinstance(b, pd.Index)):
            return False
        try:
            kw = dict(check_dtype=False, check_exact=False, rtol=REL, atol=ABS)
            if isinstance(a, pd.DataFrame):
                pd.testing.assert_frame_equal(a, b, check_index_type=False, check_column_type=False,
                                              check_categorical=False, **kw)
            elif isinstance(a, pd.Series):
                pd.testing.assert_series_equal(a, b, check_index_type=False, check_names=False,
                                               check_categorical=False, **kw)
            else:
                pd.testing.assert_index_equal(a, b, exact=False, check_names=False, check_exact=False,
                                              rtol=REL, atol=ABS)
            return True
        except AssertionError:
            return False
        except Exception:
            return _pickle_equal(a, b)

    np = sys.modules.get("numpy")
    if np is not None and (isinstance(a, np.ndarray) or isinstance(b, np.ndarray)):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)) or a.shape != b.shape:
            return False
        try:
            if a.dtype.kind in "biufc" and b.dtype.kind in "biufc":
                return bool(np.allclose(a, b, rtol=REL, atol=ABS, equal_nan=True))
            return all(same(x, y, _seen) for x, y in zip(a.ravel().tolist(), b.ravel().tolist()))
        except Exception:
            return _pickle_equal(a, b)

    if type(a) is not type(b):
        return False
    if isinstance(a, ITER_TYPES):
        return True                       # can't inspect without consuming; see Known limits
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], _seen) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y, _seen) for x, y in zip(a, b))
    if isinstance(a, (set, frozenset)):
        return a == b
    if hasattr(a, "get_params") and hasattr(a, "fit"):          # scikit-learn estimators
        if not same(a.get_params(deep=False), b.get_params(deep=False), _seen):
            return False
        fa = {k for k in vars(a) if k.endswith("_") and not k.startswith("_")}
        fb = {k for k in vars(b) if k.endswith("_") and not k.startswith("_")}
        return fa == fb and all(same(getattr(a, k), getattr(b, k), _seen) for k in fa)
    if hasattr(a, "__dict__") and not isinstance(a, (str, bytes)):
        return same(vars(a), vars(b), _seen)
    if type(a).__eq__ is object.__eq__:  # no value equality defined (e.g. a fitted tree's internals)
        if hasattr(a, "__getstate__"):
            try:
                return same(a.__getstate__(), b.__getstate__(), _seen)
            except Exception:
                pass
        return _pickle_equal(a, b)
    try:
        r = a == b
        return bool(r) if isinstance(r, bool) else _pickle_equal(a, b)
    except Exception:
        return _pickle_equal(a, b)


# ---------- running a line ----------

def _visible(ns):
    return {k: v for k, v in ns.items() if not k.startswith("__") and not isinstance(v, SKIP_TYPES)}


def _copy(v):
    try:
        return copy.deepcopy(v)
    except Exception:
        return v                          # uncopyable: its mutation can't be detected


def _seed():
    random.seed(0)
    np = sys.modules.get("numpy")
    if np is not None:
        np.random.seed(0)


def targets(line):
    """Names a line lands its result in (assignment targets), read from the syntax."""
    out = set()
    try:
        tree = ast.parse(line)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        tgts = node.targets if isinstance(node, ast.Assign) else \
            [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.NamedExpr)) else []
        for t in tgts:
            for n in ast.walk(t):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    out.add(n.id)
    return out


def imported(line):
    """Names a line creates with import statements; never compared."""
    out = set()
    try:
        tree = ast.parse(line)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                out.add((a.asname or a.name).split(".")[0])
    return out


IGNORED = {"_"}


def _normalise(v, options):
    """Per-note relaxations applied before comparing."""
    if not options or not options.get("ignore_order"):
        return v
    pd = sys.modules.get("pandas")
    if pd is not None and isinstance(v, pd.DataFrame):
        try:
            return v.sort_index(axis=0).sort_index(axis=1)
        except Exception:
            return v
    if pd is not None and isinstance(v, pd.Series):
        try:
            return v.sort_index()
        except Exception:
            return v
    if isinstance(v, list):
        try:
            return sorted(v)
        except Exception:
            return v
    return v


def run(setup, line):
    saved_builtins = dict(builtins.__dict__)
    ns = {"__builtins__": builtins}
    out = io.StringIO()
    dropped, error, warned, setup_error = None, None, [], None
    try:
        _seed()
        try:
            exec(setup, ns)
        except BaseException as e:        # a broken note setup must never crash the checker
            setup_error = {"type": type(e).__name__, "message": str(e)}
            return {"setup_error": setup_error, "ns": {}, "rebound": [], "mutated": [], "deleted": [],
                    "landed": [], "stdout": "", "dropped": None, "error": None, "warnings": []}
        before_ids = {k: id(v) for k, v in _visible(ns).items()}
        before_vals = {k: _copy(v) for k, v in _visible(ns).items()}
        tree = ast.parse(line, mode="exec")
        _seed()
        try:
            with contextlib.redirect_stdout(out), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                    dropped = eval(compile(ast.Expression(tree.body[0].value), "<line>", "eval"), ns)
                else:
                    exec(compile(tree, "<line>", "exec"), ns)
            warned = sorted({type(w.message).__name__ for w in caught})
        except KeyboardInterrupt:
            error = {"type": "Timeout", "message": "the line ran too long and was stopped"}
        except BaseException as e:        # includes SystemExit from exit()
            error = {"type": type(e).__name__, "message": str(e)}
    finally:
        builtins.__dict__.clear()
        builtins.__dict__.update(saved_builtins)
    after = _visible(ns)
    landed = targets(line)
    changed = {k for k, v in after.items() if before_ids.get(k) == id(v) and not same(v, before_vals[k])}
    # rebound: the name points at a different object, or it was assigned to (even if Python reused the object)
    rebound = sorted(k for k, v in after.items()
                     if before_ids.get(k) != id(v) or (k in landed and k not in changed))
    mutated = sorted(changed)          # same object, new contents (includes list += ...)
    deleted = sorted(k for k in before_ids if k not in after)
    return {"ns": after, "rebound": rebound, "mutated": mutated, "deleted": deleted,
            "landed": sorted(landed), "stdout": out.getvalue(), "dropped": dropped, "error": error,
            "warnings": warned, "setup_error": None}


def effects(r):
    e = set()
    if r["rebound"] or r["deleted"]:
        e.add("rebinds")
    if r["mutated"]:
        e.add("mutates")
    if r["stdout"]:
        e.add("sends_out")
    return sorted(e) or ["nothing"]


# ---------- comparing ----------

def _short(v, n=60):
    s = repr(v)
    return s if len(s) <= n else s[: n - 1] + "…"


def _verb_of(line):
    try:
        node = ast.parse(line).body[0]
    except Exception:
        return None
    value = getattr(node, "value", None)
    if isinstance(value, ast.Call):
        f = value.func
        return "." + f.attr + "()" if isinstance(f, ast.Attribute) else getattr(f, "id", None)
    return None


RUN_BLAME = {"NameError": "subject", "AttributeError": "verb", "TypeError": "details", "KeyError": "details",
             "IndexError": "details", "ValueError": "details"}

HINTS = {
    "NameError": "A name in your sentence isn't on the bench.",
    "AttributeError": "That verb doesn't exist for this subject's type.",
    "TypeError": "A verb got the wrong kind of detail, or one of the parts is None.",
    "KeyError": "That key or column isn't in the subject.",
    "IndexError": "That position is past the end of the subject.",
    "ValueError": "The verb got a detail of the right type but the wrong value or shape.",
    "Timeout": "The line ran too long and was stopped.",
}


def check(setup, reference, answer, options=None):
    try:
        tree = ast.parse(answer)
    except SyntaxError as e:
        return {"correct": False, "stage": "assemble",
                "blame": "assemble", "messages": [f"Python can't read this word order (col {e.offset}): {e.msg}."]}
    if not tree.body:
        return {"correct": False, "stage": "assemble", "blame": "assemble", "messages": ["Write one line of Python."]}
    if len(tree.body) > 1:
        return {"correct": False, "stage": "assemble", "blame": "assemble",
                "messages": [f"One sentence at a time: your answer has {len(tree.body)} statements."]}

    ref, you = run(setup, reference), run(setup, answer)
    if ref["setup_error"]:
        se = ref["setup_error"]
        return {"correct": False, "stage": "note",
                "messages": [f"The note's setup fails ({se['type']}: {se['message']}); fix the note."]}
    if ref["error"]:
        return {"correct": False, "stage": "note", "messages": ["The note's reference line fails on this setup; fix the note."]}
    if you["error"]:
        t, m = you["error"]["type"], you["error"]["message"]
        return {"correct": False, "stage": "run", "blame": RUN_BLAME.get(t),
                "messages": [f"{t}: {m}", HINTS.get(t, "Python stopped before the line finished.")],
                "effects": {"reference": effects(ref), "yours": []}}

    msgs, ok = [], True
    must_land = set(ref["landed"]) - set(you["landed"]) - set(you["mutated"])
    for n in sorted(must_land):
        ok = False
        msgs.append(f"Landing: the result should land in `{n}` ({n} = ...). Your line didn't put anything there.")

    for n in sorted(set(ref["deleted"]) ^ set(you["deleted"])):
        ok = False
        msgs.append(f"Effect: your line {'deleted' if n in you['deleted'] else 'kept'} `{n}`; the intent doesn't.")

    names = (set(ref["rebound"]) | set(ref["mutated"]) | set(you["rebound"]) | set(you["mutated"])) \
        - set(ref["deleted"]) - set(you["deleted"]) - must_land - IGNORED - (imported(answer) - set(ref["ns"]))
    for n in sorted(names):
        rv, yv = ref["ns"].get(n, "<missing>"), you["ns"].get(n, "<missing>")
        if same(_normalise(rv, options), _normalise(yv, options)):
            continue
        ok = False
        if n not in you["ns"]:
            msgs.append(f"Landing: the result should land in `{n}`, but your line never creates `{n}`.")
        elif n not in ref["ns"]:
            msgs.append(f"Landing: your line creates `{n}`, which the intent doesn't ask for.")
        elif yv is None and rv is not None:
            v = _verb_of(answer)
            msgs.append(f"`{n}` is now None. {v or 'Your verb'} changes its subject in place and returns None,"
                        f" so there was nothing to land in `{n}`.")
        elif n in you["mutated"] and n not in ref["mutated"] and n not in ref["rebound"]:
            msgs.append(f"Effect: your line changed `{n}` itself; the intent wants it left as it was.")
        elif n in ref["mutated"] and n not in you["mutated"] and n not in you["rebound"]:
            msgs.append(f"Effect: `{n}` should have changed, but your line left it as it was.")
        elif hasattr(rv, "get_params") and hasattr(rv, "fit"):
            msgs.append(f"`{n}` is fitted differently from the reference. Check which data the verb was given"
                        f" (for example X_train vs X).")
        elif type(rv) is not type(yv) and rv is not None and yv is not None:
            msgs.append(f"`{n}` should be a {type(rv).__name__} but is a {type(yv).__name__}.")
        elif getattr(rv, "shape", None) is not None and getattr(rv, "shape", None) != getattr(yv, "shape", None):
            msgs.append(f"`{n}` should have shape {tuple(rv.shape)} but has {tuple(yv.shape)}.")
        elif _short(rv) == _short(yv):
            msgs.append(f"`{n}` looks the same when printed, but its contents differ from the reference.")
        else:
            msgs.append(f"`{n}` should be {_short(rv)} but is {_short(yv)}.")
    if ref["stdout"] != you["stdout"]:
        ok = False
        if ref["stdout"] and not you["stdout"] and you["dropped"] is not None:
            msgs.append("Sends out: a notebook shows a bare value, but this card wants it printed: print(...).")
        else:
            msgs.append(f"Sends out: expected output {ref['stdout']!r}, got {you['stdout']!r}.")
    both_bare = isinstance(ast.parse(reference).body[0], ast.Expr) and isinstance(tree.body[0], ast.Expr)
    if ok and both_bare and not same(ref["dropped"], you["dropped"]):
        ok = False
        msgs.append(f"The line's value should be {_short(ref['dropped'])} but is {_short(you['dropped'])}.")
    if not ok and "ChainedAssignmentError" in you["warnings"]:
        msgs.insert(0, "Effect: pandas never changes df through a chain like df['col'][row] = ... or"
                       " df['col'].method(inplace=True). Land the result: df.loc[row, 'col'] = ... or df['col'] = ...")
    blame = None
    if msgs:
        m = msgs[0]
        blame = "landing" if m.startswith("Landing") else "effect" if m.startswith(("Effect", "Sends out")) \
            else "verb" if "is now None" in m else None
    return {"correct": ok, "stage": "compare", "blame": blame if not ok else None,
            "messages": msgs or ["Same effects, same result."],
            "style": style(answer) if ok else [],
            "effects": {"reference": effects(ref), "yours": effects(you)}}


def style(answer):
    """'Works, but' advice for correct lines that aren't the preferred form. Never affects correctness."""
    notes = []
    try:
        tree = ast.parse(answer)
    except SyntaxError:
        return notes
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "inplace" and \
                isinstance(node.value, ast.Constant) and node.value.value is True:
            notes.append("Works, but pandas is phasing out inplace=True. Prefer landing the result: df = df.method(...).")
            break
    return notes


def check_all(setups, reference, answer, options=None):
    if not setups:
        return {"correct": False, "stage": "note", "messages": ["The note has no setups; fix the note."]}
    r = None
    for i, setup in enumerate(setups):
        r = check(setup, reference, answer, options)
        if not r["correct"]:
            r["setup_index"] = i
            return r
    return r


def validate(setups, reference, traps=(), options=None):
    """Authoring checks run by the note editor's Validate button. Empty list = OK."""
    errs = []
    if len(setups) < 2:
        errs.append("Needs at least 2 setups.")
    try:
        if len(ast.parse(reference).body) != 1:
            errs.append("Reference must be exactly one statement.")
    except SyntaxError as e:
        return [f"Reference is not valid Python: {e.msg}"]
    finals = []
    for i, s in enumerate(setups):
        a, b = run(s, reference), run(s, reference)
        if a["setup_error"]:
            errs.append(f"Setup {i + 1} fails: {a['setup_error']['type']}: {a['setup_error']['message']}")
            continue
        if a["error"]:
            errs.append(f"Reference fails on setup {i + 1}: {a['error']['type']}: {a['error']['message']}")
            continue
        if effects(a) == ["nothing"] and not a["landed"]:
            errs.append(f"Reference has no visible effect on setup {i + 1}.")
        keys = sorted(set(a["rebound"]) | set(a["mutated"]))
        if not all(same(a["ns"].get(k), b["ns"].get(k)) for k in keys) or a["stdout"] != b["stdout"]:
            errs.append(f"Reference gives different results on repeat runs of setup {i + 1}; seed any randomness.")
        finals.append({k: a["ns"].get(k) for k in keys} | {"__out__": a["stdout"]})
    if len(finals) >= 2 and all(same(finals[0], f) for f in finals[1:]):
        errs.append("Every setup gives the same result, so a hard-coded answer would pass. Vary the setups.")
    for t in traps:
        if check_all(setups, reference, t, options)["correct"]:
            errs.append(f"Trap passes on every setup: {t}")
    return errs


# ---------- sentence diagram ----------

OPS = {"Add": "+", "Sub": "-", "Mult": "*", "Div": "/", "FloorDiv": "//", "Mod": "%", "Pow": "**",
       "Gt": ">", "GtE": ">=", "Lt": "<", "LtE": "<=", "Eq": "==", "NotEq": "!=", "In": "in", "NotIn": "not in",
       "Is": "is", "IsNot": "is not", "BitAnd": "&", "BitOr": "|"}


def _is_sentence(e):
    return isinstance(e, (ast.Call, ast.Subscript, ast.BinOp, ast.Compare))


def parts(line):
    tree = ast.parse(line)
    if len(tree.body) != 1:
        raise ValueError("parts() takes exactly one statement")
    node = tree.body[0]
    seg = lambda n: ast.get_source_segment(line, n)

    def sub(e):
        return {"text": seg(e), "nested": sentence(e) if _is_sentence(e) else None}

    def sentence(expr):
        d = {"subject": None, "verb": None, "details": []}
        if isinstance(expr, ast.Call):
            f = expr.func
            if isinstance(f, ast.Attribute):
                d["subject"], d["verb"] = sub(f.value), "." + f.attr
            else:
                d["verb"] = seg(f)
            d["details"] = [sub(a) for a in expr.args] + [
                {"text": seg(k), "nested": sentence(k.value) if _is_sentence(k.value) else None}
                for k in expr.keywords]
        elif isinstance(expr, ast.Subscript):
            d["subject"], d["verb"], d["details"] = sub(expr.value), "[ ]", [sub(expr.slice)]
        elif isinstance(expr, ast.BinOp):
            d["subject"], d["verb"], d["details"] = sub(expr.left), OPS.get(type(expr.op).__name__, "?"), [sub(expr.right)]
        elif isinstance(expr, ast.Compare):
            d["subject"], d["verb"], d["details"] = sub(expr.left), OPS.get(type(expr.ops[0]).__name__, "?"), [sub(expr.comparators[0])]
        else:
            d["subject"] = {"text": seg(expr), "nested": None}
        return d

    if isinstance(node, ast.Assign):
        kind = "binds" if all(isinstance(t, (ast.Name, ast.Tuple)) for t in node.targets) else "stores"
        return {"landing": {"kind": kind, "text": " = ".join(seg(t) for t in node.targets)}, **sentence(node.value)}
    if isinstance(node, ast.AugAssign):
        # "augmented": the UI labels it from the checker's effects (rebinds for numbers/strings, mutates for lists)
        return {"landing": {"kind": "augmented", "text": seg(node.target)},
                "subject": {"text": seg(node.target), "nested": None},
                "verb": OPS.get(type(node.op).__name__, "?") + "=", "details": [sub(node.value)]}
    if isinstance(node, ast.Expr):
        s = sentence(node.value)
        return {"landing": {"kind": "sends_out" if s["verb"] == "print" else "dropped", "text": None}, **s}
    return {"landing": None, "subject": {"text": line, "nested": None}, "verb": None, "details": []}


# ---------- the bench ----------

BENCH_ITEMS, BENCH_DEPTH, BENCH_ROWS = 8, 2, 5


def _py(v):
    """numpy scalars become plain Python values so previews are JSON."""
    if type(v).__module__ == "numpy" and hasattr(v, "item") and getattr(v, "shape", None) == ():
        try:
            return v.item()
        except Exception:
            return v
    return v


def _scalar(v):
    x = _py(v)
    if x is None or isinstance(x, (bool, str)):
        return {"kind": "scalar", "value": x}
    if isinstance(x, int):
        return {"kind": "scalar", "value": x}
    if isinstance(x, float):
        if math.isnan(x):
            return {"kind": "scalar", "value": None, "special": "nan"}
        if math.isinf(x):
            return {"kind": "scalar", "value": None, "special": "inf" if x > 0 else "-inf"}
        return {"kind": "scalar", "value": x}
    return None


def _preview(v, depth=0):
    """A JSON-safe picture of one object for the bench. Never returns a Python object."""
    s = _scalar(v)
    if s is not None:
        return s
    pd, np = sys.modules.get("pandas"), sys.modules.get("numpy")
    if pd is not None and isinstance(v, pd.DataFrame):
        head = v.head(BENCH_ROWS)
        return {"kind": "dataframe", "shape": [int(v.shape[0]), int(v.shape[1])],
                "columns": [str(c) for c in v.columns], "index": [_scalar_or_text(i) for i in head.index],
                "rows": [[_scalar_or_text(c) for c in row] for row in head.itertuples(index=False, name=None)],
                "more": max(0, int(v.shape[0]) - BENCH_ROWS)}
    if pd is not None and isinstance(v, pd.Series):
        head = v.head(BENCH_ITEMS)
        return {"kind": "series", "length": int(len(v)),
                "items": [{"index": _scalar_or_text(i), "value": _scalar_or_text(x)} for i, x in head.items()],
                "more": max(0, int(len(v)) - BENCH_ITEMS)}
    if np is not None and isinstance(v, np.ndarray):
        flat = v.ravel()[:BENCH_ITEMS].tolist()
        return {"kind": "ndarray", "shape": [int(n) for n in v.shape], "values": [_scalar_or_text(x) for x in flat],
                "more": max(0, int(v.size) - BENCH_ITEMS)}
    if hasattr(v, "get_params") and hasattr(v, "fit"):
        return {"kind": "model", "cls": type(v).__name__,
                "fitted": any(k.endswith("_") and not k.startswith("_") for k in vars(v))}
    if isinstance(v, (list, tuple, set, frozenset)):
        if depth >= BENCH_DEPTH:
            return {"kind": "other", "text": _short(v)}
        items = list(v)
        if isinstance(v, (set, frozenset)):
            try:
                items = sorted(items)
            except Exception:
                pass
        return {"kind": "list", "items": [_preview(x, depth + 1) for x in items[:BENCH_ITEMS]],
                "more": max(0, len(items) - BENCH_ITEMS)}
    if isinstance(v, dict):
        if depth >= BENCH_DEPTH:
            return {"kind": "other", "text": _short(v)}
        items = list(v.items())
        return {"kind": "dict", "items": [{"key": _preview(k, depth + 1), "value": _preview(x, depth + 1)}
                                          for k, x in items[:BENCH_ITEMS]],
                "more": max(0, len(items) - BENCH_ITEMS)}
    return {"kind": "other", "text": _short(v, 80)}


def _scalar_or_text(x):
    return _scalar(x) or {"kind": "other", "text": _short(x, 40)}


def bench(setup, line=""):
    """State of the world before and after a line, for the bench (ARCHITECTURE.md section 8).

    Each state is {"names": [{"name", "key"}], "objects": [{"key", "type", "preview", "changed"}]}. Keys are
    o1, o2, ... in order of first appearance and are shared by before and after, so an object that survives keeps
    its key and two names with one key are aliases. An empty line returns the same state twice."""
    saved_builtins = dict(builtins.__dict__)
    ns = {"__builtins__": builtins}
    keys, keep = {}, {}               # keep holds every object seen, so Python can't reuse an id mid-call
    out, error = io.StringIO(), None

    def key_of(v):
        if id(v) not in keys:
            keys[id(v)] = f"o{len(keys) + 1}"
            keep[id(v)] = v
        return keys[id(v)]

    def state(vis, changed=frozenset()):
        names = [{"name": n, "key": key_of(v)} for n, v in vis.items()]
        seen, objects = set(), []
        for v in vis.values():
            if id(v) in seen:
                continue
            seen.add(id(v))
            objects.append({"key": key_of(v), "type": type(v).__name__, "preview": _preview(v),
                            "changed": id(v) in changed})
        return {"names": names, "objects": objects}

    try:
        _seed()
        exec(setup, ns)
        vis0 = _visible(ns)
        before = state(vis0)
        before_vals = {id(v): _copy(v) for v in vis0.values()}
        if line.strip():
            try:
                tree = ast.parse(line)
                _seed()
                with contextlib.redirect_stdout(out), warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    exec(compile(tree, "<line>", "exec"), ns)
            except SyntaxError as e:
                error = {"type": "SyntaxError", "message": e.msg}
            except BaseException as e:
                error = {"type": type(e).__name__, "message": str(e)}
        vis1 = _visible(ns)
        changed = {id(v) for v in vis1.values() if id(v) in before_vals and not same(v, before_vals[id(v)])}
        after = state(vis1, changed)
    finally:
        builtins.__dict__.clear()
        builtins.__dict__.update(saved_builtins)
    return {"before": before, "after": after, "error": error, "stdout": out.getvalue()}
