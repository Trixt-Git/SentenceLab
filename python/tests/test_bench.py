"""Tests for bench() in checker.py and blank() / ref_effects() in src/python/glue.py.
Run: python3 -I python/tests/test_bench.py <repo root>"""
import json, pathlib, sys, warnings
warnings.simplefilter("ignore")
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / "python"))
sys.path.insert(0, str(root / "src" / "python"))
from checker import bench
import glue

bad = 0
total = 0


def expect(name, ok, detail=""):
    global bad, total
    total += 1
    bad += not ok
    print(("OK  " if ok else "BAD ") + name, "" if ok else detail)


def obj(state, key):
    return next(o for o in state["objects"] if o["key"] == key)


# --- aliasing, rebinding, mutation -------------------------------------------------
b = bench("a = [1, 2]\nb = a", "a.append(3)")
keys = {n["name"]: n["key"] for n in b["before"]["names"]}
expect("alias: two names share one key", keys["a"] == keys["b"], keys)
expect("alias: one box for both names", len(b["before"]["objects"]) == 1)
expect("mutate: same key before and after", {n["name"]: n["key"] for n in b["after"]["names"]} == keys)
expect("mutate: object flagged changed", obj(b["after"], keys["a"])["changed"] is True)
expect("mutate: before preview is not changed", obj(b["before"], keys["a"])["changed"] is False)
expect("mutate: before preview kept the old items", len(obj(b["before"], keys["a"])["preview"]["items"]) == 2)
expect("mutate: after preview shows the new item", len(obj(b["after"], keys["a"])["preview"]["items"]) == 3)

b = bench("a = [1, 2]\nb = a", "a = a + [3]")
ka, kb = ({n["name"]: n["key"] for n in b["after"]["names"]}[x] for x in "ab")
expect("rebind: a points at a new object, b keeps the old", ka != kb)
expect("rebind: the new object is not flagged changed", obj(b["after"], ka)["changed"] is False)

b = bench("x = 1", "del x")
expect("delete: name gone after", [n["name"] for n in b["after"]["names"]] == [] and len(b["before"]["names"]) == 1)

# --- limits and specials -------------------------------------------------------------
b = bench("xs = list(range(20))\nnested = [[[1, [2]]]]", "")
xs = obj(b["before"], b["before"]["names"][0]["key"])["preview"]
expect("limit: lists show 8 items and count the rest", len(xs["items"]) == 8 and xs["more"] == 12, xs)
nested = obj(b["before"], b["before"]["names"][1]["key"])["preview"]
inner = nested["items"][0]["items"][0]
expect("limit: containers nest 2 levels, then text", inner["kind"] == "other", inner)

b = bench("v = [float('nan'), float('inf'), float('-inf'), 1.5]", "")
items = obj(b["before"], b["before"]["names"][0]["key"])["preview"]["items"]
expect("special: nan, inf, -inf become null with a marker",
       [i.get("special") for i in items] == ["nan", "inf", "-inf", None] and items[0]["value"] is None, items)
expect("special: output is valid JSON", bool(json.dumps(b, allow_nan=False)))

b = bench("import pandas as pd\ndf = pd.DataFrame({'a': list(range(8)), 'b': [None] * 8})", "")
df = obj(b["before"], b["before"]["names"][0]["key"])["preview"]
expect("dataframe: head(5), shape, columns, more", df["shape"] == [8, 2] and len(df["rows"]) == 5 and df["more"] == 3
       and df["columns"] == ["a", "b"], df)
expect("dataframe: missing values are null", df["rows"][0][1]["value"] is None)

b = bench("import numpy as np\narr = np.arange(20).reshape(4, 5)", "")
arr = obj(b["before"], b["before"]["names"][0]["key"])["preview"]
expect("ndarray: shape and first 8 values", arr["shape"] == [4, 5] and len(arr["values"]) == 8 and arr["more"] == 12, arr)

