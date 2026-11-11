import argparse
import json
import time

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from config.config import CATEGORIES, ROOT
from config.runtime import MODELS
from src.classify import LLMClassifier, build_baseline, load_articles

LABELSET = ROOT / "eval" / "labelset.csv"
RESULTS = ROOT / "eval" / "results"


def load_test(articles):
    lab = pd.read_csv(LABELSET, dtype=str, keep_default_na=False)
    n_empty = int((lab["label"] == "").sum())
    n_other = int((lab["label"] == "other").sum())
    if n_empty:
        print(f"Увага: не розмічено ще {n_empty} з {len(lab)} рядків (вони пропущені).")
    used = lab[lab["label"].isin(CATEGORIES)][["id", "label"]]
    test = used.merge(articles, on="id", how="left")
    test["origin"] = test["feed_category"].map(lambda c: "mixed" if pd.isna(c) else "thematic")
    return test, set(lab["id"]), n_other


def score(y_true, y_pred):
    labels = sorted(set(y_true))
    return {
        "n": len(y_true),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_f1": round(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0), 4),
    }


def report(name, test, preds, extra=None):
    y_true = test["label"].tolist()
    result = {"method": name, "overall": score(y_true, preds), "by_origin": {}, **(extra or {})}
    for origin, part in test.assign(pred=preds).groupby("origin"):
        result["by_origin"][origin] = score(part["label"].tolist(), part["pred"].tolist())
    result["predictions"] = dict(zip(test["id"], preds))

    labels = sorted(set(y_true) | set(preds))
    print(f"\n===== {name} =====")
    print(classification_report(y_true, preds, labels=labels, digits=3, zero_division=0))
    print("Матриця помилок (рядки = істина, стовпці = передбачення):")
    print(pd.DataFrame(confusion_matrix(y_true, preds, labels=labels), index=labels, columns=labels))
    print("\nЗагалом:", result["overall"], extra or "")
    for origin, s in result["by_origin"].items():
        print(f"  {origin}: {s}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def summary_row(r):
    by = r["by_origin"]
    return {"method": r["method"], "n": r["overall"]["n"], "accuracy": r["overall"]["accuracy"],
            "macro_f1": r["overall"]["macro_f1"],
            "f1_mixed": by.get("mixed", {}).get("macro_f1"), "f1_thematic": by.get("thematic", {}).get("macro_f1"),
            "sec_per_item": r.get("seconds_per_item")}


def main():
    global RESULTS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--models", nargs="*", default=[], choices=list(MODELS), help="LLM-моделі для порівняння")
    ap.add_argument("--limit", type=int, default=None, help="взяти лише перші N тестових новин (для проби)")
    args = ap.parse_args()
    if args.limit:
        RESULTS = RESULTS / "trial"

    articles = load_articles()
    test, labelset_ids, n_other = load_test(articles)
    if args.limit:
        test = test.head(args.limit)
    print(f"Тест: {len(test)} новин (виключено 'other': {n_other})")
    print("Тест за категоріями:", test["label"].value_counts().to_dict())

    train = articles[articles["feed_category"].notna() & ~articles["id"].isin(labelset_ids)]
    print(f"Навчання baseline: {len(train)} новин;", train["feed_category"].value_counts().to_dict())

    results = []
    t0 = time.time()
    model = build_baseline().fit(train["text"], train["feed_category"])
    preds = model.predict(test["text"]).tolist()
    results.append(report("baseline_tfidf_logreg", test, preds,
                          {"n_train": len(train), "seconds_per_item": round((time.time() - t0) / max(len(test), 1), 4)}))

    for name in args.models:
        try:
            from src.llm import LLM
            clf = LLMClassifier(LLM(name))
        except Exception as e:
            print(f"\n!!! Модель '{name}' не завантажилась: {type(e).__name__}: {e}")
            continue
        t0 = time.time()
        preds = clf.predict(test["text"], progress=True)
        per_item = round((time.time() - t0) / max(len(test), 1), 3)
        results.append(report(f"llm_{name}", test, preds, {"seconds_per_item": per_item}))

    saved = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(RESULTS.glob("*.json"))]
    table = pd.DataFrame([summary_row(r) for r in saved if "method" in r and "overall" in r])
    RESULTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS / "summary_classify.csv", index=False)
    print("\n=== ПІДСУМОК ===")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
