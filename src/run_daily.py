import argparse
from datetime import date as date_cls

from config.config import CATEGORIES, DB_PATH
from config.runtime import MODELS, REPORTS_DIR
from src import ingest
from src.classify import classify_db, get_classifier, load_articles
from src.digest import make_digest


def run(model="baseline", digest_model="none", day=None, do_ingest=True,
        db_path=DB_PATH, reports_dir=REPORTS_DIR, llm_factory=None, reclassify=False):
    if llm_factory is None:
        from src.llm import LLM as llm_factory
    llms = {}

    def get_llm(name):
        if name not in llms:
            llms[name] = llm_factory(name)
        return llms[name]

    if do_ingest:
        ingest.run(db_path=db_path)

    articles = load_articles(db_path)
    if reclassify or articles["category"].isna().any():
        if model == "baseline":
            predictor = get_classifier("baseline", articles)
        else:
            from src.classify import LLMClassifier
            predictor = LLMClassifier(get_llm(model), allow_other=True)
        n = classify_db(predictor, db_path, only_missing=not reclassify, progress=True)
        print(f"Класифіковано новин: {n}")
    else:
        print("Нових новин для класифікації немає.")

    day = day or date_cls.today().isoformat()
    llm = get_llm(digest_model) if digest_model != "none" else None
    parts = [f"# Дайджест новин за {day}\n"]
    for category in CATEGORIES:
        parts.append(make_digest(category, day if day != date_cls.today().isoformat() else None,
                                 llm=llm, db_path=db_path))
        parts.append("")
    text = "\n".join(parts)

    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"digest_{day}.md"
    out.write_text(text, encoding="utf-8")
    (reports_dir / "latest.md").write_text(text, encoding="utf-8")
    print(f"Звіт збережено: {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model", default="baseline", choices=["baseline", *MODELS], help="чим класифікувати")
    ap.add_argument("--digest-model", default="none", choices=["none", *MODELS], help="чим робити саммарі")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (за замовчуванням сьогодні, останні 24 год)")
    ap.add_argument("--no-ingest", action="store_true", help="не збирати RSS, працювати з наявною БД")
    ap.add_argument("--reclassify", action="store_true", help="переписати категорії ВСІХ новин (інакше лише нових)")
    args = ap.parse_args()
    run(args.model, args.digest_model, args.date, do_ingest=not args.no_ingest, reclassify=args.reclassify)


if __name__ == "__main__":
    main()
