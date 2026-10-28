import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drills import DRILLS
from engine import check_blanks, run_line
from lessons import LESSONS
from scheduler import Scheduler

IDS = {d.id for d in DRILLS}


def test_lessons_reference_real_drills_and_effects():
    for l in LESSONS:
        assert l.before in IDS
        assert 0 <= l.predict["answer"] < len(l.predict["options"])
        assert 0 <= l.contrast["answer"] < len(l.contrast["options"])
        assert 0 <= l.worked["answer"] < len(l.worked["options"])


def test_lesson_lines_run_and_faded_reconstruct():
    from app import _runs
    for l in LESSONS:
        lines = [l.predict["line"], l.contrast["a"], l.contrast["b"], l.worked["line"]]
        for r in _runs(l, *lines):
            assert not r["error"], (l.id, r)
        for f in l.faded:
            line = f["template"]
            for a in f["answers"]:
                line = line.replace("___", "result" if a[0] == "<name>" else a[0], 1)
            assert not _runs(l, line)[0]["error"], (l.id, line)


def test_blank_checker():
    assert check_blanks(["foo", "sorted"], [["<name>"], ["sorted"]]) == [True, True]
    assert check_blanks(["1x"], [["<name>"]]) == [False]


def _drill(i):
    return DRILLS[i]


def test_blocked_phase_then_interleave(tmp_path):
    from lessons import LESSONS as LS
    s = Scheduler(DRILLS, LS, tmp_path / "h.csv")
    seen = []
    for _ in range(40):
        n = s.next()
        if n["kind"] == "lesson":
            s.lesson_done(n["lesson"])
            continue
        if n["phase"] == "interleaved":
            break
        seen.append(n["id"])
        s.record(next(d for d in DRILLS if d.id == n["id"]), True, True)
    assert seen == [d.id for d in DRILLS]
    a = s.next()
    b = s.next()
    assert a["phase"] == b["phase"] == "interleaved"
    assert a["id"] != b["id"] or len(DRILLS) == 1


def test_confident_error_comes_back_first(tmp_path):
    s = Scheduler(DRILLS, LESSONS, tmp_path / "h.csv")
    for l in LESSONS:
        s.lesson_done(l.id)
    for d in DRILLS:
        s.record(d, True, True)
    target = DRILLS[3]
    s.record(target, False, True)
    s.last_effect = None
    n = s.next()
    assert n["id"] == target.id and n["review"] is True


def test_mastery_and_history_reload(tmp_path):
    p = tmp_path / "h.csv"
    s = Scheduler(DRILLS, LESSONS, p)
    for d in [d for d in DRILLS if d.effect == "mutate"]:
        s.record(d, True, True)
    assert s.mastered("mutate")
    s2 = Scheduler(DRILLS, LESSONS, p)
    assert s2.mastered("mutate") and not s2.mastered("emit")
