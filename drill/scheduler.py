"""Chooses what to show next and records progress in history.csv.

Phase 1 (blocked): per effect, lesson then its drills in order.
Phase 2 (interleaved): confident errors first, then recent failures, then the
least-practised drills, avoiding the same effect twice in a row.
"""
import csv
import time
from pathlib import Path

HEADER = ["timestamp", "kind", "id", "passed", "attempt", "confident"]
MASTERY_RUN = 3


class Scheduler:
    def __init__(self, drills, lessons, explains, path: Path):
        self.drills, self.lessons, self.explains, self.path = drills, lessons, explains, path
        self.estats = {x.id: dict(passes=0, misses=0, last_t=0.0) for x in explains}
        self.picks = 0
        self.lesson_before = {l.before: l for l in lessons}
        self.stats = {d.id: dict(passes=0, last_ok=None, conf_wrong=False, last_t=0)
                      for d in drills}
        self.firsts = {}          # effect -> list of first-attempt outcomes
        self.seen = set()
        self.attempt_no = {}
        self.last_effect = None
        self._load()

    # --- persistence
    def _load(self):
        if not self.path.exists():
            return
        with self.path.open(newline="") as f:
            for r in csv.DictReader(f):
                self._apply(r["kind"], r["id"], r["passed"] == "True",
                            int(r["attempt"] or 1), r["confident"] == "True",
                            float(r["timestamp"]))

    def _log(self, kind, id_, passed, attempt, confident):
        new = not self.path.exists()
        with self.path.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(HEADER)
            w.writerow([time.time(), kind, id_, passed, attempt, confident])

    def _apply(self, kind, id_, passed, attempt, confident, t):
        if kind == "lesson":
            self.seen.add(id_)
            return
        if kind == "explain":
            e = self.estats.get(id_)
            if e is not None:
                e["passes"] += 1
                e["misses"] = attempt - 1
                e["last_t"] = t
            return
        s = self.stats.get(id_)
        if s is None:
            return
        s["last_t"], s["last_ok"] = t, passed
        s["conf_wrong"] = (not passed) and confident
        if passed:
            s["passes"] += 1
        if attempt == 1:
            eff = next(d.effect for d in self.drills if d.id == id_)
            self.firsts.setdefault(eff, []).append(passed)

    # --- events
    def lesson_done(self, lesson_id):
        self.seen.add(lesson_id)
        self._log("lesson", lesson_id, True, 1, False)

    def explain_done(self, id_, misses):
        self._apply("explain", id_, True, misses + 1, False, time.time())
        self._log("explain", id_, True, misses + 1, False)

    def record(self, drill, passed, confident):
        n = self.attempt_no[drill.id] = self.attempt_no.get(drill.id, 0) + 1
        self._apply("drill", drill.id, passed, n, confident, time.time())
        self._log("drill", drill.id, passed, n, confident)
        if passed:
            self.attempt_no.pop(drill.id)
        return n

    def failures(self, drill_id):
        return self.attempt_no.get(drill_id, 0)

    # --- selection
    def mastered(self, effect):
        run = self.firsts.get(effect, [])[-MASTERY_RUN:]
        return len(run) == MASTERY_RUN and all(run)

    def _explain(self):
        lead = self.lesson_before.get("explain")
        if lead and lead.id not in self.seen:
            return {"kind": "lesson", "lesson": lead.id, "phase": "explain"}
        pick = min(self.explains, key=lambda x: (self.estats[x.id]["passes"] > 0,
                                                 -self.estats[x.id]["misses"],
                                                 self.estats[x.id]["last_t"]))
        return {"kind": "explain", "id": pick.id, "phase": "explain"}

    def next(self, kind=""):
        if kind == "explain":
            return self._explain()
        for d in self.drills:
            lesson = self.lesson_before.get(d.id)
            if lesson and lesson.id not in self.seen:
                return {"kind": "lesson", "lesson": lesson.id, "phase": "blocked"}
            if self.stats[d.id]["passes"] == 0:
                return self._drill(d, "blocked")

        def priority(d):
            s = self.stats[d.id]
            if s["conf_wrong"]:
                return 3.0
            if s["last_ok"] is False:
                return 2.0
            return 1.0 / (1 + s["passes"])
        self.picks += 1
        if self.picks % 4 == 0:
            return self._explain()
        ranked = sorted(self.drills, key=lambda d: (-priority(d), self.stats[d.id]["last_t"]))
        pick = next((d for d in ranked if d.effect != self.last_effect), ranked[0])
        return self._drill(pick, "interleaved")

    def _drill(self, d, phase):
        self.last_effect = d.effect
        return {"kind": "drill", "id": d.id, "phase": phase,
                "mastered": self.mastered(d.effect),
                "review": self.stats[d.id]["conf_wrong"]}
