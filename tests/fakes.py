import sqlite3

from src.ingest import SCHEMA


class FakeLLM:
    def __init__(self, replies=None, choice="science", name="fake"):
        self.name, self.replies, self.choice = name, list(replies or []), choice
        self.chat_calls = []

    def chat(self, messages, max_tokens=256, stop=None):
        self.chat_calls.append(messages)
        return self.replies.pop(0) if self.replies else "Final Answer: (fake)"

    def choose(self, messages, choices):
        return self.choice


def make_db(path, n=30):
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    cats = ["programming", "economics", "design", "marketing", "science", "world"]
    rows = []
    for i in range(n):
        cat = cats[i % 6]
        rows.append((f"id{i}", f"https://x.test/{i}", f"Headline number {i} is about {cat}",
                     f"This is the {cat} story for you. Second sentence about {cat}. Third.",
                     "2999-01-01T00:00:00+00:00", "TestFeed", cat if i % 3 else None, "now", cat))
    conn.executemany("INSERT INTO articles VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return path
