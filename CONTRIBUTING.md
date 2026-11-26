# Contributing to BatSignal

Use Windows and Python 3.12 or 3.13 with Tkinter. Create a virtual environment, then install development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Before submitting a pull request:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
```

Keep collection logic independent of Tkinter. Worker threads communicate through a queue; only the main thread may update widgets. New collectors should raise WiFiError with an actionable message.

Preserve support for existing JSON files. Validate imported values before using them in charts or exports. Add regression tests for behavior changes, especially cancellation, disconnection, file failures, and schema changes.

Report your Windows language, Python version, reproduction steps, and relevant error messages. Remove personal SSIDs, BSSIDs, room names, and paths from shared files.

To build a portable Windows package, run:

```powershell
.\.venv\Scripts\python.exe scripts/build_windows.py
```

The result is dist/BatSignal-Windows.zip. Extract the entire archive before launching BatSignal.exe. Build artifacts and local survey data must not be committed.

The CI workflow runs tests on Windows with Python 3.12 and 3.13, then builds an artifact. It does not publish a GitHub Release automatically.

Contributions are made under the project's Apache-2.0 license.
