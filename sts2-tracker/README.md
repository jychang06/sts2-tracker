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

See [Getting statistics](#getting-statistics) for floor, card, act and other filters.

Use `--db` before the subcommand to choose the database file
(default: `sts2.db` in the current folder):

```bat
sts2 --db C:\data\sts2.db scan "C:\path\to\run\files"
```

Re-scanning is safe: runs are deduplicated by start time + seed.

## Getting statistics

Run `sts2 scan <folder>` first so the database is populated. All commands read
`sts2.db` in the current folder unless you pass `--db` (before the subcommand).

### How the data is organized

Every time the game offers you something, that offer is recorded with what was
offered and what you picked. `--kind` chooses which offers to analyze:

| `--kind` | What it covers |
|---|---|
| `card` | Card rewards after fights (skipping counts as offered, not picked) |
| `relic` | Relic rewards (elites, treasure, events) |
| `potion` | Potion rewards |
| `ancient` | Ancient/Neow-style starting choices |
| `rest` | Rest-site choices (Heal/Smith; offers are assumed, see Notes) |
| `shop_card`, `shop_relic`, `shop_potion` | Shop stock vs. what you bought |

Output columns: `offered` (times it appeared), `picked`, `pick_rate`
(picked / offered), and a 95% confidence interval (`ci_low`, `ci_high`). With few
runs the interval is wide, so a 100% pick rate from 1 offer means very little.

### By character

```bat
sts2 report --character CHARACTER.SILENT
sts2 winrate --by character
```

Character ids look like `CHARACTER.SILENT`. To list the ones in your data, run
`sts2 winrate --by character`.

### By floor or act

Floors are numbered 1, 2, 3... continuously across the whole run (they don't
reset each act). Act lengths vary, so use `--act` for act-level questions.

```bat
sts2 report --floor 1-10            :: floors 1 to 10
sts2 report --floor 12              :: exactly floor 12
sts2 report --floor 30-             :: floor 30 onward
sts2 report --act 2 --kind relic    :: relic picks in act 2
```

### By card, relic or potion

`--item` is a case-insensitive substring of the id, so you don't need the prefix:

```bat
sts2 report --item backflip
sts2 report --item ring --kind relic
sts2 report --item whip --kind shop_card
```

The result is how often it was offered and how often you took it. Use
`--floor` or `--act` with it to see whether you take a card more early or late.

### By ascension or game build

```bat
sts2 report --ascension 3
sts2 report --build v0.113.1
sts2 winrate --by ascension
sts2 winrate --by build
```

Balance patches change card and relic strength, so filtering to one build
avoids mixing patches when you compare things.

### Combining filters and trimming output

Filters combine, so this is "Silent card picks in act 1 at ascension 3, only cards
offered at least 5 times":

```bat
sts2 report --character CHARACTER.SILENT --act 1 --ascension 3 --min-offered 5
```

`--limit N` controls how many rows print (default 30). `sts2 hp` prints average
HP fraction and damage taken by floor.

### Other questions (Python)

For anything the commands don't cover, use the same functions from Python:

```python
from sts2_tracker.db import connect
from sts2_tracker.analysis import pick_rates, win_rate_by_pick
import pandas as pd

con = connect("sts2.db")

# Silent card picks in act 1, offered at least 5 times
pick_rates(con, "card", character="CHARACTER.SILENT", act=1, min_offered=5)

# Win rate of runs that picked each card (min 5 runs). Naive: see caveat below.
win_rate_by_pick(con, "card", min_runs=5)

# Cards you remove most often, from the deck_changes table
pd.read_sql_query(
    "SELECT card, COUNT(*) n FROM deck_changes WHERE action='remove' "
    "GROUP BY card ORDER BY n DESC", con)
```

The tables are `runs`, `choices`, `options` (one row per offered item),
`floors` (HP, gold and room per floor) and `deck_changes` (removals, transforms,
upgrades, downgrades).

### Interpreting results

- Pick rate is picked / times offered, not picked / runs.
- Win rate by pick is confounded: strong players pick different things and
  survive to see more choices. Don't read it as "this card wins games."
- Abandoned runs are excluded from `sts2 winrate`.
- Check the confidence interval before trusting a number; small samples swing a lot.

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
