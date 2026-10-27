"""Regression suite for checker v2. Run: python3 -I test_checker.py <dir containing checker.py>"""
import sys, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, sys.argv[1])
from checker import check_all, validate, parts

PD1 = "import pandas as pd\ndf = pd.DataFrame({'category': ['a','b','a','c'], 'price': [10.0, None, 30.0, 5.0], 'qty': [3, 12, 20, 10]})"
PD2 = "import pandas as pd\ndf = pd.DataFrame({'category': ['x','y',None], 'price': [None, 2.5, 4.0], 'qty': [10, 11, 1]})"
PD = [PD1, PD2]
SKBASE = ("import numpy as np\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.linear_model import LinearRegression\n"
          "X = np.arange(20).reshape(10, 2)\nmodel = LinearRegression()\n")
SK1, SK2 = SKBASE + "y = np.arange(10) * 2.0", SKBASE + "y = np.arange(10) * 3.0 + 1"
SPLIT = "\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)"
SKS1, SKS2 = SK1 + SPLIT, SK2 + SPLIT
SKF1, SKF2 = SKS1 + "\nmodel.fit(X_train, y_train)", SKS2 + "\nmodel.fit(X_train, y_train)"
RF = SK1 + "\nfrom sklearn.ensemble import RandomForestRegressor\nrf = RandomForestRegressor(n_estimators=3, random_state=0)"
DT = SK1 + "\nfrom sklearn.tree import DecisionTreeRegressor\nt = DecisionTreeRegressor(random_state=0)"

