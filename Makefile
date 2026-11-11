.PHONY: test ingest snapshot restore classify daily label eval-classify compare eval-agent tables chat web up web-up down logs

test:
	python -m pytest -q

ingest:
	python -m src.ingest

snapshot:
	python -m src.ingest --snapshot

restore:
	python -m src.ingest --restore

classify:
	python -m src.run_daily --no-ingest

daily:
	python -m src.run_daily --model baseline

label:
	python -m eval.label_cli

eval-classify:
	python -m eval.eval_classify --models phi qwen3

compare:
	python -m eval.compare

eval-agent:
	python -m eval.eval_agent --models phi qwen3

tables:
	python -m eval.make_tables

chat:
	python -m src.chat --trace

web:
	python -m src.web

up:
	docker compose up -d --build scheduler

web-up:
	docker compose up -d --build web

down:
	docker compose down

logs:
	docker compose logs -f --tail 50
