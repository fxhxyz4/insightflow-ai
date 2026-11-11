import sqlite3
from datetime import datetime

from src.agent import Agent, parse_action
from src.classify import LLMClassifier, classify_db, get_classifier, load_articles
from src.digest import make_digest
from src.scheduler import next_run
from src.tools import Toolbox
from tests.fakes import FakeLLM, make_db


def test_llm_classifier_and_invalid_fallback():
    assert LLMClassifier(FakeLLM(choice="science")).predict(["a", "b"]) == ["science", "science"]
    assert LLMClassifier(FakeLLM(choice="banana")).predict(["a"]) == ["invalid"]


def test_baseline_trains_and_classify_db_fills_missing(tmp_path):
    db = make_db(tmp_path / "t.db", n=120)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE articles SET category = NULL")
    conn.commit()
    conn.close()
    predictor = get_classifier("baseline", load_articles(db))
    assert classify_db(predictor, db) == 120
    assert load_articles(db)["category"].notna().all()


def test_tools(tmp_path):
    db = make_db(tmp_path / "t.db")
    tb = Toolbox(db_path=db)
    assert "science: 5 news" in tb.list_categories()
    assert "Headline number" in tb.get_articles("economics")
    assert tb.get_articles("sport").startswith("ERROR: unknown category")
    assert "about world" in tb.search_news("world")
    assert tb.search_news("zz") .startswith("ERROR")
    assert "## design" in tb.build_digest("design")


def test_digest_with_llm_uses_cache(tmp_path):
    db = make_db(tmp_path / "t.db")
    llm = FakeLLM(replies=["Overview sentence."] + ["Short summary."] * 10)
    first = make_digest("science", llm=llm, db_path=db)
    assert "**Огляд:** Overview sentence." in first and "Short summary." in first
    calls_before = len(llm.chat_calls)
    make_digest("science", llm=FakeLLM(replies=["Overview sentence."]), db_path=db)
    assert calls_before > 1


def test_agent_react_loop_with_tool(tmp_path):
    db = make_db(tmp_path / "t.db")
    llm = FakeLLM(replies=["Thought: need headlines\nAction: get_articles(economics)",
                           "Thought: I now know the final answer\nFinal Answer: Headline number 1 about economics"])
    res = Agent(llm, Toolbox(db_path=db).registry).run("What's new in economics?")
    assert res["finished"] and res["tool_calls"] == [{"tool": "get_articles", "arg": "economics"}]
    assert "Headline number 1" in res["answer"]
    assert llm.chat_calls[1][-1]["content"].startswith("Observation:")


def test_agent_unknown_tool_and_format_violation(tmp_path):
    db = make_db(tmp_path / "t.db")
    llm = FakeLLM(replies=["Action: fly_to_moon(now)", "Final Answer: sorry"])
    res = Agent(llm, Toolbox(db_path=db).registry).run("q")
    assert "unknown tool" in res["trace"][1]["result"] and res["answer"] == "sorry"
    bad = Agent(FakeLLM(replies=["just chatting", "more chatting"]), {}).run("q")
    assert not bad["finished"] and bad["answer"] == "more chatting"
    fixed_llm = FakeLLM(replies=["Thought: hmm\nAction:", "Final Answer: Hello!"])
    ok = Agent(fixed_llm, {}).run("привіт")
    assert ok["finished"] and ok["answer"] == "Hello!"
    assert "invalid format" in fixed_llm.chat_calls[1][-1]["content"]


def test_parse_action():
    assert parse_action("Thought: x\nAction: search_news(AI chips, now)") == ("search_news", "AI chips, now")


def test_scheduler_next_run():
    now = datetime(2026, 11, 3, 8, 0)
    assert next_run(["07:00", "19:00"], now) == datetime(2026, 11, 3, 19, 0)
    assert next_run(["07:00"], now) == datetime(2026, 11, 4, 7, 0)


def test_other_class_only_when_allowed():
    assert LLMClassifier(FakeLLM(choice="other")).predict(["a"]) == ["invalid"]
    assert LLMClassifier(FakeLLM(choice="other"), allow_other=True).predict(["a"]) == ["other"]


def test_english_filter():
    from src.digest import looks_english
    assert looks_english("Binance CFO is leaving to pursue a new venture after the hack")
    assert not looks_english("Come passare lavoro da osFoundry a una chat di Claude collegata")
    assert not looks_english("Kui sa seda loed, on sul ilmselt praegu avatud üle 40 vahekaardi")
    assert not looks_english("Neuropixels のニュースから考える、分子構造ビューアの次のインターフェース")


def test_parse_action_tolerates_named_arguments():
    assert parse_action("Action: build_digest(category=economics)") == ("build_digest", "economics")
    assert parse_action('Action: get_articles(category="economics", date="2026-11-07")') == ("get_articles", "economics, 2026-11-07")
    assert parse_action('Action: search_news(keywords="AI chips")') == ("search_news", "AI chips")
    assert parse_action("Action:") == (None, None)
