.PHONY: docs tests
PYTHON_FILES = cassis tests

clean:
	rm -Rf build dkpro_cassis.egg-info dist

# Dependencies
pin:
	rm requirements.txt requirements-dev.txt requirements-doc.txt
	pip-compile -o requirements.txt pyproject.toml
	pip-compile --extra dev -o requirements-dev.txt pyproject.toml
	pip-compile --extra doc -o requirements-doc.txt pyproject.toml

init:
	pip install --upgrade pip pip-tools
	pip install setuptools setuptools_scm wheel

dependencies: init
	pip-sync requirements.txt requirements-dev.txt

# Tests
unit-tests:
	python -m pytest --cov=cassis --cov-branch --cov-fail-under=90 tests

tests: unit-tests integ-tests

coverage:
	python -m pytest --cov=cassis --cov-branch --cov-fail-under=90 --cov-report=xml:coverage.xml -m "not performance" tests

# Static analysis/linting
format:
	ruff format $(PYTHON_FILES)

lint:
    # stop the build if there are Python syntax errors or undefined names
	ruff check --select=E9,F63,F7,F82 --output-format=full $(PYTHON_FILES)
    # exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
    # flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	ruff check --exit-zero $(PYTHON_FILES)

# Docs
docs:
	pip-sync requirements-doc.txt
	cd docs && make html

# Building and publishing
build: unit-tests lint
	python -m build
