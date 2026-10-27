# Sentence Lab — Design Review

Overall assessment: Strong learning concept, but the specification is more complicated than the problem it is trying to solve.

I would pursue this. The central idea is sound: Sentence Lab isn't trying to teach Python from scratch. It is trying to close the gap between understanding code and producing it independently.

That distinction matters. A conventional coding course teaches concepts, while a flashcard system often trains recognition. Sentence Lab instead trains the ability to translate an intention into executable Python.

Three decisions stand out positively:

- L5 first, then scaffold: Attempt the actual line before receiving help. This preserves the skill you're trying to develop.
- Visualize state changes: Showing how names, objects, and values change makes Python's behavior concrete rather than abstract.
- Execute answers instead of matching text: Accepting multiple valid solutions is much better than forcing learners to memorize one exact expression.

The fallback ladder is also consistent with research on scaffolding code-writing tasks. However, research on Parsons-style exercises finds stronger evidence for improving practice efficiency than for guaranteeing long-term learning gains.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://doi.org\&sz=32)

Volume 1

+1



The biggest question isn't whether the learning mechanism is promising. It's whether every feature contributes enough to justify its complexity.

## Where I'd push back

| Priority | Concern                                                                 | What I'd change                                                 |
| -------- | ----------------------------------------------------------------------- | --------------------------------------------------------------- |
| High     | Mandatory effect gate adds friction before every line                   | Make it temporary scaffolding that fades as competence improves |
| High     | Success on rehearsed cards may not transfer to notebooks                | Test unfamiliar prompts and actual notebook work                |
| High     | Adding your own notes is cumbersome                                     | Add a quick-capture inbox, separate from card authoring         |
| Medium   | The checker can accept technically equivalent but undesirable solutions | Separate behavioral correctness from best-practice feedback     |
| Medium   | Too much infrastructure precedes proving the learning experience        | Pilot with 15–20 cards before building the complete system      |

### 1. The effect gate could work against fluency

This is my biggest concern with the actual learning design.

The app requires selecting what a line changes before the learner can write Python.

That makes sense when initially teaching the distinction between mutation and reassignment. But the eventual goal is to look at an intent and produce code naturally.

Consider:

INTENT

Add `"kiwi"` to the end of `fruits`.

CURRENT WORKFLOW

Choose effect

Write code

Check

EVENTUAL TARGET

Write code naturally

Check

I'd retain the effect gate as a teaching mechanism, but remove its mandatory role once a pattern is consistently understood.

Otherwise, Sentence Lab could teach a ritual that doesn't translate into natural coding.

### 2. The finish line measures recall more than transfer

The 80% first-try threshold on new notes and 90% recall on due notes are useful.

But there is an important distinction between recalling a familiar line and composing a genuinely unfamiliar one.

Rotating between 2–4 English phrasings helps, but doesn't guarantee transfer. The learner can still memorize the structure of each card.

I'd introduce a small set of unseen transfer challenges that combine familiar syntax with unfamiliar situations.

For instance, after practicing filtering DataFrames on `qty`, ask the learner to filter a different DataFrame using another column and threshold.

This evaluates whether the underlying skill has developed rather than whether a particular card has been learned.

It also gives you better evidence for when Goal 1 is genuinely finished.

### 3. The add-your-own-note feature needs rethinking

This is the biggest usability contradiction in the specification.

The home screen promises a simple action: Add a line that froze me.

But a valid note requires multiple intents, setups, a reference, traps, a rule, return behavior, and validation.

That's a substantial authoring task, especially when the person is already struggling to produce the Python.

I'd separate two concepts:

Capture: Quickly record what you were trying to do and, optionally, the incorrect line you attempted.

Authoring: Turn that record into a validated study card later.

The captured item wouldn't enter spaced repetition until it was valid. This maintains your automatic grading requirements without turning study into content administration.

## Technical review

The stack is reasonable. I verified that Pyodide 314.0.7 and ts-fsrs 5.4.2 are real, documented versions, and Pyodide supports Python execution in a Web Worker.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyodide.org\&sz=32)

Version 314.0.7

+2



The architecture has clearly received substantial attention. Still, several things should be corrected before Antigravity builds it.

1\. The answer checker is necessarily imperfect. Comparing final states across two setups is a reasonable strategy, but does not establish that an answer generalizes. Expand the test cases, especially for aliases, empty inputs, missing values, and shape changes. Also, the current `run()` implementation does not catch errors arising while executing a note's setup, so a malformed custom setup can crash validation instead of generating useful feedback.

2\. Feedback timing contradicts itself. Section 6 describes showing both the learner's and reference lines immediately after checking. Section 8 says the reference is hidden until after a retry. Meanwhile, L1 and L2 explicitly display the reference. Pick one reveal sequence and implement it consistently.

3\. Correctness and good practice aren't identical. The test suite accepts `df.dropna(..., inplace=True)` as equivalent to assigning the result back to `df`, although the teaching rules discourage `inplace=True`. That's defensible for behavioral equivalence, but feedback should distinguish works from preferred approach.

4\. Untrusted imported cards can execute Python. Pyodide running in a Worker is not a security boundary against malicious Python accessing browser APIs. Treat imported decks as executable content, not harmless JSON.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pyodide.org\&sz=32)

Version 314.0.7



These are manageable issues, not reasons to abandon the design.

## What I would actually build first

Your current seven-phase plan is optimized for building the complete application correctly.

I'd first validate whether the training loop actually solves the problem.

Sentence Lab — Learning Pilot

A smaller version to test for approximately one week before committing to the full specification.

Include

15–20 curated cards, L5 free typing, execution-based checking, a basic before/after bench, L4 help after a miss, and delayed retries.

Defer

L1–L3 interactions, complex note authoring, full FSRS integration, custom analytics, 100 seed cards, and elaborate animations.

Measure

First-try correctness, time to begin typing, number of freezes, and performance on unfamiliar Python tasks.

This would produce something you could genuinely study with while discovering which mechanisms make the biggest difference.

## Final recommendation

Keep the central model, the L5-first approach, real execution, the visual bench, and spaced repetition.

The most distinctive idea here is not FSRS or the sentence diagram. It is the combination of retrieval practice and immediate, concrete feedback about what Python actually did.

That's the product worth developing.

My main recommendation is to make the system adaptive not just in how much help it provides after a mistake, but in how little help it requires once a skill becomes automatic.

Sentence Lab should eventually get out of the learner's way. The strongest evidence of success will be opening a blank Jupyter cell, knowing what needs to happen, and beginning to type without having to think through the app's framework.