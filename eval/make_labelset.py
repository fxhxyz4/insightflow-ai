import sqlite3
import sys

import pandas as pd

from config.config import CATEGORIES, DB_PATH, ROOT, SEED

OUT = ROOT / "eval" / "labelset.csv"
N_MIXED = 100
N_PER_CATEGORY = 14


def main():
    if OUT.exists():
        sys.exit(f"{OUT} вже існує, не перезаписую. Видаліть його вручну, якщо потрібна нова вибірка.")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, title, summary, feed_category FROM articles", conn)
    conn.close()
    df["summary"] = df["summary"].fillna("")
    df = df[df["summary"].str.len() >= 40]

    mixed = df[df["feed_category"].isna()]
    parts = [mixed.sample(min(N_MIXED, len(mixed)), random_state=SEED)]
    for cat in CATEGORIES:
        pool = df[df["feed_category"] == cat]
        if len(pool) < N_PER_CATEGORY:
            print(f"Увага: для {cat} лише {len(pool)} статей (потрібно {N_PER_CATEGORY})")
        parts.append(pool.sample(min(N_PER_CATEGORY, len(pool)), random_state=SEED))

    out = pd.concat(parts).sample(frac=1, random_state=SEED)
    out["summary"] = out["summary"].str.slice(0, 300)
    out["label"] = ""
    out[["id", "title", "summary", "label"]].to_csv(OUT, index=False)
    print(f"Збережено {len(out)} рядків у {OUT}")


if __name__ == "__main__":
    main()
