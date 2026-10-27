# Decisions

Where ARCHITECTURE.md is silent, the simplest option was chosen and is recorded here with one line of why.

## Phase 1 — Python in the browser

### Scope and dependencies

- **Only the packages Phase 1 uses are installed** (react, react-dom, vite, typescript, vitest, @vitejs/plugin-react, React types, pyodide). ts-fsrs, dexie, @dnd-kit, CodeMirror, comlink and Playwright are pinned when the phase that needs them starts, so the lockfile holds no unused code.
- **Versions the doc leaves open are pinned exactly to what the registry served on 26 Oct 2026:** typescript 7.0.2, vitest 5.0.5, @vitejs/plugin-react 6.1.2, @types/react and @types/react-dom 19.3.0. Pinned versions from section 10 are exact: vite 8.3.5, react and react-dom 19.3.1.
- **The `pyodide` npm package (314.0.7, dev only) runs the Node-side test script.** The app itself loads Pyodide from jsDelivr at v314.0.7, as section 8 says.
- **Comlink is not used.** Plain `postMessage` is simpler and the typed protocol is only three requests.

### Worker and client

- **`python/checker.py` is imported with Vite's `?raw` and written into Pyodide's filesystem.** One copy of the checker, byte for byte, with no build step that could alter it.
- **A small Python glue function takes and returns JSON strings.** No Python object crosses into JS, and `checker.py` stays untouched.
- **`check` and `validate` messages also carry an optional `options`.** `check_all` and `validate` in `checker.py` accept it, and section 8's message list left it out.
- **Every request has an `id`, and the worker reports `loading` then `running`.** The 5-second timer starts at `running`, so package loading never counts against it (section 8).
- **One request runs at a time.** Each timer then measures exactly one request, and a restart cannot lose track of another request's answer.
- **A timed-out `check` resolves with a normal result (`timedOut: true`, message "Your line ran too long and was stopped.").** The review screen can show it like any other feedback; `validate` and `parts` timeouts reject with `PythonTimeoutError`.
- **`validate` gets a 15-second limit.** The doc gives 5 seconds per check and is silent on Validate, which also runs every trap. In Pyodide it takes about 100 ms per seed note once packages are loaded.
- **Package loading scans each snippet on its own.** A learner line with a syntax error would otherwise hide the setup's `import pandas` from the scanner.
- **Python errors reach the UI as their last traceback line** (for example `ValueError: parts() takes exactly one statement`), matching the "real error text" rule in section 8.
- **`client.restart()` exists for the start of every session** (section 8 restarts the worker then); Phase 3 calls it.

### Harness

- **`src/app/Harness.tsx` is a developer page, not a study screen.** It lets Phase 1 be exercised by hand (check, validate, parts, an endless line, restart). It shows nothing of the real Review screen, which is Phase 3.

### Tests and environment

- **`test_checker.py` and `test_seed.py` are plain scripts, not pytest files** (they read their paths from `sys.argv`). They run unchanged: with `python -I` natively, and with `runpy` inside Pyodide via `npm run test:pyodide`.
- **Native environment** (in an ignored `.venv`): Python 3.13.1, numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1. The doc tested pandas 3.0.5, so pandas differs by a minor version; results are the same.
- **Differences between normal Python and Pyodide 314.0.7: none.** Both print `mismatches: 0 of 71` and `notes: 21 problems: 0`. The two judgement cases (C16, IMPORT) are accepted in both.
- **Package load times measured in the browser worker (cold):** pandas about 9 s on the first pandas card, scikit-learn about 13 s on the first scikit-learn card, both well inside the 60-second loading limit.

### Repo state

- **The pre-existing `ARCHITECTURE.md`, `python/`, `content/` and `docs/` are untracked in git** (only the README is committed). Nothing was committed or pushed in this phase.
- **Work stays on `main`**, as chosen when the branch question was asked.

### Phase 1 re-run after the design review (decks v2, checker with `style`)

- **Counts confirmed in both places:** `mismatches: 0 of 83` and `patterns: 21 instances: 84 problems: 0`, in normal Python 3.13 and in Pyodide 314.0.7. No differences to log.
- **`scripts/pyodide-tests.mjs` now passes on zero mismatches and zero problems instead of fixed totals.** Agreed: the totals grow as cases are added. The script still fails if a summary line is missing, so a suite that silently stops running can't pass.
- **`CheckResult` gained `style?: string[]`.** A `stage: "note"` result (a setup that fails) carries no `blame`, no `effects` and no `style`, and the harness shows it as "Not a learner miss".
- **Native environment is still pandas 3.1.0** (the doc tested 3.0.5); results are identical.

## Pilot

### Help after a miss (section 13 table, followed as written)

