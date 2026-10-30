# SentenceLab drill

Single-line production practice: write one line of Python, see what it did, say what
happened to its answer, then name the four parts of your own line.

    pip install -r requirements.txt
    uvicorn app:app

- `drills.py` drill definitions; `lessons.py` short lessons shown before drills
- `engine.py` AST + namespace-diff grading; `scheduler.py` blocked-then-interleaved
  sequencing, confident-error review, per-effect mastery (3 first-try passes)
- Progress is appended to `history.csv` (override with `DRILL_HISTORY`)
- Keys: 1/2/3 effect, Enter next, Shift+Enter run as "unsure", Ctrl+H hint, M mode, E explain-a-line
- Learner code runs through `exec` in the server process: local use only.
