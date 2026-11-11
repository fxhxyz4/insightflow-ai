import argparse

from config.runtime import DEFAULT_MODEL, MODELS
from src.agent import Agent
from src.llm import LLM
from src.tools import Toolbox


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS))
    ap.add_argument("--trace", action="store_true", help="показувати кроки агента (Thought/Action/Observation)")
    ap.add_argument("--llm-digest", action="store_true", help="саммарі в build_digest від LLM (повільніше)")
    args = ap.parse_args()

    llm = LLM(args.model)
    agent = Agent(llm, Toolbox(llm=llm if args.llm_digest else None).registry)
    print(f"Модель: {args.model}. Порожній рядок або Ctrl+D для виходу.")
    while True:
        try:
            question = input("\nВи> ").strip()
        except EOFError:
            break
        if not question:
            break
        result = agent.run(question, verbose=args.trace)
        print(f"\nАгент> {result['answer']}")
        if not result["finished"]:
            print("(агент не завершив відповідь у відведену кількість кроків)")
        print(f"[{result['steps']} кроків, {result['seconds']} с]")


if __name__ == "__main__":
    main()
