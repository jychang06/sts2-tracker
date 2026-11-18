# sts2-tracker

Parse Slay the Spire 2 `.run` files into a SQLite database and analyze player
choices (card/relic/potion pick rates with Wilson confidence intervals, HP curves).

**Status:** early. The game is in early access and the run format may change.
Verified against `schema_version` 8 (build v0.98.3) and 11 (build v0.113.1). Older
versions are skipped with a logged message. Newer versions parse best-effort and log a
warning, plus a warning for any unrecognized per-floor key, so format drift is visible
rather than silent.

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

- Shops: the game marks every shop card as not picked, and `card_choices` lists only the
  *unbought* stock. Purchased cards come from `cards_gained` (inferred from 10 purchases
  across 2 runs, none of which appeared in the offered list). The full shop stock is
  reconstructed as remaining + bought.
- Card removals, transforms, upgrades and downgrades are stored in `deck_changes`.
- Rest-site offers are not recorded in the file; Heal/Smith is assumed.
- Naive win-rate-by-pick is confounded by player skill; control for character,
  ascension and build before drawing conclusions.

## Tests

```bat
pip install -e .[dev]
pytest
```
