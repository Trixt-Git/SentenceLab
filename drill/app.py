"""Local drill server: `uvicorn app:app` from this directory."""
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from drills import DRILLS
from explain import EXPLAINS
from engine import check_blanks, check_slots, describe, probe_runs, run_line
from lessons import BY_ID, LESSONS
from scheduler import Scheduler

HERE = Path(__file__).parent
app = FastAPI()
sched = Scheduler(DRILLS, LESSONS, EXPLAINS, Path(os.environ.get("DRILL_HISTORY", HERE / "history.csv")))
BY_DRILL = {d.id: d for d in DRILLS}


def get(i: int):
    if not 0 <= i < len(DRILLS):
        raise HTTPException(404, "no such drill")
    return DRILLS[i]


def lesson(lid: str):
    if lid not in BY_ID:
        raise HTTPException(404, "no such lesson")
    return BY_ID[lid]


class Effect(BaseModel):
    effect: str


class Slots(BaseModel):
    slots: dict


class Code(BaseModel):
    code: str
    confident: bool = True


class Check(BaseModel):
    stage: str
    choice: int | None = None
    blanks: list[str] = []


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/next")
def next_item(kind: str = ""):
    n = sched.next(kind)
    if n["kind"] == "explain":
        n["index"] = next(k for k, x in enumerate(EXPLAINS) if x.id == n["id"])
    if n["kind"] == "drill":
        n["index"] = DRILLS.index(BY_DRILL[n["id"]])
        n["total"] = len(DRILLS)
    return n


# ---------------------------------------------------------------- drills
@app.get("/api/drill/{i}")
def drill(i: int):
    d = get(i)
    return {"index": i, "total": len(DRILLS), "id": d.id, "domain": d.domain,
            "plan": d.plan, "effect_count": len({x.effect for x in DRILLS}),
            "intent": d.intent, "state": describe(d.setup())}


@app.post("/api/drill/{i}/effect")
def effect(i: int, body: Effect):
    d = get(i)
    return {"ok": body.effect == d.effect, "answer": d.effect}


@app.post("/api/drill/{i}/slots")
def slots(i: int, body: Slots):
    return check_slots(get(i), body.slots)


@app.get("/api/drill/{i}/reveal")
def reveal(i: int):
    return {k: v[0] for k, v in get(i).grammar.items()}


@app.post("/api/drill/{i}/run")
def run(i: int, body: Code):
    d = get(i)
    res = run_line(d, body.code)
    n = sched.record(d, res["passed"], body.confident)
    res["attempt"] = n
    if res["passed"]:
        res["reference_line"] = d.reference_line
    elif body.confident:
        res["hints"].append("You were sure about that one, so it will come back for review soon.")
    return res


@app.post("/api/drill/{i}/hint")
def hint(i: int):
    """Tiered hints, unlocked by failed attempts: slots, partial line, full line."""
    d = get(i)
    fails = sched.failures(d.id)
    if fails == 0:
        return {"level": 0, "text": "Give it a try first. Hints unlock after a wrong attempt."}
    if fails == 1:
        g = d.grammar
        return {"level": 1, "text": " · ".join(f"{k}: {v[0]}" for k, v in g.items())}
    if fails == 2:
        det = d.grammar["details"][0]
        masked = d.reference_line.replace(det, "…") if det not in ("none", "nothing") else d.reference_line
        return {"level": 2, "text": masked}
    return {"level": 3, "text": d.reference_line}


# --------------------------------------------------------------- lessons
def _public(l):
    strip = lambda d, *drop: {k: v for k, v in d.items() if k not in drop}
    return {"id": l.id, "title": l.title, "effect": l.effect,
            "state": describe(l.setup()),
            "teach": {**l.teach, "runs": _runs(l, l.teach["example"])},
            "predict": strip(l.predict, "answer"),
            "contrast": strip(l.contrast, "answer", "explain"),
            "worked": strip(l.worked, "answer"),
            "faded": [{"template": f["template"]} for f in l.faded]}


def _runs(l, *lines):
    return probe_runs(l.setup, *lines)


@app.get("/api/lesson/{lid}")
def get_lesson(lid: str):
    return _public(lesson(lid))


@app.post("/api/lesson/{lid}/check")
def check_lesson(lid: str, body: Check):
    l = lesson(lid)
    st = body.stage
    if st == "predict":
        p = l.predict
        return {"ok": body.choice == p["answer"], "answer": p["answer"],
                "runs": _runs(l, p["line"])}
    if st == "contrast":
        c = l.contrast
        return {"ok": body.choice == c["answer"], "answer": c["answer"],
                "explain": c["explain"], "runs": _runs(l, c["a"], c["b"])}
    if st == "worked":
        w = l.worked
        return {"ok": body.choice == w["answer"], "answer": w["answer"],
                "runs": _runs(l, w["line"])}
    m = re.fullmatch(r"faded(\d+)", st)
    if m and int(m.group(1)) < len(l.faded):
        f = l.faded[int(m.group(1))]
        res = check_blanks(body.blanks, f["answers"])
        full = f["template"]
        for a in f["answers"]:
            full = full.replace("___", a[0] if a[0] != "<name>" else "result", 1)
        return {"ok": len(res) == len(f["answers"]) and all(res), "blanks": res, "line": full}
    raise HTTPException(400, "bad stage")


@app.post("/api/lesson/{lid}/done")
def lesson_done(lid: str):
    sched.lesson_done(lesson(lid).id)
    return {"ok": True}


# --------------------------------------------------------------- explain
def exp(k: int):
    if not 0 <= k < len(EXPLAINS):
        raise HTTPException(404, "no such item")
    return EXPLAINS[k]


@app.get("/api/explain/{k}")
def get_explain(k: int):
    x = exp(k)
    return {"index": k, "total": len(EXPLAINS), "id": x.id, "domain": x.domain,
            "line": x.line, "question": x.question, "options": x.options,
            "state": describe(x.setup())}


@app.post("/api/explain/{k}/effect")
def explain_effect(k: int, body: Effect):
    x = exp(k)
    return {"ok": body.effect == x.effect, "answer": x.effect}


@app.post("/api/explain/{k}/slots")
def explain_slots(k: int, body: Slots):
    return check_slots(exp(k), body.slots)


@app.get("/api/explain/{k}/reveal")
def explain_reveal(k: int):
    return {s: v[0] for s, v in exp(k).grammar.items()}


class Pick(BaseModel):
    choice: int


@app.post("/api/explain/{k}/answer")
def explain_answer(k: int, body: Pick):
    x = exp(k)
    ok = body.choice == x.answer
    res = {"ok": ok, "answer": x.answer}
    if ok:
        res.update(why=x.why, runs=probe_runs(x.setup, x.line))
    return res


class Done(BaseModel):
    misses: int = 0


@app.post("/api/explain/{k}/done")
def explain_done(k: int, body: Done):
    sched.explain_done(exp(k).id, body.misses)
    return {"ok": True}
