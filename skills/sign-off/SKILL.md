---
name: sign-off
description: >-
  Orderly end-of-session ritual: scans the conversation, saves decisions, pending
  tasks and project context to a per-project "memory card" session log, updates the
  project's CLAUDE.md, optionally drafts a daily progress report, then says goodbye.
  Use when the user wants to end the conversation without losing context.
when_to_use: >-
  Triggers on /sign-off, "sign off", "save and quit", "wrap up", "let's call it",
  "save what we discussed", "don't want to lose today's progress", "summarize and
  close", "gotta go, save this", "heading out" (with save intent), and Spanish
  variants such as "cierra la sesión", "guarda y salimos", "guarda todo y cerramos",
  "terminamos por hoy", "me voy, guarda esto".
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/memcard.py *)
license: MIT
---

# Sign-Off: orderly session closing

When the user signals they are done, run this protocol in order. Each step is short;
details live in `references/` and are loaded only when a step needs them.

| Step | What | Reference |
|---|---|---|
| 1 | Analyze the conversation | — |
| 1.5 | Session balance (category split + ASCII chart) | [session-balance.md](references/session-balance.md) |
| 2 | Save the entry to the memory card via `memcard.py` | [session-log.md](references/session-log.md) |
| 3 | First run only: add Session Recovery to `~/.claude/CLAUDE.md` | — |
| 4 | Update the project's `CLAUDE.md` if there is lasting context | — |
| 4.5 | Draft a daily progress report (Gmail draft, never sent) | [daily-report.md](references/daily-report.md) |
| 5 | Closing summary and goodbye | — |

## Step 1: Conversation analysis

Review the whole thread and extract:

- **Decisions made**: anything the user decided or agreed on
- **New personal data**: name, job, preferences, location, projects
- **Pending tasks**: things left to do, or that the user said they would do
- **Claude preferences**: how the user likes responses (tone, format, language)
- **Project context**: what they are working on, current state, next steps
- **Problems solved**: solutions likely to be useful again

## Step 1.5: Session balance

Score the session across `technical`, `planning`, `learning`, `admin`, `creation`,
`comms` (5% steps, sum 100%), append the result to `~/.claude/session-balance.json`,
add a `**Balance:**` line to the entry, and render a bar chart in Step 5. Read
[references/session-balance.md](references/session-balance.md) for the exact format.

## Step 2: Save to the memory card

The session log is a memory card: `~/.claude/session-log.md` holds one slot per
project (max 15) with that project's latest session; every overwritten or evicted
save goes to `~/.claude/session-log-history.md`.

1. Check the current slot first to avoid duplicates:
   `${CLAUDE_SKILL_DIR}/scripts/memcard.py show "$PWD"`
2. Write the entry (format in [references/session-log.md](references/session-log.md);
   the `## Session: YYYY-MM-DD HH:MM` header is mandatory) to a temp file.
3. Save it:
   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/memcard.py save "$PWD" /path/to/entry.md
   ```

The script moves the project's previous save to history, adds a `**Dir:**` line if
missing, and rebuilds the slot table. Never edit the card or the history by hand,
except to append the `**Report:**` line in Step 4.5. If the script fails, stop and
tell the user. Other commands: `list`, `show <dir>`, `index`, `--help`.

## Step 3: Session recovery setup (first run only)

If `~/.claude/CLAUDE.md` has no `## Session Recovery` section, append:

```markdown

## Session Recovery
At the start of every conversation, read ~/.claude/session-log.md. It is a memory card: one slot per project with that project's latest session, and a slot table at the top. The slot whose **Dir:** matches the current directory is the primary context (pending tasks, decisions); the other slots give the overview of what else is in flight. Older sessions live in ~/.claude/session-log-history.md — do not read it whole; grep it by project or date only when the slot is not enough.
```

## Step 4: Update the project CLAUDE.md (if applicable)

If the session produced context that is **project-specific**, **lasting**, and
**actionable** (architecture decisions, conventions, workflow preferences), append it
to the project's `CLAUDE.md` under `## Session Notes`. Otherwise skip.

## Step 4.5: Daily progress report

If the session produced real work and the project has a git remote, draft a
scrum-daily-style report to the stakeholder bound to this project, as a **Gmail
draft only**. Follow [references/daily-report.md](references/daily-report.md) for
skip conditions, recipient selection, content sources, template, and state updates.

## Step 5: Closing summary

```
## Session Summary

**Saved to session log:**
- [short list of what was logged]

**Updated CLAUDE.md:**
- [what was added, or "No project-specific updates"]

**Report drafted:**
- [To: <name> <email> — Gmail draft id <id>  OR  Skipped (<reason>)  OR  Failed (<reason>)]

**Pending items:**
- [tasks or to-dos, if any]

[Session Balance chart from Step 1.5]

**Until next time!**
[Brief, warm goodbye — personalized if there's context]
```

## Rules

- **Never save secrets**: passwords, tokens, API keys, specific financial figures, ID
  numbers. The same applies to report drafts.
- **No duplicates**: check the slot (`memcard.py show "$PWD"`) before saving.
- **Ask when in doubt** whether something is worth saving.
- **Match the user's language** in the summary and goodbye.
- **Light sessions**: if nothing substantive happened, don't invent content. Say
  something like "Light session today — nothing new to save. See you next time!"
- **Brevity**: the closing summary stays short.
- **Never auto-send reports**: Step 4.5 creates a draft; the user sends it.
- **The card is script-owned**: every save goes through `memcard.py save`; never
  truncate or rewrite the history by hand.

## How context is recovered

A new session reads `~/.claude/session-log.md` (small, always current), greps
`~/.claude/session-log-history.md` only when needed, and loads the project's
`CLAUDE.md`. That gives continuity across sessions without a memory API.
