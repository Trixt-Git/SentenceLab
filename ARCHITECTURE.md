# Sentence Lab — Architecture

Oct 26, 2026 · @Wil

## 1. Purpose

Sentence Lab is a browser study app that trains one skill: turning a plain-English intent into a single working line of Python. Lines come back on a spaced schedule, just before they'd be forgotten. Every card makes the learner type a line, and every line is actually run.

**The problem it solves.** The learner (Wil) can read and understand Python, including new ML concepts, but freezes when he has to produce a line from a blank cell. That is a production gap, not a knowledge gap. Flashcards that show code and ask "do you recognise this?" train recognition, which he already has. This app trains production.

**Working diagnosis.** Writing one line hides five small decisions. The freeze happens because they were never practised separately, so all five land at once:

1. **Intent** — say in English what the line must do.
2. **Effect** — decide what the line changes: a name, an object, the outside world, or the flow of execution.
3. **Parts** — choose the subject (who acts), the verb (the method, function or operator), the details (arguments), and where the result goes.
4. **Assemble** — put the parts in Python's word order, building nested pieces inside-out.
5. **Check** — predict what changed and what came back, then confirm.

The app asks for the whole line first, and when it fails, gives help on the one decision that went wrong.

### Two goals, in order

| Goal | What it means | Where it lives |
| --- | --- | --- |
| 1. Stop freezing (now) | Turn an English intent into one correct line without stalling. The example lines come from real pandas and scikit-learn work, so the learner sees job skills, but only the sentence skill is tested. | Everything in this doc |
| 2. Job-ready (later) | The full analyst and ML skill set: loading and inspecting data, dates, text, reshaping, charts, pipelines, metrics, debugging, multi-line analyses. | A placeholder in section 4; not built in this version |

The two goals are never mixed. Goal 2 content is not added to Goal 1 decks as tested material, so Goal 1 stays small enough to finish.

### Goal 1 finish line

Goal 1 is done when the app's own numbers and Wil's notebook experience agree. The thresholds below are defaults that Wil can change in Settings.

- **First-try success on new lines:** at least 80% of never-seen notes answered correctly on the first L5 attempt, across 5 separate days.
- **Unaided recall:** at least 90% of due notes answered correctly on the first L5 attempt over the last 2 weeks.
- **Start time:** median time from card shown to first keystroke is falling, shown in the session summary (section 6).
- **Notebook check (Wil judges):** freezing on a single line in real work has become rare.

When all four hold, Goal 2 starts as a separate piece of work.

## 2. Locked decisions

These were decided by Wil on 26 Oct 2026 and are not open for the builder to change.

| Decision | Choice | Why |
| --- | --- | --- |
| Platform | Browser app, visual first | Wil wants to see sentence parts and state changes, not read terminal text. |
| Who builds | Antigravity builds from this doc; Wil only studies | Keeps study time on the skill, not on the tool. |
| Goals | Goal 1 (stop freezing) first and alone; Goal 2 (job-ready) later and separate | Mixing them overloads the learner and the build. |
| What it is | A sentence trainer that uses spaced repetition. It is not an Anki replacement. | Spaced repetition is the one idea borrowed from Anki; nothing else (ratings, decks to manage, leech rules) is copied. |
| How answers are judged | The typed line runs as real Python (Pyodide, in a Web Worker) and its effects are compared with the reference line's effects | Accepts every correct spelling the checker can verify, and makes feedback causal. |
| Grading | Fully automatic. The learner never rates a card. | Removes a decision from every card and stops self-grading drift. |
| Motivation | No points, XP, streaks, targets, badges or leaderboards. An end-of-session summary is shown as information only. | Expected rewards can crowd out interest; informational feedback on competence supports it. |

## 3. Learning model: the anatomy of a Python sentence

Every card in the app uses the same grammar, the same four part names and the same four colours, so the learner builds one mental template that works for every line.

&#91;embedded content: sentence anatomy · 4 parts, one nested sentence\]

The same four parts appear in every line; a nested sentence is drawn as an indented row under the chip it feeds.

### The four parts

| Part | Question it answers | Colour token | Examples |
| --- | --- | --- | --- |
| Subject | Who is acting, or being acted on? | blue | `df` in `df.dropna(...)`, `scores` in `scores.append(7)`, `a` in `a + b` |
| Verb | What action? | orange | a method (`.dropna`), a function (`len`, `sorted`), an operator (`+`, `>`), a lookup (`[...]`) |
| Details | With what, how, how much? | green | arguments and keywords: `subset=["price"]`, `test_size=0.2`, the key in `ages["Ana"]` |
| Landing | Where does the result go? | purple | bound to a name (`df = ...`), stored in a slot (`d[k] = ...`), sent out (`return`, `print`), or dropped (a bare call) |

A function call with no object in front (`len(orders)`) has no subject: the verb acts on its details. Colour must never be the only signal; every chip also shows its part name.

### Sentences inside sentences

A detail can itself be a whole sentence. In `big = df[df["qty"] > 10]`, the inner sentence `df["qty"] > 10` produces a True/False mask, and that result becomes the detail of the outer lookup `df[...]`. The rule the app teaches is: **read outside-in, build inside-out.** The diagram view (section 6) shows each nested sentence as an indented clause the learner can expand or collapse.

### The four effects

Every line does one or more of these. Choosing the effects before writing is the step most often skipped, and it is where the classic traps live.

| Effect | What changes | Typical verbs | Trap it prevents |
| --- | --- | --- | --- |
| Rebinds a name | A name now points at a different object | `=`, `+=` on numbers and strings | Thinking `df.dropna()` changed `df` without `df = ...` |
| Mutates an object | An existing object's contents change; every name pointing at it sees the change | `.append`, `.sort`, `d[k] = v`, `model.fit` | Writing `x = lst.sort()` and getting `None` |
| Sends out | Something leaves the line: printed text or a returned value | `print`, `return` | Printing when the caller needed a returned value |
| Moves the needle | Which line runs next changes | `if`, `for`, `while`, `break` | Expecting a loop to stop the instant its condition turns false |

Version 1 cards use the first three effects. "Moves the needle" arrives with multi-line phrases in version 2.

**The pandas exception.** In pandas 3, Copy-on-Write is always on: a column or subset taken from a DataFrame behaves as its own copy. So "every name pointing at it sees the change" holds for lists, dicts and models, but not for pieces of a DataFrame. Two traps follow and both are seed cards: `df['price'].fillna(0, inplace=True)` changes nothing, and `df['a'][0] = 1` changes nothing. The working form is always to land the result: `df['price'] = df['price'].fillna(0)`. `inplace=True` is also being phased out of pandas, so no card teaches it as the right answer.

