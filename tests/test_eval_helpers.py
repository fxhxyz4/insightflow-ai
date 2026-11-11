import json

from eval.eval_agent import is_grounded, saved_summaries, tool_ok


def test_is_grounded_accepts_paraphrase_and_rejects_invention():
    titles = ["VPS vs shared hosting: which one do you actually need?",
              "Binance CFO is leaving to 'pursue a new venture' after $6.3 billion hack",
              "Costco members can get $5 off the reimagined Ocarina of Time"]
    paraphrase = ("1. A discussion on shared hosting versus VPS. 2. The CFO of Binance is leaving the company to "
                  "pursue a new venture after a $6.3 billion hack. 3. Costco members can save $5 on Ocarina of Time.")
    assert is_grounded(paraphrase, titles)
    assert not is_grounded("Stocks rallied today as the Federal Reserve held interest rates steady.", titles)
    assert not is_grounded("Binance CFO is leaving.", titles)
    assert not is_grounded("anything", [])


def test_tool_ok_rules():
    q_digest = {"type": "digest", "category": "economics"}
    assert tool_ok(q_digest, [{"tool": "build_digest", "arg": "economics"}])
    assert tool_ok(q_digest, [{"tool": "get_articles", "arg": "economics, 2026-11-03"}])
    assert not tool_ok(q_digest, [{"tool": "get_articles", "arg": "design"}])
    q_search = {"type": "search", "keywords": "AI"}
    assert tool_ok(q_search, [{"tool": "search_news", "arg": "latest AI news"}])
    assert not tool_ok(q_search, [{"tool": "list_categories", "arg": ""}])


def test_saved_summaries_merges_models(tmp_path):
    for name, ok in (("phi", 0.8), ("qwen3", 0.6)):
        (tmp_path / f"agent_{name}.json").write_text(json.dumps({"summary": {"model": name, "agent_success": ok}, "rows": []}))
    table = saved_summaries(tmp_path)
    assert list(table["model"]) == ["phi", "qwen3"]
