# The Lab

A lightweight fantasy football draft helper that makes it easy to compare players before you pick them.

## Features


## Run the app

```bash
pip install -r requirements.txt
python app.py
```

The app runs on `http://127.0.0.1:5000` by default.

Optional native player-data libraries are disabled by default for maximum compatibility.
If you want optional headshot enrichment from those libraries, set:

```bash
ENABLE_OPTIONAL_PLAYER_DATA=1
```

## Run the tests

```bash
pytest
```

Browser UI tests

Install the Playwright browser once after installing the requirements:

```bash
python -m playwright install chromium
```

Run the full test suite, including the browser UI tests:

```bash
pytest
```

For a reliable full-suite report, use the project runner. It saves the complete
pytest output under `test-reports/` and prints `PYTEST_EXIT_CODE`:

```powershell
$env:PLAYWRIGHT_HEADED = "1"
.\.venv\Scripts\python.exe .\run_test_suite.py
```
