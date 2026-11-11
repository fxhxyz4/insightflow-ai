# Contributing / Running the project

## 1. Setup

The project targets **Python 3.12**. Other versions may have no prebuilt `llama-cpp-python` wheels, and pip would then try to compile it.

```zsh
sudo pacman -S uv
uv venv --seed --python 3.12 .venv

# or with plain venv, if python3.12 is installed
python3.12 -m venv .venv
```

### Activate the virtual environment

Do this in **every new terminal** before running anything.

```zsh
source .venv/bin/activate              # bash / zsh
source .venv/bin/activate.fish         # fish
.venv\Scripts\activate                 # Windows (cmd / PowerShell)

python --version                       # should print 3.12.x
deactivate                             # leave the environment
```

### Install dependencies

```zsh
pip install -r requirements.txt
python -c "import llama_cpp, sklearn, feedparser, pandas; print('ok', llama_cpp.__version__)"
```

`requirements.txt` starts with `--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`,
so `llama-cpp-python` is installed from a prebuilt CPU wheel (no compilation).

In VS Code: `Ctrl+Shift+P` -> *Python: Select Interpreter* -> `.venv`.

## 2. Typical workflow

```zsh
python -m src.ingest --check           # test the RSS feeds, saves nothing
python -m src.ingest                   # collect news into data/news.db
python -m src.ingest --snapshot        # freeze the data: data/snapshot/<date>.jsonl
python -m src.ingest --restore         # fresh clone: rebuild data/news.db from the latest snapshot
python -m src.run_daily --no-ingest    # classify the restored news (baseline) and build the digest, no collection

python -m eval.make_labelset           # build eval/labelset.csv (once; never overwritten)
python -m eval.label_cli               # label by hand: 1-6 categories, 0 other, b back, q quit

python -m eval.eval_classify --models phi --limit 20   # quick trial, saved to eval/results/trial/ (downloads the model on first run)
python -m eval.eval_classify --models phi qwen3        # full comparison with the TF-IDF baseline
python -m eval.compare                                 # confidence intervals of the differences (paired bootstrap)
python -m eval.eval_agent --models phi qwen3           # agent with tools vs the same model without tools (needs classified news)
python -m eval.make_tables                             # tables for the note: docs/results_tables_ua.md

python -m src.chat --trace             # talk to the agent, show Thought/Action/Observation steps
python -m src.web                      # web interface: http://127.0.0.1:8000 (digest + agent with live steps)
python -m src.run_daily                # collect + classify + write reports/latest.md (no LLM needed)
python -m src.run_daily --model phi --digest-model phi   # same, with LLM classification and summaries
```

Results are written to `eval/results/` (JSON per method and `summary_*.csv`).
The notebook `notebooks/insightflow.ipynb` only calls these modules and displays the results:

```zsh
python -m ipykernel install --user --name insightflow
jupyter lab
```

## 3. Models

Defined in `config/runtime.py` (`MODELS`). Default: `phi`.

| Name | Model | Note |
|---|---|---|
| `phi` | Phi-4-mini-instruct, Q4_K_M | used in the course, default |
| `qwen3` | Qwen3-4B, Q4_K_M | safe second model for the comparison |
| `qwen35` | Qwen3.5-4B, Q4_K_M | newer; may need a newer `llama-cpp-python` |

GGUF files are downloaded from Hugging Face on first use and cached (`~/.cache/huggingface`, or `./models` in Docker).
The project runs on CPU only.

## 4. Run on a schedule

### systemd (Linux, no Docker)

See `deploy/systemd/README.md`. In short:

```zsh
mkdir -p ~/.config/systemd/user
cp deploy/systemd/insightflow.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now insightflow.timer
systemctl --user list-timers | grep insightflow
```

### Docker

SQLite is just a file, so there is no separate database container: `data/news.db` lives in `./data`
and is mounted into the container together with `./reports` and `./models`.

```zsh
docker compose up -d --build scheduler        # scheduler: runs at RUN_AT (07:00 and 19:00 by default)
docker compose up -d --build web              # web interface at http://localhost:8000
WEB_PORT=8081 docker compose up -d web        # another host port, if 8000 is taken
docker compose logs -f scheduler              # follow the logs
docker compose run --rm chat                  # interactive agent in a container
docker compose run --rm eval python -m eval.eval_classify --models phi
docker compose --profile tools up db-browser  # optional: browse news.db at http://localhost:8080
docker compose down                           # stop
```

Settings (classification model, summary model, run times, timezone) are environment variables in `docker-compose.yml`:
`MODEL`, `DIGEST_MODEL`, `RUN_AT`, `TZ`. The web service also reads `WEB_MODEL` (default model of the agent), `HOST` and `PORT`.

## 5. Tests

```zsh
python -m pytest -q
```

The tests use a fake LLM (`tests/fakes.py`), so they need neither a model nor network access.
The same tests run in CI (`.github/workflows/ci.yml`).
