# sts2-tracker

Parse Slay the Spire 2 `.run` files into a SQLite database and analyze player
choices (card/relic/potion pick rates with Wilson confidence intervals, HP curves).

**Status:** early. The game is in early access and the run format may change.

## Install

Requires Python 3.10+.

**Windows (Command Prompt):**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bat
sts2 scan "C:\path\to\run\files"
sts2 report --kind card
sts2 report --kind relic --character CHARACTER.SILENT
```

Use `--db` before the subcommand to choose the database file
(default: `sts2.db` in the current folder):

```bat
sts2 --db C:\data\sts2.db scan "C:\path\to\run\files"
```

Re-scanning is safe: runs are deduplicated by start time + seed.

## Notes

- Shop purchases are derived from `bought_*` / `cards_gained` because the game
  marks every shop offer as not picked.
- Rest-site offers are not recorded in the file; Heal/Smith is assumed.
- Naive win-rate-by-pick is confounded by player skill; control for character,
  ascension and build before drawing conclusions.

## Tests

```bat
pip install -e .[dev]
pytest
```
