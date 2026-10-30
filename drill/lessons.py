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
        id="sentence", title="Every line of Python is a short sentence", effect="sentence",
        before="py-title",
        setup=lambda: {"name": "ada", "scores": [72, 88, 91, 88]},
        teach=dict(
            points=["Each line you write works like a short sentence, and a sentence has up to four parts.",
                    "The [[subject|subject]] is the thing the line works on. In the line below, the [[subject|subject]] is [[subject|name]].",
                    "The [[verb|verb]] is what the line does to the [[subject|subject]]. Here, [[verb|.upper]] makes the text uppercase.",
                    "The [[details|details]] are anything extra the [[verb|verb]] needs. .upper needs nothing extra, so there are no [[details|details]].",
                    "The [[variable|variable]] is where the answer is saved. It is the name on the left of the =, which is [[variable|shout]] here.",
                    "Some lines skip a part, and that is fine."],
            example="shout = name.upper()",
            slots={"Subject": "name", "Verb": ".upper", "Details": "none", "Variable": "shout"},
            rule="Every line follows this pattern: variable = subject.verb(details)."),
        worked=dict(
            line="count = scores.count(88)",
            slots={"Subject": "scores", "Verb": ".count", "Details": "88", "Variable": "count"},
            why="Which part of this line is the extra information the verb needs?",
            options=["88", "scores", "count", ".count"], answer=0),
        contrast=dict(
            a="shout = name.upper()", b="name.upper()",
            question="What does line B leave out?",
            options=["The variable, so the answer is not saved anywhere", "The subject",
                     "The verb", "The details"], answer=0,
            explain="Both lines do the same work, but line B has no variable. Its answer is shown "
                    "once and then lost. Line A saves it as shout."),
        predict=dict(
            line="pos = scores.index(91)",
            question="Which part of this line is the variable?",
            options=["pos", "scores", ".index", "91"], answer=0),
        faded=[dict(template="shout = ___.upper()", answers=[["name"]]),
               dict(template="___ = ___.upper()", answers=[["<name>"], ["name"]])],
    ),
    Lesson(
        id="saved", title="What happens to the answer?", effect="saved",
        before="py-title",
        setup=lambda: {"nums": [3, 1, 2]},
        teach=dict(
            points=["After a line runs, one of three things can happen.",
                    "First, its answer can be saved in a [[variable|variable]]. For example, [[variable|ranked]] = [[verb|sorted]]([[subject|nums]]) saves a sorted copy of the list as [[variable|ranked]].",
                    "Second, the line can change the thing itself, so there is no separate answer to save. For example, [[subject|nums]][[verb|.sort]]() reorders nums directly.",
                    "Third, its answer can simply be shown on screen. For example, print([[verb|sum]]([[subject|nums]])) displays the total without saving it.",
                    "Step 1 of every exercise asks which of these three a line does."],
            example="ranked = sorted(nums)",
            slots={"Subject": "nums", "Verb": "sorted", "Details": "none", "Variable": "ranked"},
            rule="Before you write a line, decide whether its answer will be saved, changed in place, or only shown."),
        worked=dict(
            line="nums.sort()",
            slots={"Subject": "nums", "Verb": ".sort", "Details": "none", "Variable": "none"},
            why="Why is the variable empty in this line?",
            options=["The verb changes nums directly, so there is no separate answer to save",
                     "Because sort is slow", "Because lists cannot be saved",
                     "Because nums is short"], answer=0),
        contrast=dict(
            a="ranked = sorted(nums)", b="nums.sort()",
            question="Which line leaves nums as it was?",
            options=["The first one", "The second one", "Both", "Neither"], answer=0,
            explain="sorted(nums) builds a new sorted list and saves it as ranked, so nums is "
                    "untouched. nums.sort() reorders nums itself and saves nothing."),
        predict=dict(
            line="print(len(nums))",
            question="Where does the answer to this line go?",
            options=["It is saved in a variable", "It changes nums", "It is shown on screen",
                     "It is lost"], answer=2),
        faded=[dict(template="___ = sorted(nums)", answers=[["<name>"]]),
               dict(template="ranked = ___(nums)", answers=[["sorted"]])],
    ),
    Lesson(
        id="pandas", title="pandas builds a new table", effect="rebind",
        before="pd-dropna",
        setup=_price_df,
        teach=dict(
            points=["This works just like before, except that the [[subject|subject]] is now a table, [[subject|df]].",
                    "Most pandas [[verb|verbs]] build a new table and leave df alone. The new table is the answer, so it needs a [[variable|variable]] to be saved in.",
                    "The [[details|details]] can be named options. Here, [[details|subset=['price']]] tells [[verb|dropna]] which column to check."],
            example="clean_df = df.dropna(subset=['price'])",
            rule="A pandas verb builds a new table, so save it in a variable."),
        worked=dict(
            line="clean_df = df.dropna(subset=['price'])",
            slots={"Subject": "df", "Verb": ".dropna", "Details": "subset=['price']",
                   "Variable": "clean_df"},
            why="Why does this line need a variable?",
            options=["dropna builds a new table, and the table is lost unless you save it",
                     "dropna edits df directly", "A variable is optional for every method",
                     "pandas does not allow reusing df"], answer=0),
        contrast=dict(
            a="df.dropna(subset=['price'])", b="df = df.dropna(subset=['price'])",
            question="In which line does df lose the row with the missing price?",
            options=["The first one", "The second one", "Both", "Neither"], answer=1,
            explain="dropna builds a new table and leaves df alone. Only the second line saves "
                    "the new table back into df, so only there does df lose the row. You can "
                    "also use inplace=True, but it is harder to predict, so we avoid it."),
        predict=dict(
            line="df.dropna(subset=['price'])",
            question="After this line runs, how many rows does df have?",
            options=["2", "3", "0", "It causes an error"], answer=1),
        faded=[dict(template="clean_df = df.___(subset=['price'])",
                    answers=[["dropna", ".dropna"]]),
               dict(template="___ = df.___(subset=['price'])",
                    answers=[["<name>"], ["dropna", ".dropna"]])],
    ),
    Lesson(
        id="sk-fit", title="fit trains the model", effect="mutate",
        before="sk-fit",
        setup=_unfitted_env,
        teach=dict(
            points=["scikit-learn has three main [[verb|verbs]]: fit, predict and transform.",
                    "fit trains the model. The [[subject|model]] is the [[subject|subject]], and the data it learns from is the [[details|details]]: [[details|X_train and y_train]].",
                    "fit changes the model directly, so there is no separate answer to save and the [[variable|variable]] is empty. You can see that it worked because the model goes from not fitted to fitted."],
            example="model.fit(X_train, y_train)",
            rule="fit changes the model itself, so it does not need a variable."),
        worked=dict(
            line="model.fit(X_train, y_train)",
            slots={"Subject": "model", "Verb": ".fit", "Details": "X_train, y_train",
                   "Variable": "none"},
            why="Why does fit not need a variable?",
            options=["The model itself holds what it learned",
                     "fit returns the accuracy", "scikit-learn never needs variables",
                     "X_train gets overwritten"], answer=0),
        contrast=dict(
            a="model.fit(X_train, y_train)", b="fitted = model.fit(X_train, y_train)",
            question="After line B, which names hold a fitted model?",
            options=["Only fitted", "Both model and fitted, because they are the same object",
                     "Neither", "Only model"], answer=1,
            explain="fit trains the model and hands that same model back, so model is fitted "
                    "after either line. The main point is that fit changes its subject, so it "
                    "does not need a variable."),
        predict=dict(
            line="model.fit(X_train, y_train)",
            question="After this line runs, what has changed?",
            options=["The model has learned from the data", "X_train has been scaled",
                     "A new fitted model was made and the old one is untouched",
                     "Nothing, because fit only checks the data"], answer=0),
        faded=[dict(template="model.___(X_train, y_train)", answers=[["fit", ".fit"]]),
               dict(template="___.___(X_train, y_train)",
                    answers=[["model"], ["fit", ".fit"]])],
    ),
    Lesson(
        id="sk-predict", title="predict gives you answers", effect="rebind",
        before="sk-predict",
        setup=_sklearn_env,
        teach=dict(
            points=["predict is the second [[verb|verb]]. It reads the model and builds a new result: the predictions.",
                    "A new result needs a [[variable|variable]], so you write [[variable|preds]] = [[subject|model]][[verb|.predict]]([[details|X_test]]).",
                    "The [[details|details]] are just the data to predict on, which is [[details|X_test]]."],
            example="preds = model.predict(X_test)",
            rule="predict makes something new, so save it in a variable."),
        worked=dict(
            line="preds = model.predict(X_test)",
            slots={"Subject": "model", "Verb": ".predict", "Details": "X_test",
                   "Variable": "preds"},
            why="Why does predict need a variable when fit does not?",
            options=["predict makes a new result, while fit changes the model itself",
                     "predict is slower", "fit gives nothing back at all",
                     "They work the same way"], answer=0),
        contrast=dict(
            a="preds = model.predict(X_test)", b="model.predict(X_test)",
            question="Which line keeps the predictions?",
            options=["The first one", "The second one", "Both", "Neither"], answer=0,
            explain="predict builds a new result and leaves the model alone. Without a "
                    "variable, the predictions are shown once and then lost."),
        predict=dict(
            line="preds = model.predict(X_test)",
            question="After this line runs, what happened to model?",
            options=["Nothing: model is unchanged, and preds holds the new answers",
                     "The model was trained again", "model became preds",
                     "X_test was overwritten"], answer=0),
        faded=[dict(template="preds = model.___(X_test)",
                    answers=[["predict", ".predict"]]),
               dict(template="___ = model.___(X_test)",
                    answers=[["<name>"], ["predict", ".predict"]])],
    ),
    Lesson(
        id="sk-transform", title="transform rescales new data", effect="rebind",
        before="sk-transform",
        setup=_scaler_env,
        teach=dict(
            points=["transform is the third [[verb|verb]]. Its [[subject|subject]] is a scaler that has already learned some numbers from the training data.",
                    "[[subject|scaler]][[verb|.transform]]([[details|X_test]]) applies those numbers to new data and builds a new result, so it needs a [[variable|variable]].",
                    "fit_transform would learn from X_test all over again, which mixes the test data into the scaler. So fit on the training data, and only transform the test data."],
            example="X_test_s = scaler.transform(X_test)",
            rule="Fit on the training data, and only transform the test data."),
        worked=dict(
            line="X_test_s = scaler.transform(X_test)",
            slots={"Subject": "scaler", "Verb": ".transform", "Details": "X_test",
                   "Variable": "X_test_s"},
            why="Why use transform and not fit_transform here?",
            options=["The scaler already learned from the training data, and the test data should not change that",
                     "transform is faster", "fit_transform does not exist",
                     "They give the same result"], answer=0),
        contrast=dict(
            a="X_test_s = scaler.transform(X_test)",
            b="X_test_s = scaler.fit_transform(X_test)",
            question="Which line changes what the scaler learned?",
            options=["The first one", "The second one", "Both", "Neither"], answer=1,
            explain="fit_transform makes the scaler learn again from whatever you give it. "
                    "With test data, that mixes the test set into what the scaler knows."),
        predict=dict(
            line="X_test_s = scaler.transform(X_test)",
            question="After this line runs, has the scaler changed?",
            options=["No, transform only applies what the scaler already learned",
                     "Yes, it learns again from X_test", "Yes, it gets reset",
                     "X_test gets scaled in place"], answer=0),
        faded=[dict(template="X_test_s = scaler.___(X_test)",
                    answers=[["transform", ".transform"]]),
               dict(template="___ = scaler.___(X_test)",
                    answers=[["<name>"], ["transform", ".transform"]])],
    ),
    Lesson(
        id="read", title="What does this line do?", effect="rebind",
        before="explain",
        setup=lambda: {"nums": [3, 1, 2]},
        teach=dict(
            points=["Sometimes you will be given a line and asked what it does.",
                    "Start with the left side of the =. Is the answer saved in a [[variable|variable]]?",
                    "Then look at the [[verb|verb]]. Does it change the thing it is called on, or does it make something new?",
                    "A common mistake is saving the answer of a [[verb|verb]] that changes things in place. For example, ranked = nums.sort() saves nothing useful."],
            example="ranked = sorted(nums)",
            rule="Check the left side of the = first, then the verb."),
        worked=dict(
            line="ranked = nums.sort()",
            slots={"Subject": "nums", "Verb": ".sort", "Details": "none", "Variable": "ranked"},
            why="What is wrong with this line?",
            options=["sort changes nums and gives back nothing, so ranked holds None",
                     "sort needs extra details", "ranked cannot be assigned",
                     "nums stays unchanged"], answer=0),
        contrast=dict(
            a="ranked = sorted(nums)", b="ranked = nums.sort()",
            question="Which line puts the sorted list in ranked?",
            options=["The first one", "The second one", "Both", "Neither"], answer=0,
            explain="nums.sort() reorders nums itself and gives back nothing, which Python "
                    "calls None. So ranked = nums.sort() saves None, while nums ends up sorted. "
                    "sorted(nums) builds a new list, and ranked saves it."),
        predict=dict(
            line="ranked = nums.sort()",
            question="After this line runs, what is ranked?",
            options=["[1, 2, 3]", "[3, 1, 2]", "None", "An error"], answer=2),
        faded=[dict(template="ranked = ___.sort()", answers=[["nums"]]),
               dict(template="___ = ___.sort()", answers=[["<name>"], ["nums"]])],
    ),
]

BY_ID = {l.id: l for l in LESSONS}
