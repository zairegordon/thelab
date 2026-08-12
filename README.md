# The Lab

A lightweight fantasy football draft helper that makes it easy to compare players before you pick them.

## Features

- Compare two players side by side
- Evaluate projected fantasy points, floor, ceiling, and risk
- Highlight which player has the stronger draft value
- Use built-in player data for quick comparisons

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
