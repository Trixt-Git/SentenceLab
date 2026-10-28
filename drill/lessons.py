"""Short lessons shown before the drills they support.

Stage order (cognitive-apprenticeship style, fading support):
  predict -> contrast pair -> labelled worked example -> faded x2
Contrast pairs and predictions are executed live against a real namespace, so the
state diff shown is what Python actually did.
"""
from dataclasses import dataclass, field
from typing import Callable

from drills import _price_df


@dataclass
class Lesson:
    id: str
    title: str
    effect: str
    before: str                      # drill id this lesson precedes
    setup: Callable[[], dict]
    predict: dict                    # {line, question, options, answer}
    contrast: dict                   # {a, b, question, options, answer, explain}
    worked: dict                     # {line, slots, why, options, answer}
    faded: list = field(default_factory=list)  # [{template, answers}]


LESSONS = [
    Lesson(
        id="mutate", title="Mutate: change the object, keep the name", effect="mutate",
        before="py-append",
        setup=lambda: {"scores": [72, 88, 91]},
        predict=dict(
            line="scores.append(95)",
            question="After this line runs, what is scores?",
            options=["[72, 88, 91]", "[72, 88, 91, 95]", "None", "an error"], answer=1),
        contrast=dict(
            a="scores.append(95)", b="scores = scores.append(95)",
            question="What is different about scores afterwards?",
            options=["Nothing: both give [72, 88, 91, 95]",
                     "The second overwrites scores with None",
                     "The second raises an error",
                     "The first creates a new list"], answer=1,
            explain=".append changes the list in place and returns None. Assigning that "
                    "None to scores throws the list away."),
        worked=dict(
            line="scores.append(95)",
            slots={"Subject": "scores", "Verb": ".append", "Details": "95", "Landing": "none"},
            why="Why is Landing empty?",
            options=["The list is changed in place, so nothing needs to catch a result",
                     "append is slow", "Lists cannot be reassigned", "Because 95 is an int"],
            answer=0),
        faded=[dict(template="___.append(95)", answers=[["scores"]]),
               dict(template="___.___(95)", answers=[["scores"], ["append", ".append"]])],
    ),
    Lesson(
        id="rebind", title="Rebind: a new object must land in a name", effect="rebind",
        before="py-sorted",
        setup=lambda: {"nums": [3, 1, 2]},
        predict=dict(
            line="ranked = sorted(nums)",
            question="After this line runs, what is nums?",
            options=["[1, 2, 3]", "[3, 1, 2]", "None", "[]"], answer=1),
        contrast=dict(
            a="nums.sort()", b="ranked = sorted(nums)",
            question="Which line leaves nums unchanged?",
            options=["nums.sort()", "ranked = sorted(nums)", "Both", "Neither"], answer=1,
            explain="sort() mutates nums and returns None. sorted() returns a new list "
                    "that has to land in a name or it disappears."),
        worked=dict(
            line="ranked = sorted(nums)",
            slots={"Subject": "nums", "Verb": "sorted", "Details": "none", "Landing": "ranked"},
            why="What happens if you drop 'ranked ='?",
            options=["The sorted list is computed and thrown away", "nums gets sorted",
                     "It raises an error", "ranked is created anyway"], answer=0),
        faded=[dict(template="ranked = ___(nums)", answers=[["sorted"]]),
               dict(template="___ = ___(nums)", answers=[["<name>"], ["sorted"]])],
    ),
    Lesson(
        id="pandas", title="pandas returns a new DataFrame", effect="rebind",
        before="pd-dropna",
        setup=_price_df,
        predict=dict(
            line="df.dropna(subset=['price'])",
            question="After this line runs, how many rows does df have?",
            options=["2", "3", "0", "an error"], answer=1),
        contrast=dict(
            a="df.dropna(subset=['price'])", b="df = df.dropna(subset=['price'])",
            question="In which line does df lose the row with the missing price?",
            options=["the first", "the second", "both", "neither"], answer=1,
            explain="Most pandas methods return a new DataFrame and leave the original "
                    "alone, so the result must land in a name. Prefer rebinding over "
                    "inplace=True, whose behaviour is harder to predict."),
        worked=dict(
            line="clean_df = df.dropna(subset=['price'])",
            slots={"Subject": "df", "Verb": ".dropna", "Details": "subset=['price']",
                   "Landing": "clean_df"},
            why="Why does this line need a Landing?",
            options=["The method returns a new DataFrame, which is lost unless bound",
                     "dropna edits df in place", "Landing is optional for every method",
                     "pandas forbids reusing df"], answer=0),
        faded=[dict(template="clean_df = df.___(subset=['price'])",
                    answers=[["dropna", ".dropna"]]),
               dict(template="___ = df.___(subset=['price'])",
                    answers=[["<name>"], ["dropna", ".dropna"]])],
    ),
    Lesson(
        id="emit", title="Emit: look at a value without changing anything", effect="emit",
        before="pd-head",
        setup=lambda: {"scores": [72, 88, 91]},
        predict=dict(
            line="print(sum(scores))",
            question="After this line runs, what changed?",
            options=["251 is shown; scores is unchanged", "scores becomes 251",
                     "scores is emptied", "nothing is shown"], answer=0),
        contrast=dict(
            a="print(sum(scores))", b="total = sum(scores)",
            question="Which line shows you the value?",
            options=["the first", "the second", "both", "neither"], answer=0,
            explain="Emit shows a value and changes no state. Rebinding saves it silently."),
        worked=dict(
            line="print(sum(scores))",
            slots={"Subject": "scores", "Verb": "sum", "Details": "none", "Landing": "print"},
            why="Why is Landing print rather than a variable?",
            options=["The goal is to see the value, not keep it", "print is faster",
                     "Variables cannot hold sums", "sum() requires print"], answer=0),
        faded=[dict(template="print(___(scores))", answers=[["sum"]]),
               dict(template="___(___(scores))", answers=[["print"], ["sum"]])],
    ),
]

BY_ID = {l.id: l for l in LESSONS}
