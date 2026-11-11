import json

import pandas as pd

from config.config import ROOT

RESULTS = ROOT / "eval" / "results"
OUT = ROOT / "docs" / "results_tables_ua.md"


def md(df):
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(x) else str(x) for x in row) + " |")
    return "\n".join(lines)


def classification_tables():
    parts = []
    p = RESULTS / "summary_classify.csv"
    if p.exists():
        df = pd.read_csv(p).rename(columns={"method": "Метод", "accuracy": "accuracy", "macro_f1": "macro-F1",
                                            "f1_mixed": "F1 mixed", "f1_thematic": "F1 thematic",
                                            "sec_per_item": "с/новину"})
        parts.append("### Таблиця 1. Класифікація за категоріями (ручна вибірка)\n\n" + md(df))
    p = RESULTS / "compare.csv"
    if p.exists():
        df = pd.read_csv(p, keep_default_na=False)
        for subset, title in (("all", "уся вибірка"), ("mixed", "змішані фіди"), ("thematic", "тематичні фіди")):
            part = df[df["subset"] == subset].drop(columns=["subset"])
            if len(part):
                part = part.dropna(axis=1, how="all")
                parts.append(f"### Таблиця 2 ({title}, n = {int(part['n'].iloc[0])}). 95% довірчі інтервали (bootstrap)\n\n"
                             + md(part.drop(columns=["n"])))
        parts.append("`*` у стовпцях d_* означає, що інтервал різниці з baseline не містить 0.")
    return parts


def agent_tables():
    parts = []
    p = RESULTS / "summary_agent.csv"
    if p.exists():
        parts.append("### Таблиця 3. Агент з інструментами проти тієї ж моделі без інструментів\n\n" + md(pd.read_csv(p)))
    fails = []
    for path in sorted(RESULTS.glob("agent_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data["rows"]:
            a = row["agent"]
            if not a["success"]:
                fails.append({"Модель": data["summary"]["model"], "#": row["id"], "Запит": row["question"],
                              "tool_ok": a["tool_ok"], "grounded": a["grounded"], "finished": a["finished"],
                              "Відповідь (початок)": a["answer"][:120].replace("\n", " ").replace("|", "/"),
                              "Причина (заповнити вручну)": ""})
    if fails:
        parts.append("### Таблиця 4. Запити, які агент не пройшов автоматично (розбір вручну)\n\n" + md(pd.DataFrame(fails)))
    return parts


def main():
    parts = ["# Таблиці для Розділу 3 (згенеровано eval/make_tables.py)\n"] + classification_tables() + agent_tables()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Збережено: {OUT}")


if __name__ == "__main__":
    main()
