# Developer setup

Steps to set up a development environment:

1. Create virtualenv:

```
python -m venv backend/.venv
backend/.venv/Scripts/activate.bat  # Windows
source backend/.venv/bin/activate    # Unix
```

2. Install dependencies:

```
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
```

3. Run tests:

```
python -m pytest backend -q
```
