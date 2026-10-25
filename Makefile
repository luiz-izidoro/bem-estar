.PHONY: install dev check test lint format format-check type architecture migrate api worker mcp dashboard-build

install:
	python -m pip install -e '.[dev]'

dev:
	uvicorn bemestar.interfaces.api.app:create_app --factory --reload --host 127.0.0.1 --port 8787

api:
	uvicorn bemestar.interfaces.api.app:create_app --factory --host 127.0.0.1 --port 8787

worker:
	python -m bemestar.interfaces.worker

mcp:
	uvicorn bemestar.interfaces.mcp.app:create_app --factory --host 127.0.0.1 --port 8788

migrate:
	alembic upgrade head

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts

format-check:
	ruff format --check src tests scripts

type:
	mypy

architecture:
	python scripts/verify_architecture.py

test:
	pytest

check: lint format-check type architecture test

# Requires Node 22+
dashboard-build:
	cd dashboard && npm ci && npm run build
