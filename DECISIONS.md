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