# --- models ----------------------------------------------------------------------------
b = bench("import numpy as np\nfrom sklearn.linear_model import LinearRegression\nX = np.arange(6).reshape(3, 2)\n"
          "y = np.arange(3) * 1.0\nmodel = LinearRegression()", "model.fit(X, y)")
mk = next(n["key"] for n in b["before"]["names"] if n["name"] == "model")
expect("model: unfitted before, fitted after",
       obj(b["before"], mk)["preview"] == {"kind": "model", "cls": "LinearRegression", "fitted": False}
       and obj(b["after"], mk)["preview"]["fitted"] is True)
expect("model: fit flags the model as changed", obj(b["after"], mk)["changed"] is True)

# --- errors never throw ------------------------------------------------------------------
b = bench("x = 1", "x = (")
expect("syntax error: reported, state unchanged", b["error"]["type"] == "SyntaxError" and b["before"] == b["after"])
b = bench("x = [1]", "y = x[5]")
expect("runtime error: reported", b["error"]["type"] == "IndexError")
b = bench("x = [1]", "print('hi')")
expect("print is captured", b["stdout"] == "hi\n")
b = bench("x = 1", "")
expect("empty line: same state twice", b["before"] == b["after"] and b["error"] is None)

# --- every seed instance: JSON-safe, reference changes something ------------------------------
n = 0
for f in sorted((root / "content" / "decks").glob("*.json")):
    for p in json.loads(f.read_text(encoding="utf-8"))["patterns"]:
        for inst in p["instances"]:
            for s in inst["setups"]:
                r = bench(s, inst["reference"])
                json.dumps(r, allow_nan=False)
                n += 1
                if r["error"]:
                    expect(f"seed {inst['id']}: reference runs on the bench", False, r["error"])
expect(f"seed: {n} benches are JSON-safe and error-free", True)

# --- blank(): filling the blank with the removed text restores the line ---------------------------------
filled_ok, blanked_n, parts_seen = True, 0, set()
for f in sorted((root / "content" / "decks").glob("*.json")):
    for p in json.loads(f.read_text(encoding="utf-8"))["patterns"]:
        for inst in p["instances"]:
            line = inst["reference"]
            for part in glue.PARTS:
                r = glue.blank(line, part)
                if r is None:
                    continue
                blanked_n += 1
                parts_seen.add(part)
                restored = r["blanked"].replace("____", r["answer"], 1)
                if restored.replace(" ", "") != line.replace(" ", "") or "____" not in r["blanked"]:
                    filled_ok = False
                    print("   blank mismatch:", part, repr(line), "->", repr(r["blanked"]), "|", repr(r["answer"]))
expect(f"blank: {blanked_n} blanks restore their lines exactly", filled_ok)
expect("blank: every part is blankable somewhere", parts_seen == set(glue.PARTS), parts_seen)
expect("blank: landing swallows the =", glue.blank("df = df.dropna(subset=['price'])", "landing")["blanked"]
       == "____ df.dropna(subset=['price'])")
expect("blank: method verb keeps its dot", glue.blank("df = df.dropna()", "verb")["answer"] == ".dropna")
expect("blank: operator verb", glue.blank("big = qty > 10", "verb")["blanked"] == "big = qty ____ 10")
expect("blank: bare call has no landing", glue.blank("fruits.append('kiwi')", "landing") is None)
expect("blank: lookup has no verb", glue.blank("age = ages['Ana']", "verb") is None)
expect("blank: function call has no subject", glue.blank("n = len(orders)", "subject") is None)
expect("blank: brackets stay around a blanked operand",
       glue.blank("mask = (df['a'] > 1) & (df['a'] < 5)", "verb")["blanked"] == "mask = (df['a'] > 1) ____ (df['a'] < 5)")

# --- ref_effects ---------------------------------------------------------------------------------------
e = glue.ref_effects("stack = [1, 2]", "top = stack.pop()")
expect("ref_effects: pop rebinds top and mutates stack",
       e["rebound"] == ["top"] and e["mutated"] == ["stack"] and e["effects"] == ["mutates", "rebinds"], e)

print("bench tests:", total, "failed:", bad)
sys.exit(1 if bad else 0)