### What each verb gives back

The learner must know, for every verb, which of three things comes back. Each note records it, and the feedback names it.

- **A new object** — the original is untouched (`sorted(x)`, most pandas methods, `a + b`).
- **None, after mutating in place** — (`list.sort`, `list.append`, `dict.update`).
- **The same object, after mutating it** — (`model.fit` returns the model itself).

## 4. Scope

This build is Goal 1 only: single-line sentences. Goal 2 is listed here so that nothing in this build blocks it, not so that any of it gets built now.

| Version | Serves | Contents |
| --- | --- | --- |
| v1 (this build) | Goal 1 | Single lines; L5-first ladder with fallback help; automatic spaced repetition; real-Python checking; sentence diagram and bench; three seed decks used as exposure (core Python, pandas, scikit-learn); add-your-own notes; session summary; JSON export and import |
| v2 (later) | Bridge from Goal 1 to 2. Starts only when the Goal 1 finish line (section 1) holds | 2–4 line phrases built from common plans (accumulate in a loop, filter into a new list, clean → split → fit → predict); the "moves the needle" effect; line-ordering and missing-line cards |
| v3+ (later) | Goal 2 | The job-ready curriculum below |

### Goal 2 placeholder (not in this build)

The full skill map, lesson plan and real-dataset capstones are in the audit report "Sentence Lab design audit" (26 Oct 2026). Parked topics: loading and inspecting data; dates and `.str`; `agg`, `transform`, `merge`, `concat`, reshaping and window functions; charts; numpy masks, `axis` and broadcasting; preprocessing, `Pipeline`, cross-validation and metrics; reading tracebacks and docs; debugging; whole analyses on real datasets.

### Rules that keep v2 and v3 possible

- Every note has `kind: "line"`. Later kinds (`phrase`, `program`) get their own checker and card types; v1 builds only `line`.
- The line checker refuses more than one statement. A phrase checker is v2 work, not a loosening of this one.
- Effects are measured from end state, so "moves the needle" can't be detected by the v1 checker; v2 will need execution tracing.

**Out of scope for every version:** a general code editor or notebook, running code outside a card, runtime AI generation of cards, accounts or cloud sync, and anything social.

## 5. Try first, then help

Every card starts by asking for the whole line. Help appears only after a miss, and only the kind the miss calls for. Wil can already read code, and the evidence favours attempting first and getting targeted help over walking every note up a fixed staircase.

| Level | Learner sees | Learner does | Shown when |
| --- | --- | --- | --- |
| L5 Produce | An intent and the bench | Picks the effects, types the whole line | Always first |
| L4 Fill | The intent and the line with one part blanked | Types the missing part | After a miss caused by one part (wrong verb, wrong details, missing landing) |
| L3 Assemble | The intent and tiles | Orders the tiles. Each distractor is shown paired with the tile it imitates, as a choice of two | After a word-order (syntax) miss, or a miss at L4 |
| L2 Predict | The reference line and the bench | Ticks its effects, then predicts the result | After an effect miss ("changed something it shouldn't", "didn't land the result") |
| L1 Diagram | The reference line in chunks | Tags each chunk as subject, verb, details or landing | Only after a miss at L2 or L3 on the same card |

The old L0 (pick the intent from three) is removed. It trained recognition, which Wil already has.

**After a miss** the order is always: feedback (section 8) → the fallback level for that miss → the same note again at L5 with a different intent wording. The card ends on an unaided attempt. A miss still counts as wrong for scheduling, however the retry goes.

**Effect-first gate (L5 and L4).** Input is locked until the learner picks what the line should change (section 6). It's graded against the reference's effects, or against the learner's own effects when the line was correct by another route (for example `df.dropna(inplace=True)` mutates where the reference rebinds). A wrong pick shows a one-line hint and is logged against "Effect"; it doesn't end the card.

**Reworded intents.** Each note has 2–4 intent wordings, rotated so the same wording never appears twice in a row. This stops the learner memorising "this sentence → this line" instead of building the line.

**Which part L4 blanks.** The part the checker blamed for the miss. If it blamed none, rotate subject → verb → details → landing.

**Contrast pairs.** Notes that are easy to confuse (`.sort()` and `sorted()`, `>` and `>=`) carry the same `contrast` tag. When one is due, its partner is pulled into the same session if it's due within 3 days.

**I'm stuck.** Pressing `?` (or the Stuck button) at L5 counts as a miss and drops straight to L4 without revealing the answer. A freeze always turns into an easier attempt, never a dead end.

**Sure or unsure.** Enter checks the line as "sure"; Shift+Enter checks it as "unsure". A sure-but-wrong answer shows the rule first and gets one extra L5 retry later in the session. This is only logged; it never reaches FSRS.

**How each fallback level works.**