# (id, setups, reference, answer, expected_correct)   expected None = judgement call, printed only
CASES = [
    # --- original v1 cases ---
    ("O1", ["fruits = ['apple', 'pear']", "fruits = []"], "fruits.append('kiwi')", "fruits += ['kiwi']", True),
    ("O2", ["fruits = ['apple', 'pear']"], "fruits.append('kiwi')", "fruits = fruits.append('kiwi')", False),
    ("O3", ["fruits = ['apple', 'pear']"], "fruits.append('kiwi')", "fruits = fruits + ['kiwi']", True),
    ("O4", ["scores = [3, 1, 2]"], "ranked = sorted(scores)", "ranked = scores.sort()", False),
    ("O5", ["ages = {'Ana': 31}"], "age = ages['Ana']", "age = ages.get('Ana')", True),
    ("O6", PD, "df = df.dropna(subset=['price'])", "df.dropna(subset=['price'])", False),
    ("O7", PD, "df = df.dropna(subset=['price'])", "df.dropna(subset=['price'], inplace=True)", True),
    ("O8", PD, "big = df[df['qty'] > 10]", "big = df[df.qty > 10]", True),
    ("O9", PD, "big = df[df['qty'] > 10]", "big = df[df['qty'] >= 10]", False),
    ("O10", PD, "avg = df.groupby('category')['price'].mean()", "avg = df.groupby('category').price.mean()", True),
    ("O11", PD, "avg = df.groupby('category')['price'].mean()", "avg = df.groupby('category')['prices'].mean()", False),
    ("O12", [SKS1], "model.fit(X_train, y_train)", "model = model.fit(X_train, y_train)", True),
    ("O13", [SKS1], "model.fit(X_train, y_train)", "model.predict(X_train)", False),
    ("O14", ["scores = [3, 1, 2]"], "ranked = sorted(scores)", "ranked = sorted(scores", False),
    ("O15", ["name = 'Wil'", "name = 'Ana'"], "print(name)", "print('Wil')", False),
    # --- researcher false rejects (all should now be accepted) ---
    ("C1", PD, "big = df[df['qty'] > 10]", "big = df.query('qty > 10')", True),
    ("C3", PD, "df = df.dropna(subset=['price'])", "df.dropna(subset=['price'], inplace=True)", True),
    ("C6", ["xs = [1.0, float('nan')]"], "ys = [v * 2 for v in xs]", "ys = [v * 2 for v in xs]", True),
    ("C7", ["import pandas as pd\ns = pd.Series([None, None], dtype=float)"], "m = s.mean()", "m = s.mean()", True),
    ("C8", PD, "p = df['price'].iloc[1]", "p = df['price'].iloc[1]", True),
    ("C9", ["import numpy as np\nd = {'a': np.float64('nan')}"], "n = len(d)", "n = len(d)", True),
    ("C10", ["import numpy as np\nxs = [1.0, 2.0, 4.0]"], "avg = sum(xs) / len(xs)", "avg = np.mean(xs)", True),
    ("C11", ["import pandas as pd\ndf = pd.DataFrame({'a':[0.1,0.7],'b':[0.2,0.1],'c':[0.3,0.2]})"],
     "df['m'] = (df['a'] + df['b'] + df['c']) / 3", "df['m'] = df[['a','b','c']].mean(axis=1)", True),
    ("C12", PD, "ids = df['qty'].tolist()", "ids = list(df['qty'])", True),
    ("C13", PD, "n = len(df)", "n = df['qty'].count()", True),
    ("C14", PD, "has = (df['qty'] > 10).any()", "has = any(df['qty'] > 10)", True),
    ("C16", PD, "avg = df.groupby('category')['price'].mean()", "avg = df.groupby('category', sort=False)['price'].mean()", None),
    ("C20", PD, "df['category'] = df['category'].str.upper()", "df['category'] = df['category'].map(str.upper, na_action='ignore')", True),
    ("C21", [SK1], "a, b, c, d = train_test_split(X, y, test_size=0.2)", "a, b, c, d = train_test_split(X, y, test_size=0.2)", True),
    ("C22", [RF], "rf.fit(X, y)", "rf.fit(X, y)", True),
    ("C23", [DT], "t.fit(X, y)", "t.fit(X, y)", True),
    ("C25", ["nums = [1,2,3]"], "g = (n * 2 for n in nums)", "g = (n * 2 for n in nums)", True),
    ("C26", ["nums = [1,2,3]"], "m = map(str, nums)", "m = map(str, nums)", True),
    ("C27", ["it = iter([1, 2, 3])"], "first = next(it)", "first = next(it)", True),
    ("C38", ["import math\nr = 2.0"], "area = math.pi * r ** 2", "area = 3.141592653589793 * r ** 2", True),
    ("D1", ["xs = [0.1, 0.2, 0.3]"], "t = sum(xs)", "t = xs[0] + xs[1] + xs[2]", True),
    ("D12", ["import pandas as pd\ndf = pd.DataFrame({'q':[1,2]})"], "df['q2'] = df['q'] * 2", "df['q2'] = df['q'] * 2.0", True),
    ("D16", ["import pandas as pd\ndf = pd.DataFrame({'c':['a','b']})"], "df['c'] = df['c'].str.upper()", "df['c'] = df['c'].str.upper().astype(object)", True),
    ("D18", ["import numpy as np"], "r = np.random.rand(2)", "r = np.random.rand(2)", True),
    ("D17", ["class N: pass\nn = N()\nn.me = n"], "x = 1", "x = 1", True),
    # --- researcher false accepts (all should now be rejected) ---
    ("C4", PD, "df = df.dropna(subset=['price'])", "df = df.dropna(subset=['price'], inplace=True)", False),
    ("C5", PD, "df['price'] = df['price'].fillna(0)", "df['price'].fillna(0, inplace=True)", False),
    ("C28", ["name = 'Wil'"], "name = name.strip()", "name.strip()", False),
    ("C29", ["name = 'Wil'"], "name = name.strip()", "pass", False),
    ("C30", ["orders = []\nn = 0"], "n = len(orders)", "len(orders)", False),
    ("C31", ["scores = [3, 1, 2]"], "ranked = sorted(scores)", "ranked = sorted(scores); del scores", False),
    ("C32", ["fruits = ['apple']"], "fruits.append('kiwi')", "fruits.append('kiwi'); fruits.append('x'); fruits.pop()", False),
    ("C33", ["total = 10", "total = -2"], "total += 5", "total = 15", False),
    ("C34", ["names = ['ana', 'ben']", "names = ['cy']"], "upper = [n.upper() for n in names]", "upper = ['ANA', 'BEN']", False),
    ("C35", ["x = [1, 2, 3]"], "print(len(x))", "len(x)", False),
    ("C37", ["fruits = ['apple']\nbasket = fruits"], "fruits.append('kiwi')", "fruits = fruits + ['kiwi']", False),
    ("C2", PD, "df = df.dropna(subset=['price'])", "df = df.dropna(subset=['price']).reset_index(drop=True)", False),
    ("D5", PD, "n = len(df)", "", False),
    ("D6", PD, "n = len(df)", "# not sure", False),
    ("D7", PD, "n = len(df)", "raise SystemExit", False),
    ("D8", PD, "n = len(df)", "exit()", False),
    ("D9", [], "n = 1", "n = 1", False),
    ("LEAK", [SKS1, SKS2], "model.fit(X_train, y_train)", "model.fit(X, y)", False),
    ("WRONGSET", [SKF1, SKF2], "preds = model.predict(X_test)", "preds = model.predict(X_train)", False),
    # --- remaining audit items (D8, D10, D25, A7) ---
    ("C39", ["fruits = ['apple']"], "fruits.append('kiwi')", "_ = fruits.append('kiwi')", True),
    ("C38b", ["import math\nr = 2.0", "import math\nr = 3.0"], "area = math.pi * r ** 2", "from math import pi; area = pi * r ** 2", False),
    ("IMPORT", ["r = 2.0", "r = 3.0"], "import math", "import math as m", None),
    ("C40", ["xs = [1,2,3]"], "total = sum(xs)", "total = (s := sum(xs))", False),
    ("D25", ["x = [1, 2, 3]", "x = [1]"], "print(len(x))", "len(x)", False),
    ("CHAIN", PD, "df.loc[0, 'qty'] = 99", "df['qty'][0] = 99", False),
    ("LOC", PD, "df.loc[0, 'qty'] = 99", "df.at[0, 'qty'] = 99", True),
]
ORDERED = [  # (id, setups, reference, answer, options, expected)
    ("ORD1", ["import pandas as pd\ndf = pd.DataFrame({'c':['b','a','b'], 'p':[1.0,2.0,3.0]})"],
     "s = df.groupby('c')['p'].sum()", "s = df.groupby('c', sort=False)['p'].sum()", None, False),
    ("ORD2", ["import pandas as pd\ndf = pd.DataFrame({'c':['b','a','b'], 'p':[1.0,2.0,3.0]})"],
     "s = df.groupby('c')['p'].sum()", "s = df.groupby('c', sort=False)['p'].sum()", {"ignore_order": True}, True),
    ("ORD3", ["import pandas as pd\ndf = pd.DataFrame({'a':[1],'b':[2]})"],
     "sub = df[['a', 'b']]", "sub = df[['b', 'a']]", {"ignore_order": True}, True),
]

