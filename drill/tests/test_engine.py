import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from drills import DRILLS
from engine import check_slots, run_line

D = {d.id: d for d in DRILLS}


@pytest.mark.parametrize("d", DRILLS, ids=lambda d: d.id)
def test_reference_line_passes(d):
    assert run_line(d, d.reference_line)["passed"]


def test_mutate_rebind_to_none_fails():
    r = run_line(D["py-append"], "scores = scores.append(95)")
    assert not r["passed"] and any("holds None" in h for h in r["hints"])


def test_quote_style_irrelevant():
    assert run_line(D["pd-dropna"], 'clean_df = df.dropna(subset=["price"])')["passed"]


def test_rebind_without_variable_fails():
    assert not run_line(D["pd-dropna"], "df.dropna(subset=['price'])")["passed"]


def test_emit_bare_expression_jupyter_style():
    assert run_line(D["sk-score"], "model.score(X_test, y_test)")["passed"]


def test_emit_binding_fails():
    assert not run_line(D["sk-score"], "acc = model.score(X_test, y_test)")["passed"]


def test_multiple_statements_rejected():
    r = run_line(D["py-append"], "scores.append(95); scores.append(1)")
    assert r["error"] and not r["passed"]


def test_slots():
    ok = check_slots(D["py-append"], {"subject": "scores", "verb": ".append",
                                      "details": "95", "variable": "None"})
    assert all(ok.values())
    assert not check_slots(D["py-append"], {"subject": "x"})["subject"]


def test_scaler_refit_fails():
    r = run_line(D["sk-transform"], "X_test_s = scaler.fit_transform(X_test)")
    assert not r["passed"]


def test_pandas_inplace_not_a_rebind():
    assert not run_line(D["pd-reassign"], "df.dropna(subset=['price'], inplace=True)")["passed"]


def test_sorted_vs_sort():
    assert not run_line(D["py-sorted"], "nums.sort()")["passed"]
    assert not run_line(D["py-sort"], "nums = sorted(nums)")["passed"]


def test_diff_notes():
    r = run_line(D["py-append"], "scores = scores.append(95)")
    assert r["diff"][0]["note"] == "scores now refers to a different object"


def test_fit_shows_in_state_diff():
    r = run_line(D["sk-fit"], "model.fit(X_train, y_train)")
    row = r["diff"][0]
    assert row["name"] == "model" and "not fitted" in row["before"] and "fitted" in row["after"]


def test_scaler_refit_visible_in_diff():
    r = run_line(D["sk-transform"], "X_test_s = scaler.fit_transform(X_test)")
    assert any(row["name"] == "scaler" and row["change"] == "mutated" for row in r["diff"])
