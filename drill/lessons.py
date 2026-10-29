"""Short lessons shown before the drills they support.

Stage order (teach first, then check, then fade support):
  teach -> labelled worked example -> contrast pair -> predict -> faded x2
Contrast pairs and predictions are executed live against a real namespace, so the
state diff shown is what Python actually did.
"""
from dataclasses import dataclass, field
from typing import Callable

from drills import _price_df, _scaler_env, _sklearn_env, _unfitted_env


@dataclass
class Lesson:
    id: str
    title: str
    effect: str
    before: str                      # drill id this lesson precedes, or "explain"
    setup: Callable[[], dict]
    predict: dict                    # {line, question, options, answer}
    contrast: dict                   # {a, b, question, options, answer, explain}
    teach: dict                      # {points, example, rule}: shown first, before any question
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
        teach=dict(
            points=['Some operations change an object in place. The name stays attached to the same object; only its contents change.', 'Methods like .append, .sort and .fit work this way. They give back None (or the object itself), not a new result.', 'So there is nothing to catch: no assignment, and the Landing is empty.'],
            example='scores.append(95)',
            rule='Mutate: same object, changed in place. Landing: none.'),
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
        teach=dict(
            points=['Some operations build a new object and leave the original alone.', 'sorted(nums) returns a new list. If nothing catches it, it is thrown away.', 'A name on the left of = catches it. That name is the Landing.'],
            example='ranked = sorted(nums)',
            rule='Rebind: a new object must land in a name.'),
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
        teach=dict(
            points=['Most pandas methods return a new DataFrame and leave the original unchanged.', 'df.dropna(...) on its own only displays the result; df keeps all its rows.', 'Catch the result: use a new name (clean_df = ...) or reuse the old one (df = ...). Avoid inplace=True, whose behaviour is harder to predict.'],
            example="clean_df = df.dropna(subset=['price'])",
            rule='pandas returns a new DataFrame: give it a name.'),
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
        teach=dict(
            points=['Sometimes you only want to look at a value, not keep it.', 'print(...) shows a value and changes nothing. In a notebook, a bare expression does the same.', 'The Landing is the screen (print / output), not a variable.'],
            example='print(sum(scores))',
            rule='Emit: show a value, change no state.'),
        worked=dict(
            line="print(sum(scores))",
            slots={"Subject": "scores", "Verb": "sum", "Details": "none", "Landing": "print"},
            why="Why is Landing print rather than a variable?",
            options=["The goal is to see the value, not keep it", "print is faster",
                     "Variables cannot hold sums", "sum() requires print"], answer=0),
        faded=[dict(template="print(___(scores))", answers=[["sum"]]),
               dict(template="___(___(scores))", answers=[["print"], ["sum"]])],
    ),
    Lesson(
        id="sk-fit", title="scikit-learn: fit trains the model in place", effect="mutate",
        before="sk-fit",
        setup=_unfitted_env,
        predict=dict(
            line="model.fit(X_train, y_train)",
            question="After this line runs, what has changed?",
            options=["model has learned from the data, in place",
                     "X_train has been scaled",
                     "a new fitted model is returned and model is untouched",
                     "nothing: fit only checks the data"], answer=0),
        contrast=dict(
            a="model.fit(X_train, y_train)", b="fitted = model.fit(X_train, y_train)",
            question="After line B, which names are fitted models?",
            options=["only fitted", "both model and fitted (the same object)",
                     "neither", "only model"], answer=1,
            explain="fit trains the estimator in place and returns the same object. "
                    "Unlike list.append it does not return None, but the habit that "
                    "matters is the same: the model object itself holds what it learned."),
        teach=dict(
            points=['scikit-learn methods come in three kinds: fit trains, predict and transform return new arrays.', 'fit changes the model object itself: what it learned is stored inside it.', 'It returns the same object, so you do not need to assign it. The change to look for is the model going from not fitted to fitted.'],
            example='model.fit(X_train, y_train)',
            rule='fit mutates the model: no Landing needed.'),
        worked=dict(
            line="model.fit(X_train, y_train)",
            slots={"Subject": "model", "Verb": ".fit", "Details": "X_train, y_train",
                   "Landing": "none"},
            why="Why does fit need no Landing?",
            options=["The model object itself holds what it learned",
                     "fit returns the accuracy", "Landing is never needed in sklearn",
                     "X_train is overwritten"], answer=0),
        faded=[dict(template="model.___(X_train, y_train)", answers=[["fit", ".fit"]]),
               dict(template="___.___(X_train, y_train)",
                    answers=[["model"], ["fit", ".fit"]])],
    ),
    Lesson(
        id="sk-predict", title="scikit-learn: predict returns a new array", effect="rebind",
        before="sk-predict",
        setup=_sklearn_env,
        predict=dict(
            line="preds = model.predict(X_test)",
            question="After this line runs, what happened to model?",
            options=["nothing: model is unchanged and preds holds a new array",
                     "model was refitted", "model became preds",
                     "X_test was overwritten"], answer=0),
        contrast=dict(
            a="preds = model.predict(X_test)", b="model.predict(X_test)",
            question="Which line keeps the predictions?",
            options=["the first", "the second", "both", "neither"], answer=0,
            explain="predict returns a new array and leaves the model unchanged. With no "
                    "name to land in, the predictions are shown once and then lost."),
        teach=dict(
            points=['predict reads the model and returns a new array of labels. The model is unchanged.', 'The array must land in a name, or it is shown once and lost.', 'Rule of thumb: if a method gives you data back, give it a name.'],
            example='preds = model.predict(X_test)',
            rule='predict returns a new array: give it a name.'),
        worked=dict(
            line="preds = model.predict(X_test)",
            slots={"Subject": "model", "Verb": ".predict", "Details": "X_test",
                   "Landing": "preds"},
            why="Why does predict need a Landing when fit does not?",
            options=["predict returns a new array; fit changes the model itself",
                     "predict is slower", "fit returns nothing at all",
                     "they work the same way"], answer=0),
        faded=[dict(template="preds = model.___(X_test)",
                    answers=[["predict", ".predict"]]),
               dict(template="___ = model.___(X_test)",
                    answers=[["<name>"], ["predict", ".predict"]])],
    ),
    Lesson(
        id="sk-transform", title="scikit-learn: transform reuses what was learned",
        effect="rebind", before="sk-transform",
        setup=_scaler_env,
        predict=dict(
            line="X_test_s = scaler.transform(X_test)",
            question="After this line runs, has the scaler changed?",
            options=["no: transform only applies what it already learned",
                     "yes: it relearns from X_test", "yes: it is reset",
                     "X_test is scaled in place"], answer=0),
        contrast=dict(
            a="X_test_s = scaler.transform(X_test)",
            b="X_test_s = scaler.fit_transform(X_test)",
            question="Which line changes what the scaler learned?",
            options=["the first", "the second", "both", "neither"], answer=1,
            explain="fit_transform refits the scaler on whatever it is given. On test data "
                    "that leaks information about the test set. Fit on training data, then "
                    "only transform test data."),
        teach=dict(
            points=['A fitted scaler stores what it learned from the training data.', 'transform applies that stored knowledge to new data and returns a new array. The scaler is unchanged.', 'fit_transform refits first. On test data that leaks information about the test set, so use transform.'],
            example='X_test_s = scaler.transform(X_test)',
            rule='Fit on training data. Only transform test data.'),
        worked=dict(
            line="X_test_s = scaler.transform(X_test)",
            slots={"Subject": "scaler", "Verb": ".transform", "Details": "X_test",
                   "Landing": "X_test_s"},
            why="Why transform and not fit_transform here?",
            options=["the scaler already learned from training data; test data must not change it",
                     "transform is faster", "fit_transform does not exist",
                     "they give identical results and state"], answer=0),
        faded=[dict(template="X_test_s = scaler.___(X_test)",
                    answers=[["transform", ".transform"]]),
               dict(template="___ = scaler.___(X_test)",
                    answers=[["<name>"], ["transform", ".transform"]])],
    ),
    Lesson(
        id="read", title="Reading a line you did not write", effect="rebind",
        before="explain",
        setup=lambda: {"nums": [3, 1, 2]},
        predict=dict(
            line="ranked = nums.sort()",
            question="After this line runs, what is ranked?",
            options=["[1, 2, 3]", "[3, 1, 2]", "None", "an error"], answer=2),
        contrast=dict(
            a="ranked = sorted(nums)", b="ranked = nums.sort()",
            question="Which line puts the sorted list in ranked?",
            options=["the first", "the second", "both", "neither"], answer=0,
            explain="To read a line, check the Landing first: what catches the result, "
                    "and can that verb return something? sort() returns None, so ranked "
                    "catches None while nums is sorted in place."),
        teach=dict(
            points=['When you read a line someone else wrote, check the Landing first: what catches the result?', 'Then ask whether the verb mutates (and returns None) or returns a new object.', 'The classic bug is a mutating verb whose None gets caught by a name.'],
            example='ranked = sorted(nums)',
            rule='Read the Landing first, then the verb.'),
        worked=dict(
            line="ranked = nums.sort()",
            slots={"Subject": "nums", "Verb": ".sort", "Details": "none", "Landing": "ranked"},
            why="What is wrong with this line?",
            options=["sort returns None, so ranked holds None while nums is sorted in place",
                     "sort needs arguments", "ranked cannot be assigned",
                     "nums is left unchanged"], answer=0),
        faded=[dict(template="ranked = ___.sort()", answers=[["nums"]]),
               dict(template="___ = ___.sort()", answers=[["<name>"], ["nums"]])],
    ),
]

BY_ID = {l.id: l for l in LESSONS}
