import re
import sqlite3
from datetime import datetime, timedelta, timezone

from config.config import DB_PATH

COLUMNS = "id, title, summary, source, published, url, category"


def time_window(date=None):
    if date in (None, "", "today"):
        return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(), None
    day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return day.isoformat(), (day + timedelta(days=1)).isoformat()


EN_WORDS = {"the", "and", "of", "to", "is", "for", "with", "that", "are", "this", "from", "your", "how", "what",
            "why", "you", "it", "its", "was", "will", "can", "not", "be", "has", "have", "after", "says"}


def looks_english(text):
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isascii() for c in letters) / len(letters) < 0.9:
        return False
    hits = len({w for w in re.findall(r"[a-z']+", text.lower()) if w in EN_WORDS})
    return hits >= (1 if len(text) < 80 else 2)


def _english_only(rows, limit):
    return [r for r in rows if looks_english(f"{r['title']} {r['summary'] or ''}")][:limit]


def fetch_articles(conn, category, date=None, limit=8, fallback=True):
    conn.row_factory = sqlite3.Row
    start, end = time_window(date)
    sql = f"SELECT {COLUMNS} FROM articles WHERE category = ? AND published >= ?"
    args = [category, start]
    if end:
        sql += " AND published < ?"
        args.append(end)
    rows = _english_only(conn.execute(sql + " ORDER BY published DESC LIMIT ?", args + [limit * 4]).fetchall(), limit)
    note = ""
    if not rows and fallback:
        rows = _english_only(conn.execute(
            f"SELECT {COLUMNS} FROM articles WHERE category = ? ORDER BY published DESC LIMIT ?",
            (category, limit * 4),
        ).fetchall(), limit)
        if rows:
            note = "Новин за запитаний період немає; показано найновіші з наявних."
    return [dict(r) for r in rows], note


def lead(text, n=2, max_chars=300):
    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return " ".join(sentences[:n])[:max_chars].strip()


def summarize(llm, title, summary):
    if not summary:
        return ""
    if llm is None:
        return lead(summary)
    messages = [
        {"role": "system", "content": "Summarize the news article in at most two short sentences. "
                                      "Use only the given text. Do not add facts."},
        {"role": "user", "content": f"Title: {title}\nText: {summary[:800]}"},
    ]
    return llm.chat(messages, max_tokens=90).strip()


def _ensure_cache(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS summaries "
                 "(id TEXT, model TEXT, text TEXT, PRIMARY KEY (id, model))")


def make_digest(category, date=None, llm=None, limit=8, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    _ensure_cache(conn)
    rows, note = fetch_articles(conn, category, date, limit)
    model = llm.name if llm else "lead"

    lines = [f"## {category} ({len(rows)})"]
    if note:
        lines.append(f"_{note}_")
    if not rows:
        lines.append("Новин немає.")
    if llm and len(rows) >= 2:
        headlines = "\n".join(f"- {r['title']}" for r in rows)
        overview = llm.chat(
            [{"role": "system", "content": "Write ONE sentence (max 30 words) naming the main themes of these headlines."},
             {"role": "user", "content": headlines}], max_tokens=70).strip()
        lines.append(f"**Огляд:** {overview}")

    for i, r in enumerate(rows, 1):
        cached = conn.execute("SELECT text FROM summaries WHERE id = ? AND model = ?", (r["id"], model)).fetchone()
        if cached:
            text = cached[0]
        else:
            text = summarize(llm, r["title"], r["summary"])
            if llm:
                conn.execute("INSERT OR REPLACE INTO summaries VALUES (?, ?, ?)", (r["id"], model, text))
        lines.append(f"{i}. **{r['title']}** ({r['source']}, {(r['published'] or '')[:10]})")
        if text:
            lines.append(f"   {text}")
        lines.append(f"   {r['url']}")
    conn.commit()
    conn.close()
    return "\n".join(lines)
