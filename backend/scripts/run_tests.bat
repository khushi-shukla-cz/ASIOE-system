@echo off
REM Simple wrapper to run backend tests in the repo venv
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)
python -m pytest backend -q
