import re
import sqlite3

from config.config import CATEGORIES, DB_PATH
from src.digest import fetch_articles, make_digest

DESCRIPTIONS = """- list_categories(): how many news are available per category
- get_articles(category): headlines of the latest news in a category; optionally with a date: get_articles(category, YYYY-MM-DD)
- search_news(keywords): find news by keywords (any category)
- build_digest(category): short digest (headlines + summaries) of the latest news in a category; optional date like get_articles
Examples: build_digest(economics)   get_articles(design)   get_articles(world, 2026-11-07)   search_news(Israel)   list_categories()"""


class Toolbox:
    def __init__(self, db_path=DB_PATH, llm=None, limit=8):
        self.db_path, self.llm, self.limit = db_path, llm, limit

    @staticmethod
    def _parse(arg):
        parts = [p.strip().strip("\"'") for p in (arg or "").split(",")]
        category = parts[0].lower()
        date = parts[1] if len(parts) > 1 and parts[1] else None
        if category not in CATEGORIES:
            raise ValueError(f"unknown category '{category}'. Use one of: {', '.join(CATEGORIES)}. Pass the plain value, e.g. build_digest(economics)")
        return category, date

    def list_categories(self, arg=""):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT category, COUNT(*) FROM articles WHERE category IS NOT NULL "
                            "GROUP BY category").fetchall()
        conn.close()
        if not rows:
            return "ERROR: no classified news yet (run: python -m src.run_daily)"
        counts = dict(rows)
        return "\n".join(f"{c}: {counts.get(c, 0)} news" for c in CATEGORIES)

    def get_articles(self, arg):
        try:
            category, date = self._parse(arg)
            conn = sqlite3.connect(self.db_path)
            rows, note = fetch_articles(conn, category, date, self.limit)
            conn.close()
        except ValueError as e:
            return f"ERROR: {e}"
        if not rows:
            return f"No news found in category '{category}'."
        lines = ([note] if note else []) + [f"- {r['title']} ({r['source']}, {(r['published'] or '')[:10]})" for r in rows]
        return "\n".join(lines)

    def search_news(self, arg):
        words = [w for w in re.findall(r"\w+", (arg or "").lower()) if len(w) >= 3][:5]
        if not words:
            return "ERROR: give at least one keyword (3+ letters)"
        score = " + ".join("(instr(lower(title || ' ' || coalesce(summary, '')), ?) > 0)" for _ in words)
        sql = (f"SELECT title, source, published, category, s FROM "
               f"(SELECT title, summary, source, published, category, ({score}) AS s FROM articles) "
               f"WHERE s > 0 ORDER BY s DESC, published DESC LIMIT ?")
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(sql, words + [self.limit]).fetchall()
        conn.close()
        if not rows:
            return f"No news found for '{arg}'."
        return "\n".join(f"- {t} ({src}, {(pub or '')[:10]}, {cat})" for t, src, pub, cat, _ in rows)

    def build_digest(self, arg):
        try:
            category, date = self._parse(arg)
        except ValueError as e:
            return f"ERROR: {e}"
        return make_digest(category, date, self.llm, self.limit, self.db_path)[:1800]

    @property
    def registry(self):
        return {"list_categories": self.list_categories, "get_articles": self.get_articles,
                "search_news": self.search_news, "build_digest": self.build_digest}
