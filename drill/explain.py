"""'Explain this line' items: read a line, then say what it does.

Three steps, no typing of code: classify the effect, name the four slots, predict the
result. Several items are deliberately buggy or subtly different lines.
"""
from dataclasses import dataclass
from typing import Callable

from drills import SHOWN, NONE, _price_df, _scaler_env


@dataclass
class Explain:
    id: str
    domain: str
    setup: Callable[[], dict]
    line: str
    effect: str
    grammar: dict
    question: str
    options: list
    answer: int
    why: str


EXPLAINS = [
    Explain(
        id="ex-append-bug", domain="python",
        setup=lambda: {"scores": [72, 88, 91]},
        line="scores = scores.append(95)", effect="rebind",
        grammar={"subject": ["scores"], "verb": [".append", "append"], "details": ["95"],
                 "variable": ["scores"]},
        question="After this line runs, what is scores?",
        options=["[72, 88, 91, 95]", "None", "[72, 88, 91]", "an error"], answer=1,
        why=".append changes the list itself and produces no result (None). Then scores = "
            "stores that nothing, replacing your list."),
    Explain(
        id="ex-sort", domain="python",
        setup=lambda: {"nums": [3, 1, 2]},
        line="nums.sort()", effect="mutate",
        grammar={"subject": ["nums"], "verb": [".sort", "sort"], "details": NONE,
                 "variable": ["none", "dropped"]},
        question="After this line runs, what is nums?",
        options=["[1, 2, 3]", "[3, 1, 2]", "None", "[]"], answer=0,
        why="sort() reorders the list itself. The variable is empty because there is no separate result."),
    Explain(
        id="ex-df-bare", domain="pandas",
        setup=_price_df,
        line="df.dropna(subset=['price'])", effect="emit",
        grammar={"subject": ["df"], "verb": [".dropna", "dropna"],
                 "details": ["subset=['price']"], "variable": SHOWN},
        question="After this line runs, how many rows does df have?",
        options=["2", "3", "0", "an error"], answer=1,
        why="dropna builds a new table. With no variable it is only displayed, so df keeps "
            "all its rows."),
    Explain(
        id="ex-df-reassign", domain="pandas",
        setup=_price_df,
        line="df = df.dropna(subset=['price'])", effect="rebind",
        grammar={"subject": ["df"], "verb": [".dropna", "dropna"],
                 "details": ["subset=['price']"], "variable": ["df"]},
        question="After this line runs, how many rows does df have?",
        options=["2", "3", "0", "an error"], answer=0,
        why="The variable is df, so the new table replaces the old one."),
    Explain(
        id="ex-scaler-leak", domain="sklearn",
        setup=_scaler_env,
        line="X_test_s = scaler.fit_transform(X_test)", effect="rebind",
        grammar={"subject": ["scaler"], "verb": [".fit_transform", "fit_transform"],
                 "details": ["X_test"], "variable": ["X_test_s"]},
        question="What is wrong with this line, given scaler was already fitted on the training data?",
        options=["Nothing: it scales X_test as intended",
                 "It refits the scaler on the test data, changing what it learned",
                 "It modifies X_test in place", "It raises an error"], answer=1,
        why="fit_transform makes the scaler learn again from the test data, which mixes test "
            "data into what it learned. Use scaler.transform(X_test) on test data."),
    Explain(
        id="ex-print-sum", domain="python",
        setup=lambda: {"scores": [72, 88, 91]},
        line="print(sum(scores))", effect="emit",
        grammar={"subject": ["scores"], "verb": ["sum"], "details": NONE,
                 "variable": SHOWN},
        question="After this line runs, what changed?",
        options=["251 is shown; scores is unchanged", "scores becomes 251",
                 "scores is emptied", "nothing is shown"], answer=0,
        why="print shows a value and changes nothing."),
]
