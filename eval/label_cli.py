import pandas as pd

from config.config import CATEGORIES, ROOT

PATH = ROOT / "eval" / "labelset.csv"
KEYS = {str(i): c for i, c in enumerate(CATEGORIES, 1)}
KEYS["0"] = "other"
LEGEND = "  ".join(f"{k}={v}" for k, v in KEYS.items()) + "  b=назад  q=вийти"


def main():
    df = pd.read_csv(PATH, dtype=str, keep_default_na=False)
    todo = list(df.index[df["label"] == ""])
    print(f"Лишилось розмітити: {len(todo)} з {len(df)}")
    pos, show = 0, True
    while pos < len(todo):
        i = todo[pos]
        if show:
            row = df.loc[i]
            print(f"\n[{pos + 1}/{len(todo)}] {row['title']}\n{row['summary']}\n{LEGEND}")
        show = True
        try:
            ans = input("> ").strip().lower()
        except EOFError:
            ans = "q"
        if ans == "q":
            print("Збережено. Продовжите пізніше тією ж командою.")
            return
        if ans == "b":
            if pos == 0:
                print("Це перша новина цієї сесії, назад нікуди.")
                show = False
                continue
            pos -= 1
            df.loc[todo[pos], "label"] = ""
            df.to_csv(PATH, index=False)
            continue
        if ans in KEYS:
            df.loc[i, "label"] = KEYS[ans]
            df.to_csv(PATH, index=False)
            pos += 1
        else:
            print(f"Невідома клавіша '{ans}'. Допустимі: {', '.join(KEYS)}, b, q.")
            show = False
    print("Усе розмічено.")


if __name__ == "__main__":
    main()
