"""Validate every pattern and instance in content/decks/*.json.
Run: python3 -I python/tests/test_seed.py <repo root>"""
import json, pathlib, sys, warnings
warnings.simplefilter("ignore")
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / "python"))
from checker import validate

patterns = []
for f in sorted((root / "content" / "decks").glob("*.json")):
    patterns += json.loads(f.read_text(encoding="utf-8"))["patterns"]
pids = {p["id"] for p in patterns}
iids = [i["id"] for p in patterns for i in p["instances"]]
problems = 0
if len(iids) != len(set(iids)):
    print("BAD  duplicate instance ids"); problems += 1
n_inst = 0
for p in patterns:
    perrs = []
    practice = [i for i in p["instances"] if i["role"] == "practice"]
    cold = [i for i in p["instances"] if i["role"] == "cold"]
    if len(practice) < 3:
        perrs.append("needs at least 3 practice instances")
    if len(cold) < 1:
        perrs.append("needs at least 1 cold instance")
    if not p.get("rule"):
        perrs.append("missing rule")
    perrs += [f"requires unknown pattern {r}" for r in p.get("requires", []) if r not in pids]
    if len({i["reference"] for i in p["instances"]}) != len(p["instances"]):
        perrs.append("instances must differ (same reference twice)")
    problems += len(perrs)
    print(("OK  " if not perrs else "BAD ") + p["id"], perrs or "")
    for i in p["instances"]:
        n_inst += 1
        errs = validate(i["setups"], i["reference"], i["traps"], p.get("options"))
        if not 2 <= len(i["intents"]) <= 4:
            errs.append("needs 2-4 intents")
        problems += len(errs)
        if errs:
            print("   BAD " + i["id"], errs)
print("patterns:", len(patterns), "instances:", n_inst, "problems:", problems)
sys.exit(1 if problems else 0)
