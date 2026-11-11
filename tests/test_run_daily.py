import sqlite3

from src import run_daily
from tests.fakes import FakeLLM, make_db


def test_run_daily_end_to_end_without_network(tmp_path):
    db = make_db(tmp_path / "t.db", n=120)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE articles SET category = NULL")
    conn.commit()
    conn.close()
    out = run_daily.run(model="baseline", digest_model="none", do_ingest=False, db_path=db, reports_dir=tmp_path / "rep")
    text = out.read_text(encoding="utf-8")
    assert "# Дайджест новин" in text and "## economics" in text
    assert (tmp_path / "rep" / "latest.md").exists()


def test_run_daily_with_fake_llm(tmp_path):
    db = make_db(tmp_path / "t.db", n=60)
    out = run_daily.run(model="qwen3", digest_model="qwen3", do_ingest=False, db_path=db,
                        reports_dir=tmp_path / "rep", llm_factory=lambda name: FakeLLM(name=name))
    assert out.exists()


def test_reclassify_with_other_hides_other_from_digest(tmp_path):
    db = make_db(tmp_path / "t.db", n=60)
    out = run_daily.run(model="phi", digest_model="none", do_ingest=False, db_path=db, reports_dir=tmp_path / "rep",
                        llm_factory=lambda name: FakeLLM(name=name, choice="other"), reclassify=True)
    text = out.read_text(encoding="utf-8")
    assert "Новин немає." in text and "Headline number" not in text
