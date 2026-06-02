PYTHON=python

test:
	$(PYTHON) -m pytest backend -q

lint:
	flake8

format:
	black .
