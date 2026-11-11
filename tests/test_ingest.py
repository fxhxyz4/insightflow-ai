import json
import sqlite3

from src.ingest import clean_summary, normalize_url, restore


def test_hacker_news_boilerplate_removed():
    raw = "<p>Article URL: https://a.b/c</p><p>Comments URL: https://news.ycombinator.com/item?id=1</p><p>Points: 5</p><p># Comments: 2</p>"
    assert clean_summary(raw) == ""


def test_wordpress_tail_removed_text_kept():
    assert clean_summary("Real text. The post Title appeared first on Site.") == "Real text."


def test_normalize_url_drops_utm_and_fragment():
    assert normalize_url("https://e.com/a?utm_source=x&id=3#top") == "https://e.com/a?id=3"


def test_restore_rebuilds_db_from_snapshot(tmp_path):
    row = {"id": "a1", "url": "https://e.com/a", "title": "T", "summary": "S", "published": "2026-11-07T00:00:00+00:00",
           "source": "X", "feed_category": None, "fetched_at": "2026-11-07T01:00:00+00:00", "category": None}
    snap = tmp_path / "s.jsonl"
    snap.write_text(json.dumps(row) + "\n", encoding="utf-8")
    db = tmp_path / "news.db"
    restore(snap, db)
    restore(snap, db)
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


def test_clean_summary_removes_nature_doi():
    assert clean_summary("Nature, Published online: 05 November 2026; doi:10.1038/d41586-026-01 Real text.").endswith("Real text.")
