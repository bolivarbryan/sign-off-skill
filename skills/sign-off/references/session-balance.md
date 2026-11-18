# Session balance (Step 1.5)

## Categories

Classify the conversation into these categories. Scores use 5% increments and must
sum to 100%.

| Category | Covers |
|---|---|
| `technical` | coding, debugging, architecture, tools, infrastructure |
| `planning` | strategy, decisions, roadmap, prioritization |
| `learning` | research, concepts, documentation, exploration |
| `admin` | legal, taxes, contracts, business operations |
| `creation` | content, writing, design, publishing |
| `comms` | emails, messages, outreach, coordination |

## Persistence

Append one object to `~/.claude/session-balance.json` (a JSON array). Never overwrite
existing data. If the file does not exist, create it as `[]` first. Include only
non-zero categories.

```json
{"date": "YYYY-MM-DD", "project": "<dir>", "technical": 40, "planning": 30, "creation": 20, "admin": 10}
```

Add the same split to the session-log entry (Step 2):

```
**Balance:** technical=40% planning=30% creation=20% admin=10%
```

## Rendering (Step 5)

A minimal ASCII bar chart, 20 characters wide, using `█` (filled) and `░` (empty).
Omit categories at 0%. No colors, no emojis: terminal-safe only.

```
Session Balance
───────────────────────────────
technical  ████████████░░░░░░░░  40%
planning   ██████████░░░░░░░░░░  30%
creation   ████████░░░░░░░░░░░░  20%
admin      ████░░░░░░░░░░░░░░░░  10%
───────────────────────────────
```