bad = 0
for cid, setups, ref, ans, exp in CASES:
    try:
        r = check_all(setups, ref, ans)
        got, msg = r["correct"], r["messages"][0]
    except BaseException as e:
        got, msg = "CRASH", f"{type(e).__name__}: {e}"
    flag = "    " if exp is None else ("OK  " if got == exp else "BAD ")
    bad += flag == "BAD "
    print(f"{flag}{cid:9} exp={exp!s:5} got={got!s:5} {msg[:95]}")

for cid, setups, ref, ans, opts, exp in ORDERED:
    r = check_all(setups, ref, ans, opts)
    flag = "OK  " if r["correct"] == exp else "BAD "
    bad += flag == "BAD "
    print(f"{flag}{cid:9} exp={exp!s:5} got={r['correct']!s:5} {r['messages'][0][:95]}")

# builtins isolation: a patch in one check must not leak into the next
check_all(["x=[1,2]"], "n = len(x)", "__import__('builtins').len = lambda o: 99")
r = check_all(["x=[1,2]", "x=[1]"], "n = len(x)", "n = len(x)")
iso = r["correct"]
print("OK  " if iso else "BAD ", "ISO      builtins restored between checks:", iso)
bad += not iso

# parts() labels += as augmented, refuses two statements
pa = parts("fruits += ['kiwi']")["landing"]["kind"] == "augmented"
try:
    parts("a = 1; b = 2"); pm = False
except ValueError:
    pm = True
print("OK  " if pa and pm else "BAD ", "PARTS    augmented label + single statement:", pa, pm)
bad += not (pa and pm)
print("mismatches:", bad, "of", len(CASES) + len(ORDERED) + 2)
