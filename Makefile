test:
	python -m pytest tests/

black:
	black -l 120 cassis/
	black -l 120 tests/
