import argparse
import hashlib
import html
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests

from config.config import DB_PATH, FEEDS, REQUEST_TIMEOUT, ROOT, SNAPSHOT_DIR, USER_AGENT

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id            TEXT PRIMARY KEY,  -- sha1 нормалізованого URL (дедуплікація)
    url           TEXT NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT,
    published     TEXT,              -- ISO, UTC
    source        TEXT,              -- назва фіда
    feed_category TEXT,              -- слабка мітка з config.FEEDS (або NULL)
    fetched_at    TEXT,
    category      TEXT               -- сюди classify.py запише передбачену категорію
)
"""


def clean_text(raw, limit=1500):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


BOILERPLATE = [
    re.compile(r"Article URL:\s*\S+", re.I),
    re.compile(r"Comments URL:\s*\S+", re.I),
    re.compile(r"Points:\s*\d+", re.I),
    re.compile(r"#\s*Comments:\s*\d+", re.I),
    re.compile(r"\bThe post\b.{0,300}?appeared first on [^.]{0,80}\.?", re.I),
    re.compile(r"Nature\s*,?\s*Published online:?[^;]{0,40};?", re.I),
    re.compile(r"\bdoi:?\s*10\.\d{4,9}/\S+", re.I),
    re.compile(r"https?://\S+"),
]


def clean_summary(raw):
    text = clean_text(raw)
    for pattern in BOILERPLATE:
        text = pattern.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(url):
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def parse_date(entry, fallback):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return fallback


def fetch_entries(feed):
    resp = requests.get(feed["url"], headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content).entries


def to_article(entry, feed, now):
    link, title = entry.get("link"), clean_text(entry.get("title"), 300)
    if not link or not title:
        return None
    url = normalize_url(link)
    return {
        "id": hashlib.sha1(url.encode()).hexdigest(),
        "url": url,
        "title": title,
        "summary": clean_summary(entry.get("summary") or entry.get("description")),
        "published": parse_date(entry, now),
        "source": feed["name"],
        "feed_category": feed["category"],
        "fetched_at": now,
        "category": None,
    }


def save(conn, articles):
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO articles VALUES (:id, :url, :title, :summary, :published,"
        " :source, :feed_category, :fetched_at, :category)",
        articles,
    )
    conn.commit()
    return conn.total_changes - before


def run(feeds=FEEDS, check_only=False, db_path=DB_PATH):
    now = datetime.now(timezone.utc).isoformat()
    conn = None
    if not check_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(SCHEMA)

    ok, total_new = 0, 0
    for feed in feeds:
        try:
            entries = fetch_entries(feed)
            articles = [a for a in (to_article(e, feed, now) for e in entries) if a]
            if not articles:
                raise ValueError("фід порожній")
            new = save(conn, articles) if conn else 0
            ok += 1
            total_new += new
            print(f"OK    {feed['name']:<24} записів: {len(articles):>3}  нових: {new:>3}")
        except Exception as e:
            print(f"FAIL  {feed['name']:<24} {type(e).__name__}: {e}")

    print(f"\nПрацює фідів: {ok}/{len(feeds)}; нових статей: {total_new}")
    if conn:
        rows = conn.execute("SELECT feed_category FROM articles").fetchall()
        counts = Counter(r[0] or "mixed" for r in rows)
        print("У БД за слабкою міткою:", dict(counts), f"| всього: {len(rows)}")
        conn.close()


def clean_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, summary FROM articles").fetchall()
    fixed = {i: clean_summary(s) for i, s in rows}
    changed = sum(1 for i, s in rows if (s or "") != fixed[i])
    conn.executemany("UPDATE articles SET summary = ? WHERE id = ?", [(v, k) for k, v in fixed.items()])
    conn.commit()
    conn.close()
    print(f"БД: змінено описів {changed} з {len(rows)}")

    labelset = ROOT / "eval" / "labelset.csv"
    if labelset.exists():
        import pandas as pd
        df = pd.read_csv(labelset, dtype=str, keep_default_na=False)
        df["summary"] = [fixed.get(i, s)[:300] for i, s in zip(df["id"], df["summary"])]
        df.to_csv(labelset, index=False)
        print(f"{labelset.name}: описи оновлено, мітки збережено")


def snapshot(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM articles ORDER BY published")]
    conn.close()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{datetime.now().date()}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Знімок: {path} ({len(rows)} статей)")


def restore(snapshot_path=None, db_path=DB_PATH):
    if snapshot_path is None:
        files = sorted(SNAPSHOT_DIR.glob("*.jsonl"))
        if not files:
            raise SystemExit(f"Немає знімків у {SNAPSHOT_DIR}. Спочатку: python -m src.ingest --snapshot")
        snapshot_path = files[-1]
    with open(snapshot_path, encoding="utf-8") as f:
        articles = [json.loads(line) for line in f if line.strip()]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    added = save(conn, articles)
    conn.close()
    print(f"Відновлено з {snapshot_path.name}: у знімку {len(articles)}, додано {added}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--check", action="store_true", help="лише перевірити фіди")
    ap.add_argument("--snapshot", action="store_true", help="вивантажити БД у JSONL")
    ap.add_argument("--restore", action="store_true", help="відновити БД зі знімка JSONL")
    ap.add_argument("--clean-db", action="store_true", help="очистити описи в уже збереженій БД")
    args = ap.parse_args()
    if args.restore:
        restore()
    elif args.clean_db:
        clean_db()
    elif args.snapshot:
        snapshot()
    else:
        run(check_only=args.check)
