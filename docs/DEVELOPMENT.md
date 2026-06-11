# Development Setup

1. Create and activate virtual environment:

```
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows
```

2. Install runtime and dev dependencies:

```
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
```

3. Run tests:

```
python -m pytest backend -q
```
