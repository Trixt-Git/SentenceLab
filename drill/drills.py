"""Drill definitions. One grammatical clause per drill.

grammar values are lists of accepted answers (first one is shown on reveal).
Use "none" as the accepted variable answer when nothing is saved.
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
    plan: str = ""                   # reusable code fragment this drill practices


def _sklearn_env():
    from sklearn.linear_model import LogisticRegression
    rng = np.random.RandomState(0)
    X = rng.randn(100, 4)
    y = (X[:, 0] + X[:, 1] + rng.randn(100) * 0.8 > 0).astype(int)
    model = LogisticRegression().fit(X[:80], y[:80])
    return {"model": model, "X_test": X[80:], "y_test": y[80:]}


def _emitted_equals(stdout, ret, expected):
    if isinstance(expected, pd.DataFrame):
        return stdout.strip() == str(expected).strip() or (
            isinstance(ret, pd.DataFrame) and ret.equals(expected))
    return stdout.strip() == str(expected) or (ret is not None and ret == expected)


def _sk_data():
    rng = np.random.RandomState(0)
    X = rng.randn(100, 4)
    y = (X[:, 0] + X[:, 1] + rng.randn(100) * 0.8 > 0).astype(int)
    return X[:80], y[:80], X[80:], y[80:]


def _unfitted_env():
    from sklearn.linear_model import LogisticRegression
    X_train, y_train, _, _ = _sk_data()
    return {"model": LogisticRegression(), "X_train": X_train, "y_train": y_train}


def _scaler_env():
    from sklearn.preprocessing import StandardScaler
    X_train, _, X_test, _ = _sk_data()
    return {"scaler": StandardScaler().fit(X_train), "X_test": X_test}


def _price_df():
    return {"df": pd.DataFrame({"item": ["a", "b", "c"], "price": [10.0, np.nan, 30.0]})}


SHOWN = ["none", "print", "print(...)", "stdout", "output", "display", "screen"]
NONE = ["none", "nothing"]

DRILLS = [
    Drill(
        id="py-title", domain="python", plan="text",
        intent="Turn name into title case, so that 'ada lovelace' becomes 'Ada Lovelace', and save it as title.",
        setup=lambda: {"name": "ada lovelace"},
        effect="rebind",
        grammar={"subject": ["name"], "verb": [".title", "title"],
                 "details": NONE, "variable": ["title"]},
        reference_line="title = name.title()",
        verify=lambda b, a, out, ret: a.get("title") == "Ada Lovelace" and a["name"] == "ada lovelace",
    ),
    Drill(
        id="py-sum", domain="python", plan="total",
        intent="Add up the numbers in scores and save the answer as total.",
        setup=lambda: {"scores": [72, 88, 91]},
        effect="rebind",
        grammar={"subject": ["scores"], "verb": ["sum"], "details": NONE, "variable": ["total"]},
        reference_line="total = sum(scores)",
        verify=lambda b, a, out, ret: a.get("total") == 251,
    ),
    # ---- mutate ----
    Drill(
        id="py-append", domain="python", plan="add-item",
        intent="Add 95 to the end of the scores list itself.",
        setup=lambda: {"scores": [72, 88, 91]},
        effect="mutate",
        grammar={"subject": ["scores"], "verb": [".append", "append"],
                 "details": ["95"], "variable": ["none", "dropped"]},
        reference_line="scores.append(95)",
        verify=lambda b, a, out, ret: a.get("scores") == [72, 88, 91, 95],
        target="scores",
    ),
    Drill(
        id="py-sort", domain="python", plan="sort",
        intent="Sort the nums list itself, from smallest to largest.",
        setup=lambda: {"nums": [3, 1, 2]},
        effect="mutate",
        grammar={"subject": ["nums"], "verb": [".sort", "sort"],
                 "details": NONE, "variable": ["none", "dropped"]},
        reference_line="nums.sort()",
        verify=lambda b, a, out, ret: a.get("nums") == [1, 2, 3],
        target="nums",
    ),
    Drill(
        id="sk-fit", domain="sklearn", plan="train",
        intent="Train model on X_train and y_train.",
        setup=_unfitted_env,
        effect="mutate",
        grammar={"subject": ["model"], "verb": [".fit", "fit"],
                 "details": ["X_train, y_train"], "variable": ["none", "dropped"]},
        reference_line="model.fit(X_train, y_train)",
        verify=lambda b, a, out, ret: hasattr(a["model"], "coef_"),
        target="model",
    ),
    # ---- rebind ----
    Drill(
        id="py-sorted", domain="python", plan="sort",
        intent="Make a sorted copy of nums and save it as ranked, leaving nums as it was.",
        setup=lambda: {"nums": [3, 1, 2]},
        effect="rebind",
        grammar={"subject": ["nums"], "verb": ["sorted"],
                 "details": NONE, "variable": ["ranked"]},
        reference_line="ranked = sorted(nums)",
        verify=lambda b, a, out, ret: a.get("ranked") == [1, 2, 3] and a["nums"] == [3, 1, 2],
    ),
    Drill(
        id="pd-dropna", domain="pandas", plan="drop-missing",
        intent="Make a copy of df without the rows where price is missing, and save it as clean_df.",
        setup=_price_df,
        effect="rebind",
        grammar={"subject": ["df"], "verb": [".dropna", "dropna"],
                 "details": ["subset=['price']"], "variable": ["clean_df"]},
        reference_line="clean_df = df.dropna(subset=['price'])",
        verify=lambda b, a, out, ret: (
            isinstance(a.get("clean_df"), pd.DataFrame)
            and list(a["clean_df"]["item"]) == ["a", "c"] and len(a["df"]) == 3),
    ),
    Drill(
        id="pd-reassign", domain="pandas", plan="drop-missing",
        intent="Remove the rows where price is missing from df, and keep the name df.",
        setup=_price_df,
        effect="rebind",
        grammar={"subject": ["df"], "verb": [".dropna", "dropna"],
                 "details": ["subset=['price']"], "variable": ["df"]},
        reference_line="df = df.dropna(subset=['price'])",
        verify=lambda b, a, out, ret: list(a["df"]["item"]) == ["a", "c"],
    ),
    Drill(
        id="sk-predict", domain="sklearn", plan="predict",
        intent="Use model to predict the labels for X_test, and save them as preds.",
        setup=lambda: _sklearn_env(),
        effect="rebind",
        grammar={"subject": ["model"], "verb": [".predict", "predict"],
                 "details": ["X_test"], "variable": ["preds"]},
        reference_line="preds = model.predict(X_test)",
        verify=lambda b, a, out, ret: np.array_equal(
            a.get("preds"), a["model"].predict(a["X_test"])),
    ),
    Drill(
        id="sk-transform", domain="sklearn", plan="scale",
        intent="Scale X_test using scaler, which has already learned from the training data, without making it learn again. Save the result as X_test_s.",
        setup=_scaler_env,
        effect="rebind",
        grammar={"subject": ["scaler"], "verb": [".transform", "transform"],
                 "details": ["X_test"], "variable": ["X_test_s"]},
        reference_line="X_test_s = scaler.transform(X_test)",
        verify=lambda b, a, out, ret: (
            "X_test_s" in a
            and np.allclose(a["X_test_s"], a["scaler"].transform(a["X_test"]))
            and np.allclose(a["scaler"].mean_, b["scaler"].mean_)),
    ),
    # ---- emit ----
    Drill(
        id="pd-head", domain="pandas", plan="peek",
        intent="Show the first 2 rows of df without saving them.",
        setup=_price_df,
        effect="emit",
        grammar={"subject": ["df"], "verb": [".head", "head"],
                 "details": ["2"], "variable": SHOWN},
        reference_line="df.head(2)",
        verify=lambda b, a, out, ret: set(a) == set(b)
        and _emitted_equals(out, ret, a["df"].head(2)),
    ),
    Drill(
        id="sk-score", domain="sklearn", plan="evaluate",
        intent="Show how accurate model is on X_test and y_test, without saving the result.",
        setup=_sklearn_env,
        effect="emit",
        grammar={"subject": ["model"], "verb": [".score", "score"],
                 "details": ["X_test, y_test"], "variable": SHOWN},
        reference_line="print(model.score(X_test, y_test))",
        verify=lambda b, a, out, ret: set(a) == set(b)
        and _emitted_equals(out, ret, a["model"].score(a["X_test"], a["y_test"])),
    ),
]


_ORDER = ["py-title", "py-sum", "py-append", "py-sort", "py-sorted", "pd-dropna",
          "pd-reassign", "pd-head", "sk-fit", "sk-predict", "sk-transform", "sk-score"]
DRILLS.sort(key=lambda d: _ORDER.index(d.id))
