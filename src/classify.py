import sqlite3

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from config.config import CATEGORIES, DB_PATH, SEED
from config.runtime import CATEGORY_HINTS, CLASSIFY_MAX_CHARS


def make_text(title, summary):
    return f"{title}. {summary or ''}".strip()


def load_articles(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT id, title, summary, source, feed_category, category FROM articles", conn)
    conn.close()
    df["text"] = [make_text(t, s) for t, s in zip(df["title"], df["summary"])]
    return df


def build_baseline():
    return make_pipeline(
        TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2),
                        min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
    )


OTHER_HINT = "- other: sports, entertainment, celebrities, lifestyle, health, or anything that fits none of the categories above"


def build_messages(text, allow_other=False):
    hints = "\n".join(f"- {c}: {CATEGORY_HINTS[c]}" for c in CATEGORIES)
    if allow_other:
        hints += "\n" + OTHER_HINT
    system = (
        "You are a news classifier. Assign the article to exactly ONE category.\n"
        f"Categories:\n{hints}\n"
        "Answer with the category name only."
    )
    user = f"Article:\n{text[:CLASSIFY_MAX_CHARS]}\n\nCategory:"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


class LLMClassifier:
    def __init__(self, llm, allow_other=False):
        self.llm = llm
        self.name = llm.name
        self.allow_other = allow_other
        self.choices = CATEGORIES + (["other"] if allow_other else [])

    def predict_one(self, text):
        label = self.llm.choose(build_messages(text, self.allow_other), self.choices)
        return label if label in self.choices else "invalid"

    def predict(self, texts, progress=False):
        texts = list(texts)
        if progress:
            from tqdm import tqdm
            texts = tqdm(texts, desc=self.name)
        return [self.predict_one(t) for t in texts]


def get_classifier(method, articles=None, allow_other=False):
    if method == "baseline":
        if articles is None:
            articles = load_articles()
        train = articles[articles["feed_category"].notna()]
        if len(train) < 50:
            raise RuntimeError("Для baseline треба хоча б ~50 новин з тематичних фідів (запустіть збір).")
        return build_baseline().fit(train["text"], train["feed_category"])
    from src.llm import LLM
    return LLMClassifier(LLM(method), allow_other=allow_other)


def classify_db(predictor, db_path=DB_PATH, only_missing=True, progress=False):
    conn = sqlite3.connect(db_path)
    where = "WHERE category IS NULL" if only_missing else ""
    rows = conn.execute(f"SELECT id, title, summary FROM articles {where}").fetchall()
    if rows:
        texts = [make_text(t, s) for _, t, s in rows]
        try:
            labels = predictor.predict(texts, progress=progress)
        except TypeError:
            labels = predictor.predict(texts)
        conn.executemany("UPDATE articles SET category = ? WHERE id = ?",
                         [(str(lab), row[0]) for lab, row in zip(labels, rows)])
        conn.commit()
    conn.close()
    return len(rows)
