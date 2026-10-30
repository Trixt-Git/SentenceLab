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
        id="sentence", title="A line of Python is a sentence", effect="sentence",
        before="py-title",
        setup=lambda: {"name": "ada", "scores": [72, 88, 91, 88]},
        teach=dict(
            points=["Every line you will write here is a short sentence with four parts.",
                    "Subject: what it works on. Here, name.",
                    "Verb: what it does. Here, .upper (make it uppercase).",
                    "Details: extra information the verb needs. Here, none.",
                    "Landing: where the result goes, usually a name on the left of =. Here, shout.",
                    "Some lines leave a part out, but the shape stays the same."],
            example="shout = name.upper()",
            slots={"Subject": "name", "Verb": ".upper", "Details": "none", "Landing": "shout"},
            rule="Landing = Subject.Verb(Details)"),
        worked=dict(
            line="count = scores.count(88)",
            slots={"Subject": "scores", "Verb": ".count", "Details": "88", "Landing": "count"},
            why="Which part is the extra information the verb needs?",
            options=["88", "scores", "count", ".count"], answer=0),
        contrast=dict(
            a="shout = name.upper()", b="name.upper()",
            question="What does line B leave out?",
            options=["the Landing: nothing stores the result", "the Subject", "the Verb",
                     "the Details"], answer=0,
            explain="Both lines do the same work. B has no Landing, so the result is shown "
                    "(in a notebook) and then lost. A stores it as shout."),
        predict=dict(
            line="pos = scores.index(91)",
            question="Which part is the Landing?",
            options=["pos", "scores", ".index", "91"], answer=0),
        faded=[dict(template="shout = ___.upper()", answers=[["name"]]),
               dict(template="___ = ___.upper()", answers=[["<name>"], ["name"]])],
    ),
    Lesson(
        id="landing", title="The Landing: where does the result go?", effect="landing",
        before="py-append",
        setup=lambda: {"nums": [3, 1, 2]},
        teach=dict(
            points=["The Landing answers one question: where does the result go?",
                    "Stored: ranked = sorted(nums) gives the result a name.",
                    "Nowhere: nums.sort() changes nums itself, so there is no separate result to store.",
                    "Shown: print(sum(nums)) sends the result to the screen.",
                    "The drills call these Rebind, Mutate and Emit. Step 1 asks which one a line is."],
            example="ranked = sorted(nums)",
            slots={"Subject": "nums", "Verb": "sorted", "Details": "none", "Landing": "ranked"},
            rule="Ask first: is the result stored, changed in place, or shown?"),
        worked=dict(
            line="nums.sort()",
            slots={"Subject": "nums", "Verb": ".sort", "Details": "none", "Landing": "none"},
            why="Why is the Landing empty?",
            options=["The verb changes nums itself, so there is nothing separate to store",
                     "sort is slow", "Lists cannot be stored", "Because nums is short"],
            answer=0),
        contrast=dict(
            a="ranked = sorted(nums)", b="nums.sort()",
            question="Which line leaves nums as it was?",
            options=["the first", "the second", "both", "neither"], answer=0,
            explain="sorted builds a new sorted list and stores it as ranked, so nums is "
                    "untouched. sort() reorders nums itself and stores nothing."),
        predict=dict(
            line="print(len(nums))",
            question="Where does the result go?",
            options=["stored under a name", "nowhere: the verb changes nums",
                     "to the screen", "it is lost"], answer=2),
        faded=[dict(template="___ = sorted(nums)", answers=[["<name>"]]),
               dict(template="ranked = ___(nums)", answers=[["sorted"]])],
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
            explain="dropna builds a new table and leaves df alone. Only the second line has a Landing "
                    "(df =), so only there does df lose the row. Prefer this to inplace=True, "
                    "which is harder to predict."),
        teach=dict(
            points=['Same four parts as before. The Subject is now a DataFrame (df).', 'Most pandas verbs build a new table instead of changing df. That new table is the result, so it needs a Landing.', "Details can be named options: subset=['price'] says which column to check."],
            example="clean_df = df.dropna(subset=['price'])",
            rule='A pandas verb builds a new table: give it a Landing.'),
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
            explain="fit teaches the model and hands the same model back, so model is fitted after "
                    "either line. The point: fit changes its Subject, so it needs no Landing."),
        teach=dict(
            points=['scikit-learn has three kinds of verbs: fit, predict and transform.', 'fit teaches the model. The model is the Subject and the data it learns from is the Details (X_train, y_train).', 'fit changes the model itself, so there is no separate result and the Landing is empty. You can see it worked: the model goes from not fitted to fitted.'],
            example='model.fit(X_train, y_train)',
            rule='fit changes its Subject: the Landing is empty.'),
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
            explain="predict builds a new result and leaves the model alone. Without a Landing "
                    "the predictions are shown once and then lost."),
        teach=dict(
            points=['predict is the second kind of verb: it reads the model and builds a new result, the predictions.', 'A new result needs a Landing: preds = model.predict(X_test).', 'The Details are just the data to predict on, X_test.'],
            example='preds = model.predict(X_test)',
            rule='predict builds a new result: give it a Landing.'),
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
            explain="fit_transform makes the scaler learn again from whatever you give it. On test "
                    "data that mixes the test set into what the scaler learned."),
        teach=dict(
            points=['transform is the third kind of verb. The Subject is a scaler that already learned numbers from the training data.', 'scaler.transform(X_test) applies those numbers and builds a new result, so it needs a Landing.', 'fit_transform would first learn again from X_test, which mixes test data into the scaler. Fit on training data, only transform test data.'],
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
            explain="nums.sort() reorders nums itself and produces no result (None). ranked = then "
                    "stores that nothing, so ranked is None while nums is sorted. sorted(nums) "
                    "builds a new list, and ranked stores it."),
        teach=dict(
            points=["Reading someone else's line uses the same four parts, found in a different order.", 'Start at the Landing, the left of =: is a result stored there, or not?', 'Then look at the Verb: does it change its Subject, or build something new? A mismatch is the classic bug.'],
            example='ranked = sorted(nums)',
            rule='Read the Landing first, then the Verb.'),
        worked=dict(
            line="ranked = nums.sort()",
            slots={"Subject": "nums", "Verb": ".sort", "Details": "none", "Landing": "ranked"},
            why="What is wrong with this line?",
            options=["sort changes nums and produces no result, so ranked holds None",
                     "sort needs arguments", "ranked cannot be assigned",
                     "nums is left unchanged"], answer=0),
        faded=[dict(template="ranked = ___.sort()", answers=[["nums"]]),
               dict(template="___ = ___.sort()", answers=[["<name>"], ["nums"]])],
    ),
]

BY_ID = {l.id: l for l in LESSONS}