- **Routing lives in `src/pilot/routing.ts`, one case per row of the pilot table,** each with a Vitest case, so Phase 5 can swap rows for L2 and L3 in one place.
- **`?` acts as "stuck" only on an empty line, and the Stuck button always works.** A `?` can legitimately appear inside a string, and typing it must not end the card.
- **Stuck is allowed while the effect gate is still up** (stuck reason 3 is "I'm not sure what should change"). After stuck 1 or stuck 3 the learner types at once; the gate isn't asked a second time on a card already counted as a miss.
- **L4 reuses the effect pick already made on the card** and asks for one only if none was made. Asking twice on one card is a ritual with no new information.
- **A fix-it attempt is a normal L5 attempt with `first: false`.** The first miss has already been scheduled and its retry queued.
- **The retry is the same instance and format with the next wording; once answered, right or wrong, the reference is shown and the card ends.** The doc says the card ends on an unaided attempt; looping until right would turn it into copying.
- **L4 is judged by running the filled line through the checker**, not by comparing text, so every correct spelling of the missing part is accepted.
- **Blanking is done in `src/python/glue.py` with `ast` positions.** A part the line doesn't have (a bare call's landing, a lookup's bracket verb, `len(x)`'s subject) returns null and the next part in the rotation is used. The landing blank swallows the `=` (`____ df.dropna(...)`), as the table's example shows.
- **A line that timed out skips the bench.** The bench would run the same endless line.

### Bench

- **`bench()` is added to the end of `python/checker.py`, as section 8 says. Nothing above it changed.** If `checker.py` is ever replaced wholesale, `bench()` and its helpers (everything under the "the bench" heading) must be carried over; `python/tests/test_bench.py` fails if they are missing.
- **`test_bench.py` also covers `blank()` and `ref_effects()` from `src/python/glue.py`,** and runs in both places (`npm run test:pyodide` now runs it too).
- **Floats lose their `.0` on the bench** (`10.0` shows as `10`) because previews travel as JSON. Whole floats and ints look the same; the type shows only through the column dtype, which the bench doesn't draw yet.
- **Arrows are drawn as a `→` between a name tag and its box,** not as SVG lines. Shared objects share one box, so aliasing still shows; real arrows come with the animation in Phase 4.

### Scheduling and queue

- **Fixed gaps follow the doc: 1, 3, 7, 14, 30 days; a miss goes back to 1 day.** A new pattern has no gap yet, so its first correct attempt lands on the 1-day gap.
- **Due reviews are taken oldest-due first.** Lowest predicted recall needs FSRS, which arrives in Phase 2.
- **The 4am day boundary is applied** (cheap, and it keeps day arithmetic identical to what Phase 2 needs).
- **Not in the pilot:** contrast pairs, the session floor, the daily review cap, FSRS ratings. They are Phase 2 items; the session size (20) and new patterns per day (5, counted across sessions) are in.
- **`requires` is checked when a session is built,** so a pattern unlocked mid-session appears in the next one.
- **The Dexie `schedule` store is indexed by `dueDay`** instead of `fsrsCard.due`, and `fsrsLog` is left out. Phase 2 adds both with a new `version(n).upgrade()` step; the attempts log carries over untouched.
- **`attempts` rows carry two extra fields:** `first` (this was the first L5 attempt of the review, the only one scheduling sees) and `sure`. `level` is `L5`, `L4` or `prompt` (the effect prompt).

### Fading and Explain

- **Fluent means 3 correct first attempts in a row; the gate is off after 3 correct picks in a row.** They are tracked separately, as section 5 words them.
- **Explain reveals the bench only,** because the sentence diagram is deferred to Phase 4.
- **A correct pick on a correct line is graded against the learner's own effects,** as section 5 says, so `df.dropna(inplace=True)` is judged as "mutates".
- **Sure or unsure is logged and the rule is shown first after a sure-but-wrong answer.** The extra L5 retry later in the session is not built; the miss already schedules a retry.
- **"Show reference" is offered after a miss and counts as one** (it already is one); it is never offered before an answer.

### Cold challenge

- **Cold cards use the notebook format.** Cold eligibility (2 correct first attempts) is the same threshold that unlocks notebook-style cards, and the notebook cell is closest to real work.
- **Up to 4 cold instances from 4 different patterns; if fewer patterns are eligible it asks fewer.** Each cold instance is retired once answered.
- **A challenge is offered when the last finished one was 7 or more days ago,** and the clock starts when one is finished, not started. Cold attempts are excluded from the session measures and feed only the cold score.
- **The wrong-answer message is still shown after a cold card** (guardrail: feedback is causal) but never a bench, help, retry or reference.

### UI and app

- **Python restarts at the start of every session and every cold challenge,** as section 8 says, so the first card of each session waits for Pyodide ("Loading Python…" shows).
- **The Phase 1 harness moved to `#harness`;** the app opens on Home.
- **Light and dark follow the system setting; there is no manual toggle yet** (Phase 7 hand-check).
- **CodeMirror has syntax colour, undo and nothing else.** No autocomplete, no bracket closing, no snippets. Packages are pinned exactly: `@codemirror/state` 6.7.6, `view` 6.43.15, `language` 6.13.1, `commands` 6.11.1 (the doc pins only `lang-python`, 6.2.1).
- **The inbox is a list on the capture page,** read-only, because Browse is deferred.
- **No Playwright test in the pilot;** the end-to-end session is covered by the engine's Vitest cases and by a hand-driven run in the browser. Playwright is in Phase 7.
