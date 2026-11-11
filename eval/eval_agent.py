import argparse
import json
import re
import sqlite3

import pandas as pd

from config.config import DB_PATH, ROOT
from config.runtime import MODELS
from src.agent import Agent, plain_answer
from src.digest import fetch_articles
from src.tools import Toolbox

QUERIES = ROOT / "eval" / "agent_queries.json"
RESULTS = ROOT / "eval" / "results"


def norm(s):
    return re.sub(r"[^a-z0-9а-яіїєґ]+", " ", (s or "").lower()).strip()


def expected_titles(q, db_path):
    conn = sqlite3.connect(db_path)
    if q["type"] == "search":
        rows = conn.execute("SELECT title FROM articles WHERE instr(lower(title || ' ' || coalesce(summary, '')), ?) > 0 "
                            "ORDER BY published DESC LIMIT 8", (q["keywords"].lower(),)).fetchall()
        titles = [r[0] for r in rows]
    else:
        titles = [r["title"] for r in fetch_articles(conn, q["category"], None, 8)[0]]
    conn.close()
    return titles


STOP = {"which", "actually", "about", "after", "their", "there", "these", "those", "would", "could", "while",
        "where", "being", "other", "first", "still", "every", "because", "between", "under", "over", "with",
        "from", "that", "this", "have", "what", "when", "your", "more", "most", "into", "than", "very", "will",
        "been", "were", "they", "them", "then", "also", "just", "like", "make", "need", "says", "said"}


def distinctive(title):
    return {w[:5] for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if len(w) >= 4 and w not in STOP}


def matched_titles(answer, titles):
    a = norm(answer)
    stems = {w[:5] for w in a.split()}
    count = 0
    for t in titles:
        toks = distinctive(t)
        ok = len(toks & stems) / len(toks) >= 0.5 if len(toks) >= 2 else norm(t)[:25] in a
        count += bool(ok)
    return count


def is_grounded(answer, titles):
    return bool(titles) and matched_titles(answer, titles) >= min(2, len(titles))


def tool_ok(q, calls):
    for c in calls:
        arg = (c["arg"] or "").lower()
        if q["type"] == "search" and c["tool"] == "search_news" and q["keywords"].lower() in arg:
            return True
        if q["type"] in ("digest", "headlines") and c["tool"] in ("build_digest", "get_articles") \
                and arg.split(",")[0].strip() == q["category"]:
            return True
    return False


def saved_summaries(results_dir):
    rows = [json.loads(p.read_text(encoding="utf-8"))["summary"] for p in sorted(results_dir.glob("agent_*.json"))]
    return pd.DataFrame(rows)


def main():
    global RESULTS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--models", nargs="+", required=True, choices=list(MODELS))
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--limit", type=int, default=None, help="лише перші N запитів (проба)")
    args = ap.parse_args()
    if args.limit:
        RESULTS = RESULTS / "trial"

    conn = sqlite3.connect(args.db)
    n_missing = conn.execute("SELECT COUNT(*) FROM articles WHERE category IS NULL").fetchone()[0]
    conn.close()
    if n_missing:
        raise SystemExit(f"У БД {n_missing} новин без категорії. Спочатку: python -m src.run_daily --no-ingest")

    queries = json.loads(QUERIES.read_text(encoding="utf-8"))[: args.limit]
    summary = []
    for name in args.models:
        from src.llm import LLM
        llm = LLM(name)
        agent = Agent(llm, Toolbox(db_path=args.db, llm=None).registry)
        rows = []
        for q in queries:
            titles = expected_titles(q, args.db)
            res = agent.run(q["question"])
            plain = plain_answer(llm, q["question"])
            a_tool, a_ground = tool_ok(q, res["tool_calls"]), is_grounded(res["answer"], titles)
            rows.append({"id": q["id"], "type": q["type"], "question": q["question"],
                         "n_expected_titles": len(titles),
                         "agent": {"answer": res["answer"], "finished": res["finished"], "tool_calls": res["tool_calls"],
                                   "seconds": res["seconds"], "tool_ok": a_tool, "grounded": a_ground,
                                   "success": a_tool and a_ground},
                         "plain": {"answer": plain, "grounded": is_grounded(plain, titles),
                                   "success": is_grounded(plain, titles)}})
            print(f"[{name}] #{q['id']} agent={'OK' if a_tool and a_ground else 'fail'} "
                  f"plain={'OK' if rows[-1]['plain']['success'] else 'fail'}")
        n = len(rows)
        s = {"model": name, "n": n,
             "agent_tool_ok": sum(r["agent"]["tool_ok"] for r in rows) / n,
             "agent_success": sum(r["agent"]["success"] for r in rows) / n,
             "plain_success": sum(r["plain"]["success"] for r in rows) / n,
             "agent_sec_per_query": round(sum(r["agent"]["seconds"] for r in rows) / n, 1)}
        summary.append(s)
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / f"agent_{name}.json").write_text(json.dumps({"summary": s, "rows": rows}, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    table = saved_summaries(RESULTS)
    table.to_csv(RESULTS / "summary_agent.csv", index=False)
    print("\n=== ПІДСУМОК (частка запитів) ===")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
