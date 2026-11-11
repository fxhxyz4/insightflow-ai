import os
import time
from datetime import datetime, timedelta


def next_run(times, now):
    candidates = []
    for t in times:
        hour, minute = map(int, t.strip().split(":"))
        moment = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if moment <= now:
            moment += timedelta(days=1)
        candidates.append(moment)
    return min(candidates)


def main():
    from src import run_daily

    times = os.environ.get("RUN_AT", "07:00,19:00").split(",")
    model = os.environ.get("MODEL", "baseline")
    digest_model = os.environ.get("DIGEST_MODEL", "none")

    def job():
        try:
            run_daily.run(model, digest_model)
        except Exception as e:
            print(f"[{datetime.now():%F %T}] помилка запуску: {type(e).__name__}: {e}", flush=True)

    if os.environ.get("RUN_ON_START") == "1":
        job()
    while True:
        target = next_run(times, datetime.now())
        print(f"[{datetime.now():%F %T}] наступний запуск: {target:%F %T}", flush=True)
        time.sleep(max((target - datetime.now()).total_seconds(), 1))
        job()


if __name__ == "__main__":
    main()
