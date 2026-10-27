"""Drill definitions. One grammatical clause per drill.

grammar values are lists of accepted answers (first one is shown on reveal).
Use "none" as the accepted Landing answer when the result is dropped.
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd


@dataclass
class Drill:
    id: str
    domain: str                      # "python" | "pandas" | "sklearn"
    intent: str
    setup: Callable[[], dict]        # fresh starting namespace
    effect: str                      # "rebind" | "mutate" | "emit"
    grammar: dict                    # slot -> list of accepted answers
    reference_line: str
    verify: Callable[[dict, dict, str, Any], bool]  # (before, after, stdout, ret) -> bool
    target: Optional[str] = None     # name whose identity must survive a mutate


def _sklearn_env():
    from sklearn.linear_model import LogisticRegression
    rng = np.random.RandomState(0)
    X = rng.randn(100, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    model = LogisticRegression().fit(X[:80], y[:80])
    return {"model": model, "X_test": X[80:], "y_test": y[80:]}


def _emitted_equals(stdout, ret, expected):
    return stdout.strip() == str(expected) or (ret is not None and ret == expected)


DRILLS = [
    Drill(
        id="py-append",
        domain="python",
        intent="Append the integer 95 to the end of scores, in place.",
        setup=lambda: {"scores": [72, 88, 91]},
        effect="mutate",
        grammar={
            "subject": ["scores"],
            "verb": [".append", "append"],
            "details": ["95"],
            "landing": ["none", "dropped"],
        },
        reference_line="scores.append(95)",
        verify=lambda b, a, out, ret: a.get("scores") == [72, 88, 91, 95],
        target="scores",
    ),
    Drill(
        id="pd-dropna",
        domain="pandas",
        intent="Remove rows from df where 'price' is missing; assign the result to clean_df.",
        setup=lambda: {"df": pd.DataFrame(
            {"item": ["a", "b", "c"], "price": [10.0, np.nan, 30.0]})},
        effect="rebind",
        grammar={
            "subject": ["df"],
            "verb": [".dropna", "dropna"],
            "details": ["subset=['price']"],
            "landing": ["clean_df"],
        },
        reference_line="clean_df = df.dropna(subset=['price'])",
        verify=lambda b, a, out, ret: (
            "clean_df" in a
            and isinstance(a["clean_df"], pd.DataFrame)
            and list(a["clean_df"]["item"]) == ["a", "c"]
            and len(a["df"]) == 3
        ),
    ),
    Drill(
        id="sk-score",
        domain="sklearn",
        intent="Output the mean accuracy of model on X_test and y_test without saving it to a variable.",
        setup=_sklearn_env,
        effect="emit",
        grammar={
            "subject": ["model"],
            "verb": [".score", "score"],
            "details": ["X_test, y_test"],
            "landing": ["print", "print(...)", "stdout", "output"],
        },
        reference_line="print(model.score(X_test, y_test))",
        verify=lambda b, a, out, ret: (
            set(a) == set(b)
            and _emitted_equals(out, ret, a["model"].score(a["X_test"], a["y_test"]))
        ),
    ),
]
