.PHONY: docs tests
PYTHON_FILES = cassis tests

# Dependencies
dependencies:
	poetry install

# Tests
unit-tests:
	poetry run py.test --cov=cassis --cov-branch --cov-fail-under=90 tests

tests: unit-tests integ-tests

coverage:
	poetry run py.test --cov=cassis --cov-branch --cov-fail-under=90 --cov-report=xml:coverage.xml -m "not performance" tests

# Static analysis/linting
format:
	poetry run ruff format $(PYTHON_FILES)

lint:
    # stop the build if there are Python syntax errors or undefined names
	poetry run ruff check --select=E9,F63,F7,F82 --output-format=full $(PYTHON_FILES)
    # exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
    # flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	poetry run ruff check --exit-zero $(PYTHON_FILES)

# Docs
docs:
	cd docs && make html

# Building and publishing
build: unit-tests lint
	poetry build

publish: build
	poetry publish

# CI

ci-publish:
	poetry publish --build --username "${PYPI_USERNAME}" --password "${PYPI_PASSWORD}" --no-interaction

ci-bump-version:
	poetry run bump2version patch
