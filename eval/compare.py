import json

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from config.config import ROOT, SEED
from src.classify import load_articles

RESULTS = ROOT / "eval" / "results"
LABELSET = ROOT / "eval" / "labelset.csv"
BASELINE = "baseline_tfidf_logreg"
N_BOOT = 2000


def load():
    lab = pd.read_csv(LABELSET, dtype=str, keep_default_na=False).set_index("id")["label"]
    preds = {}
    for path in sorted(RESULTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "method" in data and "predictions" in data:
            preds[data["method"]] = data["predictions"]
    ids = sorted(set.intersection(*[set(p) for p in preds.values()]))
    origin = load_articles().set_index("id")["feed_category"].reindex(ids).map(lambda c: "mixed" if pd.isna(c) else "thematic")
    y = np.array([lab[i] for i in ids])
    return ids, y, {m: np.array([p[i] for i in ids]) for m, p in preds.items()}, origin.to_numpy()


def macro_f1(y, p):
    return f1_score(y, p, labels=sorted(set(y)), average="macro", zero_division=0)


def ci(values):
    lo, hi = np.percentile(values, [2.5, 97.5])
    return lo, hi


def analyse(name, mask, y, P, rng):
    y_, P_ = y[mask], {m: p[mask] for m, p in P.items()}
    n = len(y_)
    boot = {m: {"acc": [], "f1": []} for m in P_}
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, n)
        for m, p in P_.items():
            boot[m]["acc"].append((y_[idx] == p[idx]).mean())
            boot[m]["f1"].append(macro_f1(y_[idx], p[idx]))
    rows = []
    for m, p in P_.items():
        acc, f1 = (y_ == p).mean(), macro_f1(y_, p)
        row = {"subset": name, "n": n, "method": m,
               "accuracy": f"{acc:.3f} [{ci(boot[m]['acc'])[0]:.3f}, {ci(boot[m]['acc'])[1]:.3f}]",
               "macro_f1": f"{f1:.3f} [{ci(boot[m]['f1'])[0]:.3f}, {ci(boot[m]['f1'])[1]:.3f}]"}
        if m != BASELINE and BASELINE in P_:
            for key, label in (("acc", "d_accuracy"), ("f1", "d_macro_f1")):
                diff = np.array(boot[m][key]) - np.array(boot[BASELINE][key])
                lo, hi = ci(diff)
                point = ((y_ == p).mean() - (y_ == P_[BASELINE]).mean()) if key == "acc" \
                    else macro_f1(y_, p) - macro_f1(y_, P_[BASELINE])
                sig = "*" if (lo > 0 or hi < 0) else ""
                row[label] = f"{point:+.3f} [{lo:+.3f}, {hi:+.3f}]{sig}"
        rows.append(row)
    return rows


def main():
    ids, y, P, origin = load()
    print(f"Спільних тестових новин у всіх методів: {len(ids)}; методи: {list(P)}")
    rng = np.random.default_rng(SEED)
    rows = []
    for name, mask in (("all", np.ones(len(y), bool)), ("mixed", origin == "mixed"), ("thematic", origin == "thematic")):
        rows += analyse(name, mask, y, P, rng)
    table = pd.DataFrame(rows).fillna("")
    RESULTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS / "compare.csv", index=False)
    pd.set_option("display.width", 250)
    print(table.to_string(index=False))
    print("\n* = інтервал різниці з baseline не містить 0 (різниця виходить за межі шуму вибірки).")


if __name__ == "__main__":
    main()
