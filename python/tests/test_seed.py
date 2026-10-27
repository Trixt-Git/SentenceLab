"""Validate every seed note in content/decks/*.json.
Run: python3 -I python/tests/test_seed.py <repo root>"""
import json, pathlib, sys, warnings
warnings.simplefilter("ignore")
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / "python"))
from checker import validate

notes = []
for f in sorted((root / "content" / "decks").glob("*.json")):
    notes += json.loads(f.read_text(encoding="utf-8"))["notes"]
ids = {n["id"] for n in notes}
problems = 0
for n in notes:
    errs = validate(n["setups"], n["reference"], n["traps"], n.get("options"))
    if not 2 <= len(n["intents"]) <= 4:
        errs.append("needs 2-4 intents")
    if not n.get("rule"):
        errs.append("missing rule")
    errs += [f"requires unknown note {r}" for r in n.get("requires", []) if r not in ids]
    problems += len(errs)
    print(("OK  " if not errs else "BAD ") + n["id"], errs or "")
print("notes:", len(notes), "problems:", problems)
sys.exit(1 if problems else 0)
