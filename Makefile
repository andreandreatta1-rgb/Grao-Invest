lint:
	python -m ruff check .

typecheck:
	python -m mypy services/api/app

test:
	python -m pytest

check:
	python scripts/check.py

run:
	python -m uvicorn app.main:app --app-dir services/api --reload
