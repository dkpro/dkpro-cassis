PYTHON_FILES = cassis tests

test:
	python -m pytest -m "not performance" tests/

format:
	black -l 120 cassis/
	black -l 120 tests/
	isort --profile black $(PYTHON_FILES) --multi-line=3 --trailing-comma --force-grid-wrap=0 --use-parentheses --line-width=120


html:
	cd docs && make html