"""Local drill server: `uvicorn app:app` from this directory."""
import csv
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from drills import DRILLS
from engine import check_slots, describe, run_line

HERE = Path(__file__).parent
HISTORY = HERE / "history.csv"
app = FastAPI()
attempts: dict[str, int] = {}


def get(i: int):
    if not 0 <= i < len(DRILLS):
        raise HTTPException(404, "no such drill")
    return DRILLS[i]


class Effect(BaseModel):
    effect: str


class Slots(BaseModel):
    slots: dict


class Code(BaseModel):
    code: str


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/drill/{i}")
def drill(i: int):
    d = get(i)
    return {"index": i, "total": len(DRILLS), "id": d.id, "domain": d.domain,
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
    attempts[d.id] = attempts.get(d.id, 0) + 1
    if res["passed"]:
        res["reference_line"] = d.reference_line
        new = not HISTORY.exists()
        with HISTORY.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "drill_id", "passed", "attempts"])
            w.writerow([int(time.time()), d.id, True, attempts.pop(d.id)])
    return res