- **L4 Fill:** blanks the part named by the checker's `blame`. If the line has no such part (`len(orders)` has no subject), blank the next part in the rotation.
- **L3 Assemble:** tiles per section 9. Each distractor sits beside the tile it imitates as a choice of two. Correct means the tiles join into a line the checker accepts.
- **L2 Predict:** the learner ticks the effects, then picks what the main landed name holds now from three choices: the reference's value, and the values two of the note's traps produce on the same setup (traps that error are skipped; if fewer than two remain, the setup's original value fills in).
- **L1 Diagram:** the chunks are the top-level parts from `parts()`: landing, subject, verb and each detail. The learner drags each part name onto its chunk.

## 6. Screens and visual design

The review screen is the product; every other screen is plumbing. It always shows three things side by side: what the line must do, the state of the world before it runs, and the learner's sentence being built.

### Screens

| Screen | Purpose | Main controls |
| --- | --- | --- |
| Home | One button to start today's session | Start session, Add a line that froze me, Browse, Settings |
| Review | Runs one card at a time (layout below) | Effect gate, the level's work area, Check, Next |
| Feedback | Opens in place under the work area after Check | Compare diagrams, Show reference, Try again |
| Add / edit note | Writes a new note, including a line that froze him at work | Fields from section 9, Validate (runs it in Pyodide), Save |
| Browse | Lists notes by deck and due date, the stuck list, and misses by part and effect over the last 30 days | Search, filter, edit, stuck list |
| Settings | Daily limits and data | New notes per day (default 5), daily review cap (default 40), cards per session (default 20), Goal 1 finish-line thresholds, export JSON, import JSON, preload Python packages |

**Session summary.** Shown when a session ends: lines attempted, first-try correct, median seconds to first keystroke, and the part or effect missed most this session. It is information only: no score, no comparison against a target, no history graph on the home screen. Settings shows the four Goal 1 finish-line numbers (section 1) for anyone who wants to check them.

**Feedback layout after a miss.** One thing changes at a time. First the learner taps the chip they think is wrong (Space skips this). Then the checker's message appears next to the chip it's about, and chips that match the reference collapse. The bench animation plays on the next Space press.

**Add a line that froze me.** On Home, not buried in a menu. It opens the note editor with the line pasted in, so real notebook freezes become cards.

### Review screen regions

&#91;embedded content: review screen layout · 7 regions, shown at L5\]

The numbers match the list below; at lower levels only region 4 changes.

1. **Intent banner** — the English intent in large type (L3–L5), or the reference line itself (L1–L2).
2. **State panel ("the bench")** — names on the left as tags, objects on the right as boxes, with an arrow from each name to its object. Lists and dicts show their items; a DataFrame shows its first 5 rows and its shape; a model shows its class and whether it is fitted. This keeps state visible so it never has to be held in the head.
3. **Effect gate** (L4–L5) — four large toggle buttons: Rebinds a name, Mutates an object, Sends out, Nothing changes. The learner picks all that apply (\`x = lst.pop()\` both rebinds and mutates), then confirms; "Nothing changes" clears the others.
4. **Work area** — changes by level: taggable chunks (L1), effect ticks and a value box (L2), paired tiles (L3), a line with one blank (L4), an empty line input with Python syntax colouring (L5).
5. **Check** — Enter runs the line. Nothing about the answer is shown before this.
6. **Feedback** — the verdict, then the learner's line and the reference line as two sentence diagrams one above the other, then the bench animating before → after (section 8 defines the message).
7. **After check** — a correct line shows Next. A miss shows the fallback level, then the same note again at L5 (section 5). There are no rating buttons.

### The sentence diagram

A line is drawn as a row of chips, one per part, each filled with its part colour at low opacity and labelled with its part name in small caps above. A nested sentence (a detail that is itself a sentence) sits as an indented row under its parent chip, joined by a thin connector, collapsible. Hovering any chip shows what it gives back ("returns a new DataFrame", "returns None after mutating").

### Visual rules

- **Type:** a monospace face for all code (JetBrains Mono or IBM Plex Mono), a plain sans for UI text (Inter or system UI). Code at 18px or larger on the review screen.
- **Part colours:** Subject blue (#2563EB light, #60A5FA dark), Verb orange (#EA580C, #FB923C), Details green (#16A34A, #4ADE80), Landing purple (#7C3AED, #A78BFA). Chip fills use these at 12% opacity under the normal text colour, keeping text contrast at 4.5:1 or better. Defined as CSS variables with light and dark values; text on them stays the normal text colour. Never colour alone: every chip carries its part name.
- **State colours:** changed object = accent outline plus a short pulse; rebound name = its arrow slides to the new object; new object = fades in. Nothing else animates.
- **Motion:** 300ms or less, and none when the system asks for reduced motion.
- **Themes:** light and dark, following the system setting, with a manual toggle.
- **Keyboard first:** 1–4 toggle effects, Enter confirms and checks as sure, Shift+Enter checks as unsure, ? means stuck, Space continues. Tiles are reorderable by keyboard as well as by drag.
- **Layout:** desktop-first two-column (bench left, work right); stacks to one column under 900px wide.
- **No reward theatre:** no confetti, sounds, scores or progress bars on the review screen. The only counts shown are cards left in this session and the end-of-session summary.

## 7. Spaced repetition (automatic)

Spaced repetition runs in the background and the learner never touches it. A line comes back just before it would be forgotten, and that is the only idea taken from Anki.

**Library.** `ts-fsrs` pinned to exactly 5.4.2 (FSRS-6). Don't install 6.x: it is a beta with a renamed, async API. Settings: `request_retention: 0.9`, `enable_short_term: false` (so a missed card is simply due again tomorrow; no FSRS learning steps), `enable_fuzz: true` (spreads out notes added on the same day). Leave everything else at its default.

**What FSRS sees.** Only the first L5 attempt of each review. Fallback levels and retries after a miss are practice inside the session and are never sent to FSRS.

| First L5 attempt | Rating sent to FSRS |
| --- | --- |
| Correct, effect gate right | Good |
| Correct, effect gate missed | Hard |
| Wrong, or "Show reference" pressed first | Again |

A new note enters FSRS with the rating of its very first L5 attempt. Easy is never sent.

**Daily load.** New notes per day: 5 by default. Reviews per day: capped at 40 by default. On a day when due reviews reach the cap, no new notes are introduced.

**After missed days.** Due reviews are taken lowest predicted recall first (`get_retrievability` from ts-fsrs), up to the cap; the rest wait. The app never shows a backlog total, only today's session.

**Day boundary.** A new day starts at 4am local time. ts-fsrs works in UTC, so convert when deciding what is due today.

**Session order.** (1) Retries of notes missed earlier in this session, (2) due reviews, lowest recall first, (3) new notes. Decks are mixed; contrast pairs are pulled in together (section 5).

**Stuck notes.** A note missed on its first L5 attempt in 5 separate reviews is marked "stuck" in Browse, as a prompt to reword or split it. It keeps being scheduled; nothing is suspended automatically.

**Lapse count.** Read from the ts-fsrs card's own `lapses` field; don't store a second copy.

**Retry spacing.** After a miss, the fallback level comes straight away, but the L5 retry goes back into the queue 5 cards later (or last, if fewer than 5 remain). Retrying from memory a few cards later is real recall; retrying immediately is copying.

**Session floor.** If 4 of the last 6 first attempts were misses, the next cards are due notes answered correctly before, until 2 in a row are right. A bad stretch doesn't become a run of failures.

**Session size.** A session ends after the set number of cards (default 20), then shows the summary. Wil can start another session straight away.

**Prerequisites.** A note may list `requires` (section 9). A new note is introduced only after every note it requires has had at least one correct first L5 attempt. Among new notes that are unlocked, the order is the deck file's order.

## 8. Answer checking

The learner's line and the reference line are each run as real Python against the same setup. The answer is correct when, on every setup, both leave every touched name with an equal value, land results in the same names, delete the same names and print the same output. Text matching is never used, so `fruits += ['kiwi']` and `fruits.append('kiwi')` are both accepted.

### Runtime

- **Pyodide 314.0.7**, pinned. It ships Python 3.14.2, numpy 2.4.6, pandas 3.0.2 and scikit-learn 1.8.0. Load names: `numpy`, `pandas`, `scikit-learn` (which pulls in scipy, joblib and threadpoolctl). Load it from jsDelivr at that exact version.
- Pyodide runs in a dedicated **Web Worker**, so the UI never freezes. Packages load lazily: pandas on the first pandas card, scikit-learn on the first scikit-learn card. Show "Loading Python…" on the bench meanwhile.
- **Timeout: 5 seconds per check, covering all of a note's setups but not package loading (loading has its own 60-second limit while "Loading Python…" shows).** On timeout, terminate the worker, start a fresh one and report "Your line ran too long and was stopped." Don't use Pyodide's interrupt buffer: it needs cross-origin isolation headers that static hosts like GitHub Pages can't send. The cost is a Pyodide reload after a timeout; that is acceptable because timeouts are rare in one-line answers.
- **Isolation between checks.** Each run gets a fresh namespace, the same random seed (Python and numpy, seeded before the setup and again before the line), and any change to Python's built-ins is undone afterwards. Module-level state (for example a changed pandas option) can still leak between checks; the worker restarts at the start of every session to clear it.
- Worker messages: `{type: "check", setups, reference, answer}` → `check_all` result; `{type: "validate", setups, reference, traps}` → list of errors; `{type: "parts", line}` → diagram tree; `{type: "bench", setup, line}` → bench states.

### How a check works

1. Parse the answer. A syntax error, an empty answer or more than one statement stops here (blame: `assemble`).
2. Run the setup, record each visible name's identity and a deep copy of its value, seed randomness, run the line. A name with a new identity, or one the line assigns to, was **rebound**. A name with the same identity but different contents was **mutated**. A name that disappeared was **deleted**. Captured printing is **sends out**.
3. Do the same for the reference on a fresh setup.
4. Every name the reference lands in must be landed in, or mutated, by the answer. Then every name either line rebound or mutated is compared with `same()`.
5. Repeat on every setup in the note. The first setup that disagrees decides the result and is shown on the bench.

`same()` treats NaN as equal to NaN, compares numbers with a tolerance of 1e-9 (so `0.1 + 0.2` matches `0.3`), treats numpy and plain Python numbers and booleans alike, ignores dtype differences that don't change values (int vs float, `str` vs `object`), and compares fitted scikit-learn models by their settings and fitted attributes.

### Result fields

`correct`, `stage` (assemble, run, compare, note), `blame` (subject, verb, details, landing, effect, assemble, or none), `messages`, `effects` (reference and learner), `setup_index` (which setup failed). `blame` picks the fallback level in section 5: assemble → L3; verb, details or subject → L4 with that part blanked; landing or effect → L2; none → L4 with rotation.

**Per-note options.** `check_all(setups, reference, answer, options)` takes the note's `options` (section 9). Today there is one: `ignore_order: true` sorts DataFrame rows and columns, Series index and plain lists before comparing. Use it for notes where row or column order doesn't matter (for example `groupby(..., sort=False)` is then also accepted).

**Names never compared.** `_` and names created by an `import` in the answer are ignored. A walrus (`:=`) name is not ignored: it counts as an extra landing the intent didn't ask for.

**Real error text.** For a runtime error, the first message line is Python's own error type and text, unchanged (for example `KeyError: 'prices'`), and the part hint comes underneath. The learner practises reading the errors a notebook will show.

**pandas chained assignment.** When pandas raises its `ChainedAssignmentError` warning during the answer and the answer is wrong, the first message says so directly and gives the working form (`df.loc[row, 'col'] = …` or `df['col'] = …`).

### Feedback after a miss

The research is clear that explaining why an answer failed beats showing the right answer. So every miss shows, in order:

1. **What happened,** in the part and effect vocabulary: the checker's first message.
2. **Where it showed up:** the bench switches to the setup that exposed the miss, with the differing cells or items highlighted. DataFrames are shown as two small tables, never as text.
3. **The rule:** the note's one-line `rule` field (section 9), for example "dropna returns a new DataFrame; land it with df = …".
4. **The next step:** the fallback level (section 5), then a retry.

The reference line is shown only after the retry, or if the learner presses Show reference (which counts as a miss).

| Situation | Message pattern | Blame |
| --- | --- | --- |
| Syntax error | Python can't read this word order (col N): … | assemble |
| Empty or several statements | Write one line of Python. / One sentence at a time … | assemble |
| Runtime error | The error, then a part hint: NameError → a name isn't on the bench; AttributeError → that verb doesn't exist for this subject; KeyError → that key or column isn't in the subject | subject / verb / details |
| Result not landed | Landing: the result should land in `df` (df = …). | landing |
| A name became None | `x` is now None. `.sort()` changes its subject in place and returns None … | verb |
| Changed something it shouldn't, or didn't change something it should | Effect: … | effect |
| Model fitted on the wrong data | `model` is fitted differently from the reference. Check which data the verb was given. | none |
| Wrong value | `x` should be … but is … | none |

### Reference implementation

Rewritten after the 26 Oct 2026 audit. It passes a 71-case regression suite (below), which includes every false accept, false reject and crash the audit found. All 21 seed notes pass `validate`. Tested with CPython 3.13, pandas 3.0.5, numpy 2.5.3 and scikit-learn 1.9.1. **Phase 1 must re-run both inside Pyodide 314.0.7** (pandas 3.0.2, scikit-learn 1.8.0) and log any difference in DECISIONS.md. Use python/checker.py as-is; add `bench()` per the spec below.

The code lives in the repo, not in this doc, so there is only one copy to keep right: `python/checker.py` is the reference implementation and `python/tests/test_checker.py` is its regression suite. A third file, `python/tests/test_seed.py`, runs `validate()` on every seed note in `content/decks/`.

### Regression suite

In the repo as `python/tests/test_checker.py`. Phase 1 passes when it prints `mismatches: 0 of 71`, both with normal Python and inside Pyodide.

### `bench(setup, line)` spec

Returns, for before and after, a list of names and a list of objects, so the bench can draw tags, boxes and arrows. Each name carries the key of the object it points to (the object's `id()` as a string); two names with the same key share one box, which is how aliasing becomes visible. Each object carries its type, a preview (list and dict items up to 8; DataFrame `head(5)` as records plus `shape`; ndarray shape and first values; a model's class and whether it's fitted) and a `changed` flag. Previews must be JSON, never Python objects. A DataFrame column taken from another DataFrame gets its own box (pandas Copy-on-Write, section 3).

Details the builder shouldn't have to guess:

- **Object keys:** a counter assigned per `bench()` call in order of first appearance (`o1`, `o2`, …), keyed internally by `id()`. Never send raw `id()` values.
- **NaN and infinity:** sent as `null` with `"special": "nan" | "inf" | "-inf"`, because `json.dumps` writes invalid JSON for them.
- **Limits:** lists, tuples and dicts show the first 8 items, nested containers 2 levels deep, ndarrays their shape and first 8 values, DataFrames `head(5)`. Anything cut off carries `"more": <count>`.
- **Before and after** use the same keys, so an object that survives keeps its key and the animation can track it.

### Known limits

- Two lines that give equal results on every setup are both accepted. The note's setups decide how strict a note is.
- Iterators and generators are compared by type only; reading them would use them up.
- An object `deepcopy` can't copy is compared by identity only, so its mutation isn't detected. No seed card uses one.
- Series names and index dtypes are ignored, so `.rename('x')` on an answer isn't penalised.
- Without `ignore_order`, row and column order count. `groupby(..., sort=False)` passes on the seed setups only because their keys are already sorted (case C16); a note where order shouldn't matter sets `ignore_order`.

## 9. Data model

All data lives in the browser's IndexedDB (via Dexie) in five stores: notes, schedule, fsrsLog, attempts and settings. Seed decks ship as JSON and are imported on first run. Everything exports to one JSON file and imports back.

### Note (one sentence)

```json
{
  "id": "pd-dropna",
  "kind": "line",
  "deck": "pandas",
  "intents": [
    "Drop the rows where price is missing, and keep the result in df.",
    "Keep only rows that have a price, saving the result back to df."
  ],
  "setups": ["<PD1 from section 11>", "<PD2 from section 11>"],
  "reference": "df = df.dropna(subset=['price'])",
  "returns": "new",
  "rule": "dropna returns a new DataFrame; land it with df = …",
  "traps": ["df.dropna(subset=['price'])", "df = df.dropna()", "df = df.dropna(subset=['price'], inplace=True)"],
  "distractors": [{"tile": "df.dropna(", "imitates": "df = df.dropna("}],
  "tiles": null,
  "contrast": null,
  "requires": [],
  "options": {},
  "tags": ["cleaning"],
  "source": "seed",
  "version": 2
}
```

| Field | Rule |
| --- | --- |
| `kind` | Always `line` in v1. Reserved for `phrase` and `program` later (section 4). |
| `intents` | 2–4 plain-English wordings. Each names every name the line must create or change, and contains no code. |
| `setups` | At least 2. The first is shown on the bench. The others must change the reference's result, so a hard-coded answer fails. |
| `reference` | Exactly one statement. Runs on every setup and gives the same result on repeat runs. |
| `returns` | `new`, `none_after_mutating` or `same_after_mutating` (section 3). Shown on hover. |
| `rule` | One sentence shown after a miss (section 8). |
| `traps` | Whole wrong lines. Validate runs each one and refuses the note if any passes. Matched against the learner's line (to log which trap was hit) by `ast.dump`, with keyword arguments sorted first, so spacing, quote style and keyword order don't matter. |
| `distractors` | Wrong tile fragments for L3, each paired with the tile it imitates. They are never run, only shown. |
| `tiles` | Null means generated from the reference with Python's `tokenize` (a name with its leading dot, a keyword with its `=`, a whole string or number, a single bracket or operator, and the landing `df =` as one tile). A list overrides it. |
| `contrast` | A shared tag for mix-up pairs (section 5), or null. |
| `effects` | Not stored: derived by running the reference on the first setup. |

The Validate button runs `validate()` (section 8) and refuses to save until it returns no errors.

**Two more fields.** `requires` lists note ids that must have had a correct first L5 attempt before this note is introduced (section 7). `options` holds checker options, today only `ignore_order` (section 8).

**Tile rules** (when `tiles` is null), with examples from the seed notes:

- The landing with its `=` is one tile: `df =`, `X_train, X_test, y_train, y_test =`.
- A name is one tile; a method or attribute keeps its leading dot: `df`, `.dropna`, `.groupby`.
- An opening bracket that starts a call or a lookup stays with nothing else: `(`, `[`. Every closing bracket is its own tile.
- A keyword argument name keeps its `=`: `subset=`, `test_size=`.
- A whole string, number or f-string is one tile: `'price'`, `0.2`. A unary minus joins its number: `-1`.
- Each operator is its own tile: `>`, `&`, `*`, `+=`. Commas are their own tiles.
- A comprehension is split the same way, with `for` and `in` as separate tiles.

### Storage setup

```ts
db.version(1).stores({
  notes: 'id, deck, kind, source',
  schedule: 'noteId, fsrsCard.due',
  fsrsLog: '++id, noteId, review',
  attempts: '++id, noteId, at',
  settings: 'key'
});
```

On first run, call `navigator.storage.persist()` so the browser doesn't evict the data. Settings shows the last export date, and Home shows a one-line reminder when the last export is more than 14 days old.

### Schedule (one per note)

`{noteId, fsrsCard, stuckCount, blankNext, nextIntent}`. `fsrsCard` is the ts-fsrs card, with its dates stored as ISO strings and converted back on read. Lapses come from `fsrsCard.lapses`.

### Logs

- **fsrsLog:** the ts-fsrs review log, one entry per rated review, exactly as ts-fsrs returns it. Kept separate so it stays valid for the scheduler.
- **attempts:** one entry per answer at any level: `{noteId, at, intentIndex, level, effectPicked, effectCorrect, answer, correct, stage, blame, setupIndex, msToFirstKey, msToAnswer}`. Feeds the session summary and the Goal 1 finish line.

### Editing a note

Editing never resets scheduling or deletes history. Changing the reference or setups re-runs Validate. A "Reset progress" button in the editor starts the note over, but only when pressed.

### Versions and migrations

The database carries a `schemaVersion`, starting at 1. Every change to a store's shape gets a new Dexie `version(n).stores(...).upgrade(...)` step; existing data is migrated, never dropped. Seed notes have stable ids and a `version`. When a newer seed version ships, the note is updated only if Wil hasn't edited it (keep a hash of the last imported seed).

### Export and import

Export writes `{schemaVersion, exportedAt, notes, schedule, fsrsLog, attempts, settings}` as one `.json` file. Import offers Merge (keep the newer of each note) or Replace, and runs migrations first if the file is from an older schema.

## 10. Tech stack and file structure

A static single-page app with no server: React and TypeScript built with Vite, real Python through Pyodide, and all data in IndexedDB. It runs locally with `npm run dev` and can be deployed as static files (GitHub Pages works, because the design doesn't need cross-origin isolation headers).

Pin every version exactly in `package.json` (no `^` or `~`). Versions below were checked on the npm registry on 26 Oct 2026.

| Concern | Package | Pinned version | Note |
| --- | --- | --- | --- |
| Build | `vite` | 8.3.5 |  |
| UI | `react`, `react-dom` | 19.3.1 |  |
| Language | `typescript` | latest stable at project start | strict mode |
| Python | Pyodide (jsDelivr) | 314.0.7 | Python 3.14.2, numpy 2.4.6, pandas 3.0.2, scikit-learn 1.8.0 |
| Scheduling | `ts-fsrs` | 5.4.2 | Not 6.x (beta, renamed API) |
| Storage | `dexie` | 4.4.7 |  |
| Tile drag | `@dnd-kit/sortable` (plus `@dnd-kit/core`) | 10.0.0 | Install @dnd-kit/core at the version sortable 10.0.0 lists in its peerDependencies. Keyboard sorting is built in. Don't use the pre-1.0 @dnd-kit/react line |
| Line input (L4, L5) | `@codemirror/lang-python` with CodeMirror 6 | 6.2.1 | Syntax colour only; autocomplete off |
| Worker messages | `comlink` (optional) | 4.4.2 | Or plain `postMessage` |
| Tests | Vitest (scheduler, fallback logic, tiles); pytest (checker); Playwright (one session end to end) | latest stable at project start |  |

**Offline.** A small hand-written service worker caches the app shell and the Pyodide 314.0.7 files the first time they load (including the pandas and scikit-learn packages once used), so later sessions start without the network.

```text
sentence-lab/
  index.html
  src/
    main.tsx
    app/            routes: Home, Review, Browse, NoteEditor, Settings
    review/         L5Produce, L4Fill, L3Assemble, L2Predict, L1Diagram, EffectGate, Feedback, SessionSummary
    bench/          Bench.tsx (tags, boxes, arrows), before/after animation
    diagram/        SentenceDiagram.tsx (chips, nested clauses)
    srs/            scheduler.ts (ts-fsrs wrapper, rating from first L5 attempt), queue.ts (session order, caps)
    python/         worker.ts (loads Pyodide + checker.py), client.ts (typed messages, timeout, restart)
    data/           db.ts (Dexie stores + migrations), seed.ts, exportImport.ts
    tiles/          generateTiles.ts (via the worker's tokenize)
    styles/         tokens.css (parts, states, themes)
  python/
    checker.py      reference implementation (section 8); add bench()
    tests/test_checker.py   71-case regression suite
    tests/test_seed.py      runs validate() on every seed note
  content/decks/
    core.json  pandas.json  sklearn.json
```

**No autocomplete anywhere.** Autocomplete would produce the line for the learner, which removes the skill the app trains.

## 11. Seed content

The seed decks exist for Goal 1: they give the sentence skill real material to work on. The lines come from data work (pandas, scikit-learn) so the learner sees job-relevant code, but each card tests only whether he can produce the sentence. The 21 notes below all passed `validate()` on 26 Oct 2026, and every trap is rejected on at least one setup. They set the quality bar; the decks grow to about 40 / 40 / 20 notes in the same style.

### What the decks draw on (exposure, not a syllabus)

| Deck | Sentence shapes it exercises | Example verbs |
| --- | --- | --- |
| Core Python | Rebind vs mutate, lookups, landing a result, comprehensions | `=`, `+=`, `.append`, `.pop`, `sorted`, `len`, `d[k]`, `.upper` |
| pandas | Nested sentences (masks inside lookups), chained verbs, landing results under Copy-on-Write | `[ ]`, `.dropna`, `.fillna`, `.groupby().mean()`, `.rename`, new columns |
| scikit-learn | Unpacking several landings, verbs that mutate and return self, using the right data | `train_test_split`, `.fit`, `.predict` |

### Authoring rules

1. One statement, no semicolons. A one-line comprehension counts as one statement.
2. 2–4 intents per note, in plain English, naming every target name. No code in an intent.
3. At least 2 small setups (2–5 rows or items), and the extra setups must change the reference's result. Include a boundary value whenever the line compares (`qty` of exactly 10 for `> 10`).
4. The reference shows correct practice: no `inplace=True`, no training and predicting on the same data, no chained assignment, results always landed.
5. Every trap must fail on at least one setup; Validate enforces it.
6. One `rule` sentence per note, saying why the usual mistake fails.
7. List prerequisites in `requires`: a note that uses a comparison, unpacking or a mask needs the note that teaches it.
8. For later scikit-learn cards: don't use `LogisticRegression(penalty=...)` (deprecated in 1.8, removed in 1.10; use `C` and `l1_ratio`), and remember `OneHotEncoder` returns a sparse matrix unless `sparse_output=False`.

### Shared setups

```python
# PD1 — first pandas setup (shown on the bench)
import pandas as pd
df = pd.DataFrame({'category': ['a','b','a','c'], 'price': [10.0, None, 30.0, 5.0], 'qty': [3, 12, 20, 10]})

# PD2 — second pandas setup: a missing category, a boundary qty of 10
import pandas as pd
df = pd.DataFrame({'category': ['x','y',None], 'price': [None, 2.5, 4.0], 'qty': [10, 11, 1]})

# SK1 / SK2 — scikit-learn base; SK2 uses y = np.arange(10) * 3.0 + 1
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
X = np.arange(20).reshape(10, 2)
model = LinearRegression()
y = np.arange(10) * 2.0

# SKS1 / SKS2 — SK1 / SK2 plus:
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# SKF1 / SKF2 — SKS1 / SKS2 plus:
model.fit(X_train, y_train)
```

### Verified seed notes

| Deck | Intents | Reference | Effects | Setups | Requires | Rule | Traps (all fail) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| core | Check whether qty is above 10, keeping True or False in big\_order. / Store in big\_order whether qty is greater than 10. | `big_order = qty > 10` | rebinds | `12`, `10` | — | A comparison makes True or False; land it like any other result. | `big_order = qty >= 10`, `qty > 10` |
| core | Split pair into two names, first and second. / Unpack the two items of pair into first and second. | `first, second = pair` | rebinds | `(3, 'x')`, `('a', 'b')` | — | Several names left of = take the items in order. | `first = pair[0]`, `first, second = pair[1], pair[0]` |
| core | Add 'kiwi' to the end of fruits. / Put 'kiwi' on the end of the fruits list, changing that list itself. | `fruits.append('kiwi')` | mutates | `['apple','pear']`, `[]` | — | append changes the list and returns None; don't land it. | `fruits = fruits.append('kiwi')`, `fruits.insert(0, 'kiwi')` |
| core | Make a sorted copy of scores called ranked, leaving scores as it is. / Put the scores in order, lowest first, in a new list ranked; don't touch scores. | `ranked = sorted(scores)` | rebinds | `[3,1,2]`, `[5,5,0]` | — | sorted() gives a new list; .sort() changes the old one and returns None. | `ranked = scores.sort()`, `scores.sort()` |
| core | Look up Ana's age in ages and keep it in age. / Get the value stored under 'Ana' in ages, as age. | `age = ages['Ana']` | rebinds | two dicts, different Ana values | — | A dict key goes in square brackets as a value, here the string 'Ana'. | `age = ages[Ana]`, `age = ages.Ana` |
| core | Set Ben's age in ages to 28. / Change the value stored under 'Ben' in ages to 28. | `ages['Ben'] = 28` | mutates | two dicts | — | One = stores; == only compares. | `ages['Ben'] == 28`, `ages = {'Ben': 28}` |
| core | Count how many orders there are and keep the number in n. / Store the number of items in orders as n. | `n = len(orders)` | rebinds | 3 items, empty | — | len() is a function you hand the list to, not a method on it. | `n = orders.len()`, `n = orders.count()` |
| core | Add 5 to total. / Increase total by 5. | `total += 5` | rebinds | `10`, `-2` | — | += computes and lands in one step. | `total + 5`, `total == total + 5`, `total = 15` |
| core | Remove the last item from stack and keep it in top. / Take the item off the end of stack, storing it as top. | `top = stack.pop()` | mutates + rebinds | `[1,2,3]`, `['a']` | — | pop() removes the item and returns it, so the line changes stack and lands in top. | `top = stack[-1]`, `stack.pop()` |
| core | Make a new list, upper, with every name in names in capitals. / Build upper: each name from names, uppercased. | `upper = [n.upper() for n in names]` | rebinds | `['ana','ben']`, `['cy']` | — | String methods work on one string; a comprehension applies one to each. | `upper = names.upper()`, `upper = ['ANA', 'BEN']` |
| pandas | Drop the rows where price is missing, and keep the result in df. / Keep only rows that have a price, saving the result back to df. | `df = df.dropna(subset=['price'])` | rebinds | PD1, PD2 | — | dropna returns a new DataFrame; land it with df = … | `df.dropna(subset=['price'])`, `df = df.dropna()`, `df = df.dropna(subset=['price'], inplace=True)` |
| pandas | Keep only the rows where qty is above 10, in a new DataFrame called big. / Make big: the rows of df with qty over 10. | `big = df[df['qty'] > 10]` | rebinds | PD1, PD2 | core-compare | The inner sentence makes a True/False mask; the outer \[ \] keeps the True rows. | `big = df[df['qty'] >= 10]`, `big = df['qty'] > 10` |
| pandas | Keep the rows where qty is above 10 and below 20, in a new DataFrame called mid. / Make mid: rows of df with qty between 10 and 20, both ends excluded. | `mid = df[(df['qty'] > 10) & (df['qty'] < 20)]` | rebinds | PD1, PD2 | pd-filter | Masks combine with & and \|, and each comparison needs its own brackets; `and` doesn't work on columns. | `mid = df[df['qty'] > 10 & df['qty'] < 20]`, `mid = df[(df['qty'] > 10) and (df['qty'] < 20)]`, `mid = df[(df['qty'] >= 10) & (df['qty'] <= 20)]` |
| pandas | Get the average price for each category, as avg. / Store the mean price per category in avg. | `avg = df.groupby('category')['price'].mean()` | rebinds | PD1, PD2 | — | Group first, pick the column, then the verb that summarises. | `avg = df['price'].mean()`, `avg = df.groupby('price')['category'].mean()` |
| pandas | Add a column called total that is price times qty. / Give df a new column, total, equal to price multiplied by qty. | `df['total'] = df['price'] * df['qty']` | mutates | PD1, PD2 | — | New columns land with df\['name'\] = …, not df.name. | `df.total = df.price * df.qty`, `total = df['price'] * df['qty']` |
| pandas | Set qty in row 0 of df to 99. / Change the qty value in the first row (label 0) to 99. | `df.loc[0, 'qty'] = 99` | mutates | PD1, PD2 | pd-newcol | One cell is set with df.loc\[row, column\]; a chain like df\['qty'\]\[0\] changes nothing under Copy-on-Write. | `df['qty'][0] = 99`, `df.loc[0] = 99` |
| pandas | Replace missing prices with 0, keeping the result in the price column. / Fill the gaps in df's price column with 0. | `df['price'] = df['price'].fillna(0)` | mutates | PD1, PD2 | — | Under Copy-on-Write, fixing a column in place does nothing; land the result back in the column. | `df['price'].fillna(0, inplace=True)`, `df = df.fillna(0)`, `df['price'].fillna(0)` |
| pandas | Rename the column qty to quantity, keeping the result in df. / Change the qty column's name to quantity and save it back to df. | `df = df.rename(columns={'qty': 'quantity'})` | rebinds | PD1, PD2 | — | rename needs columns= and returns a new DataFrame. | `df.rename(columns={'qty': 'quantity'})`, `df = df.rename({'qty': 'quantity'})` |
| sklearn | Split X and y into train and test sets with 20% for testing and random\_state 42. / Hold out 20% of X and y as a test set (random\_state 42), unpacking into X\_train, X\_test, y\_train, y\_test. | `X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)` | rebinds | SK1, SK2 | core-unpack | The four landings come back in the order X\_train, X\_test, y\_train, y\_test. | names in the wrong order; `test_size=20` |
| sklearn | Train model on the training data. / Fit model using X\_train and y\_train. | `model.fit(X_train, y_train)` | mutates | SKS1, SKS2 | sk-split | Fit only on training data; fit changes the model itself. | `model.fit(X, y)`, `model = LinearRegression()`, `model.predict(X_train)` |
| sklearn | Use the trained model to predict on the test set, keeping the results in preds. / Store model's predictions for X\_test in preds. | `preds = model.predict(X_test)` | rebinds | SKF1, SKF2 | sk-fit | predict returns new values; land them, and use the test set. | `preds = model.predict(X_train)`, `preds = model.fit(X_train, y_train)`, `model.predict(X_test)` |

Note ids, in table order: core-compare, core-unpack, core-append, core-sorted, core-lookup, core-set, core-len, core-augadd, core-pop, core-comp, pd-dropna, pd-filter, pd-and, pd-groupby, pd-newcol, pd-loc, pd-fillna, pd-rename, sk-split, sk-fit, sk-predict. The same 21 notes, with setups, are in `content/decks/*.json` in the repo.

## 12. Guardrails

These are rules the build must keep even when a shortcut looks harmless. Each one protects the single thing the app trains: producing a line unaided.

- **Produce before reveal.** No card shows its answer, a hint, or the reference before the learner has committed an answer. "Show reference" exists but counts as Again.
- **No autocomplete, snippets or AI help** in any input.
- **No passive playback.** The bench animates only the consequence of a line the learner chose. There is no auto-play mode where the app runs code while the learner watches.
- **No reward layer.** No points, XP, streaks, targets, badges, levels shown as achievements, confetti or sounds. Help levels are internal; the learner sees the card, not a rank. The session summary is information, not a score.
- **Correctness comes from Python, never from the learner.** The learner never rates a card; spaced repetition stays in the background.
- **Feedback is causal.** Every wrong-answer message names a part or an effect and says what happened, never just "Incorrect".
- **Stays small.** No accounts, no server, no sync, no general-purpose editor. Anything outside section 4's version list needs a change to this doc first. Goal 2 skills are never added to Goal 1 decks as tested content.

## 13. Build phases (v1)

Build in this order. Phase 3 produces the smallest loop Wil can actually study with, so it comes before the visuals. Don't start a phase until the previous phase's checks pass.

### Phase 1 — Python in the browser

- [ ] Worker loads Pyodide 314.0.7 and `checker.py` (from the repo, unchanged); the client sends `check`, `validate` and `parts` and gets typed results back
- [ ] A 5-second timeout terminates and restarts the worker; the UI reports it
- [ ] pandas and scikit-learn load lazily on first need
- [ ] `test_checker.py` prints `mismatches: 0 of 71` with normal Python and inside Pyodide; any difference is logged in DECISIONS.md
- [ ] `test_seed.py` shows all 21 seed notes from section 11 passing `validate()`, both places

### Phase 2 — Data and scheduling

- [ ] Dexie stores and `schemaVersion` 1 from section 9; seed decks import on first run
- [ ] FSRS rating comes only from the first L5 attempt, per the table in section 7 (Vitest: one test per row)
- [ ] Daily caps, the 4am day boundary, lowest-recall-first ordering after missed days, contrast pairs, retry spacing, the session floor, session size and prerequisites work as section 7 says

### Phase 3 — Minimum study loop

- [ ] Review screen with intent, effect gate, L5 input, Check, feedback messages as text and the `rule` line
- [ ] A miss goes to L4 or a retry, then the same note again at L5 with another intent wording
- [ ] Wil can study the pandas deck, close the app, and come back the next day to the right notes due

### Phase 4 — Bench and sentence diagram

- [ ] `bench()` added to `checker.py` with pytest coverage; previews are JSON only
- [ ] Bench draws names, boxes and arrows; shared objects share one box; it animates before → after and switches to the setup that exposed a miss
- [ ] Sentence diagram shows the learner's line and the reference with part chips and collapsible nested clauses; `+=` is labelled from the checker's effects
- [ ] Reduced-motion turns animation off

### Phase 5 — Fallback levels

- [ ] L4 blanks the part named by `blame`; L3 shows paired distractors; L2 and L1 as section 5 says; the ? stuck key drops to L4 without showing the answer; Shift+Enter logs unsure
- [ ] The fallback level is chosen from `blame` exactly as section 8's result-fields paragraph says
- [ ] Tiles are generated from the reference when `tiles` is null

### Phase 6 — Authoring and data tools

- [ ] Add/edit note with Validate (refuses to save on any error); editing never resets scheduling; Reset progress works
- [ ] Browse with search, filters and the stuck list
- [ ] Export and import (Merge and Replace) round-trip without loss, including migration from an older schema

### Phase 7 — Content and finish

- [ ] Decks reach about 40 / 40 / 20 notes and every note passes Validate
- [ ] Session summary and the four Goal 1 finish-line numbers in Settings are computed from the attempts log
- [ ] One Playwright test studies a new note through a miss, a fallback and a correct retry
- [ ] Light and dark themes, keyboard-only use and the under-900px layout checked by hand

## 14. Handing this to Antigravity

Export this doc as Markdown, save it as `ARCHITECTURE.md` at the root of an empty `sentence-lab` repo, and start the agent with the prompt below. Run one phase per session, and check that phase's boxes yourself before starting the next.

```text
Read ARCHITECTURE.md fully before writing any code. It is the source of truth.

Build Phase <N> from section 13 only. Rules:
- This build is Goal 1 only (section 1). Don't add Goal 2 features or content.
- Use python/checker.py and python/tests/ exactly as committed. Don't rewrite their logic.
- Use content/decks/*.json (the 21 notes in section 11) as the seed content and as test fixtures.
- Pin every version in section 10 exactly. Use ts-fsrs 5.4.2, not 6.x.
- Follow the guardrails in section 12 without exception (no autocomplete, no rating buttons, no reward layer, try before help).
- Where this doc is silent, choose the simplest option and record it in DECISIONS.md with one line of why.
- Where this doc contradicts itself or a library's real API, stop and ask instead of guessing.
- Finish by running the phase's checks and reporting each box as pass or fail.
```

**What has been verified.** Library versions and the ts-fsrs setting names were checked against the npm registry and the package source on 26 Oct 2026. The checker (71 test cases) and the 21 seed notes were tested with normal Python (3.13, pandas 3.0.5, scikit-learn 1.9.1). They have not yet been run inside Pyodide 314.0.7, which ships pandas 3.0.2 and scikit-learn 1.8.0; Phase 1 does that first.
