"""Whatever a step asks about must be on screen: every name a shown line uses has to be
one of the starting values (or built in, or assigned by the line itself)."""
import ast
import builtins
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drills import DRILLS
from explain import EXPLAINS
from lessons import LESSONS

OK_NAMES = set(dir(builtins)) | {"pd", "np"}


def _unseen(line, shown):
    tree = ast.parse(line)
    assigned = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Store)}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Load)}
    return sorted(used - assigned - set(shown) - OK_NAMES)


def _filled(template, answers):
    for a in answers:
        template = template.replace("___", "result" if a[0] == "<name>" else a[0], 1)
    return template


def test_lesson_lines_only_use_values_that_are_shown():
    for l in LESSONS:
        shown = l.setup().keys()
        lines = [l.teach["example"], l.worked["line"], l.contrast["a"], l.contrast["b"],
                 l.predict["line"]] + [_filled(f["template"], f["answers"]) for f in l.faded]
        for line in lines:
            assert not _unseen(line, shown), f"lesson {l.id}: {line!r} uses unseen {_unseen(line, shown)}"


def test_explain_and_drill_lines_only_use_shown_values():
    for x in EXPLAINS:
        assert not _unseen(x.line, x.setup().keys()), x.id
    for d in DRILLS:
        assert not _unseen(d.reference_line, d.setup().keys()), d.id


def test_every_lesson_step_goes_through_scene():
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
    body = html[html.index("function renderStage"):html.index("function opts")]
    assert "L.state" not in body            # steps never draw state themselves
    assert "function scene(" in html and html.count("L.state.map(sl)") == 1
    assert len(re.findall(r"b\.innerHTML=", body)) == 5   # teach, predict, contrast, worked, faded


def test_starting_values_are_shown_as_code():
    from engine import describe
    from lessons import LESSONS
    for l in LESSONS:
        for v in describe(l.setup()):
            first = v["line"].splitlines()[0]
            assert not re.search(r"^\w+:\s*\w+\s*=", first), first     # no "name: type = value"
    lines = {v["name"]: v["line"] for v in describe({"nums": [3, 1, 2]})}
    assert lines["nums"] == "nums = [3, 1, 2]"
