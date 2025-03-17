all: fmt_linter check_types pytests

fmt_linter:
	uv run ruff check --select I --fix .
	uv run ruff format . --no-cache
	@echo '[OK] Formatters went through successfully'
	uv run ruff check . --no-cache --fix
	@echo '[OK] Linters checks passed successfully'

check_types:
	mypy src

pytests:
	uv run pytest tests -vv -s --cov --cov-report=term-missing

init_db:
	export PYTHONPATH="${PWD}:${PYTHONPATH}"
	uv run main.py --init-db
start:
	export PYTHONPATH="${PWD}:${PYTHONPATH}"
	uv run main.py
