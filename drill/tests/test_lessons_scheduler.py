import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drills import DRILLS
from engine import check_blanks, run_line
from explain import EXPLAINS
from lessons import LESSONS
from scheduler import Scheduler

IDS = {d.id for d in DRILLS}


def test_lessons_reference_real_drills_and_effects():
    for l in LESSONS:
        assert l.before in IDS | {"explain"}
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
    s = Scheduler(DRILLS, LS, EXPLAINS, tmp_path / "h.csv")
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
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, tmp_path / "h.csv")
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
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, p)
    for d in [d for d in DRILLS if d.effect == "mutate"]:
        s.record(d, True, True)
    assert s.mastered("mutate")
    s2 = Scheduler(DRILLS, LESSONS, EXPLAINS, p)
    assert s2.mastered("mutate") and not s2.mastered("emit")


def test_diff_detail_shapes():
    from diffdetail import MISSING, detail
    import numpy as np
    import pandas as pd
    d = detail([72, 88, 91], [72, 88, 91, 95])
    assert ["95", "add"] in d["after"] and all(op == "eq" for _, op in d["before"])
    d = detail({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
    assert ["'b': 2", "del"] in d["before"] and ["'c': 4", "add"] in d["after"]
    d = detail(np.array([1.0, 2.0, np.nan]), np.array([1.0, 5.0, np.nan]))
    assert sum(op == "add" for _, op in d["after"]) == 1
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    t = detail(df, df.dropna())
    assert [r["status"] for r in t["rows"]] == ["eq", "del", "eq"]
    assert detail(MISSING, df)["rows"][0]["status"] == "add"
    assert detail(1, 2) is None and detail([1], (1,)) is None
    long_ = detail(list(range(50)), list(range(49)) + [99])
    assert len(long_["before"]) < 20


def test_diff_detail_series_array_string():
    from diffdetail import detail
    import numpy as np
    import pandas as pd
    t = detail(pd.Series([1, 2, 3], name="s"), pd.Series([1.5, 2, 3], name="s"))
    assert t["kind"] == "table" and t["caption"] == "dtype int64 → float64"
    t = detail(pd.Series([1, 2, 3]), pd.Series([1, 3]))
    assert [r["status"] for r in t["rows"]].count("del") == 1
    g = detail(np.array([[1, 2], [3, 4]]), np.array([[1, 9], [3, 4]]))
    assert g["rows"][0]["cells"][1][:2] == ["9", "add"] and g["rows"][0]["cells"][1][2] == "was 2"
    assert detail(np.zeros((2, 2)), np.zeros((3, 2)))["caption"] == "shape (2, 2) → (3, 2)"
    big = detail(np.zeros((20, 20)), np.ones((20, 20)))
    assert len(big["rows"]) == 8 and big["hidden_changes"] == 400 - 64
    assert detail([[1, 2], [3, 4]], [[1, 2], [3, 5]])["kind"] == "table"
    s = detail("the quick brown fox", "the quick red fox jumps")
    assert s["caption"] == "2 words changed"
    assert ["red", "add"] in s["after"] or any(t[1] == "add" and "red" in t[0] for t in s["after"])
    ws = detail("a  b", "a b")
    assert ws["caption"] == "whitespace changed" and "··" in "".join(t[0] for t in ws["before"])
    long = detail("x " * 40 + "cat " + "y " * 40, "x " * 40 + "dog " + "y " * 40)
    assert len("".join(t[0] for t in long["before"])) < 60
    f = detail([0.1234567, 1.0], [0.1234568, 1.0])
    assert f["before"][1][2] == "0.1234567"


def test_explain_items_consistent():
    from engine import check_slots, probe_runs
    for x in EXPLAINS:
        assert 0 <= x.answer < len(x.options)
        assert all(check_slots(x, {k: v[0] for k, v in x.grammar.items()}).values())
        assert not probe_runs(x.setup, x.line)[0]["error"], x.id


def test_explain_scheduling_and_history(tmp_path):
    p = tmp_path / "h.csv"
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, p)
    s.lesson_done("read")
    first = s.next("explain")
    assert first["kind"] == "explain"
    s.explain_done(first["id"], 2)
    assert s.next("explain")["id"] != first["id"]
    assert Scheduler(DRILLS, LESSONS, EXPLAINS, p).estats[first["id"]]["misses"] == 2


def test_lesson_before_every_effect_group_and_domain(tmp_path):
    ids = {l.before for l in LESSONS}
    assert {"sk-fit", "sk-predict", "sk-transform", "explain"} <= ids
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, tmp_path / "h.csv")
    n = s.next("explain")
    assert n["kind"] == "lesson" and n["lesson"] == "read"
    s.lesson_done("read")
    assert s.next("explain")["kind"] == "explain"


def test_every_drill_with_new_concept_has_lesson_first(tmp_path):
    """Walking the blocked phase, each sklearn drill is preceded by its lesson."""
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, tmp_path / "h.csv")
    order = []
    for _ in range(60):
        n = s.next()
        if n["phase"] == "interleaved":
            break
        if n["kind"] == "lesson":
            order.append("L:" + n["lesson"]); s.lesson_done(n["lesson"])
        else:
            order.append(n["id"]); s.record(next(d for d in DRILLS if d.id == n["id"]), True, True)
    for drill_id, lesson_id in [("sk-fit", "sk-fit"), ("sk-predict", "sk-predict"),
                                ("sk-transform", "sk-transform")]:
        assert order.index("L:" + lesson_id) == order.index(drill_id) - 1


def test_every_lesson_teaches_before_asking():
    from app import _public
    for l in LESSONS:
        t = _public(l)["teach"]
        assert len(t["points"]) >= 2 and t["rule"] and not t["runs"][0]["error"], l.id
        assert "answer" not in str(t)
