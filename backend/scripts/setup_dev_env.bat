@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
pip install -r requirements-dev.txt
echo Development environment set up. Activate with: .venv\Scripts\activate.bat
