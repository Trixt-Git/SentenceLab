"""Guards against text a learner cannot understand: internal jargon on screen, and
screens that use ideas no lesson has taught yet."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drills import DRILLS
from explain import EXPLAINS
from lessons import LESSONS
from scheduler import Scheduler

# Words that are internal labels, not things a learner has been taught.
JARGON = re.compile(r"\b(rebind\w*|mutat\w*|emit\w*|landing|physical effect|grammatical|slots?)\b", re.I)


def _lesson_strings(l):
    out = [l.title, *l.teach["points"], l.teach["rule"]]
    for part in (l.worked, l.contrast, l.predict):
        out += [part.get(k, "") for k in ("why", "question", "explain")]
        out += list(part.get("options", []))
    out += list(l.worked["slots"].keys())
    return out


def test_no_internal_jargon_in_learner_text():
    texts = []
    for l in LESSONS:
        texts += _lesson_strings(l)
    texts += [d.intent for d in DRILLS]
    for x in EXPLAINS:
        texts += [x.question, x.why, *x.options]
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
    html = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
    texts.append(re.sub(r"<[^>]+>", " ", html))
    bad = [(m.group(0), t[:60]) for t in texts for m in [JARGON.search(t)] if m]
    assert not bad, bad


def test_terms_are_taught_before_the_first_drill(tmp_path):
    s = Scheduler(DRILLS, LESSONS, EXPLAINS, tmp_path / "h.csv")
    order = []
    for _ in range(6):
        n = s.next()
        if n["kind"] == "drill":
            break
        order.append(n["lesson"]); s.lesson_done(n["lesson"])
    # Step 1 asks "what happens to the result" and step 2 names four parts.
    assert order[:2] == ["sentence", "saved"]


def test_drill_instructions_are_plain_sentences():
    for d in DRILLS:
        assert d.intent.endswith("."), d.id
        assert len(d.intent.split()) <= 30, d.id
