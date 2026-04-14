---
name: sign-off
description: >
  Secure conversation closing ritual. Triggers when the user types /sign-off,
  "sign off", "save and quit", "wrap up", "let's call it", "save what we discussed",
  "don't want to lose today's progress", "summarize and close", or any variant
  indicating they want to end the conversation while preserving important context.
  Use this skill whenever the user wants to leave in an orderly way, saving relevant
  information for future sessions. Even casual farewells like "gotta go, save this"
  or "heading out" combined with save intent should trigger this skill.
---

# Sign-Off: Secure Conversation Closing

## What it does

When the user signals they want to close the session, Claude runs a closing protocol that:

1. **Scans** the full conversation
2. **Extracts** what's worth remembering
3. **Saves** to a persistent session log file
4. **Updates** the project's CLAUDE.md if relevant context was found
5. **Presents** a closing summary to the user
6. **Says goodbye** in a warm, personalized way

## Execution protocol

### Step 1: Conversation analysis

Review the entire thread and identify these categories:

- **Decisions made**: Anything the user decided or agreed upon
- **New personal data**: Name, job, preferences, location, projects, etc.
- **Pending tasks**: Things left to do or that the user mentioned they would do
- **Claude preferences**: How the user likes Claude to respond (tone, format, language)
- **Project context**: What they're working on, current state, next steps
- **Problems solved**: Solutions found that could be useful in future sessions

### Step 1.5: Session Balance Analysis

**Analysis**

Classify conversation content into these categories (must sum to 100%, 5% increments minimum):

- `technical` → coding, debugging, architecture, tools, infrastructure
- `planning` → strategy, decisions, roadmap, prioritization
- `learning` → research, concepts, documentation, exploration
- `admin` → legal, taxes, contracts, business operations
- `creation` → content, writing, design, publishing
- `comms` → emails, messages, outreach, coordination

**Persistence**

Append balance data to `~/.claude/session-balance.json` (a JSON array). Never overwrite — always append a new object:

```json
{"date": "YYYY-MM-DD", "project": "<dir>", "technical": 40, "planning": 30, "creation": 20, "admin": 10}
```

If the file doesn't exist, create it as `[]` and then append. Include only categories with non-zero scores.

Also include the balance line inside the session log entry (Step 2):

```
**Balance:** technical=40% planning=30% creation=20% admin=10%
```

**Output format**

Render in the closing summary (Step 5) as a minimal ASCII bar chart. Use filled block `█` and light block `░` scaled to 20 chars width. Omit any category scoring 0%. No color codes, no emojis — terminal-safe only.

```
Session Balance
───────────────────────────────
technical  ████████████░░░░░░░░  40%
planning   ██████████░░░░░░░░░░  30%
creation   ████████░░░░░░░░░░░░  20%
admin      ████░░░░░░░░░░░░░░░░  10%
───────────────────────────────
```

### Step 2: Save to session log

Append a new entry to `~/.claude/session-log.md`. Create the file if it doesn't exist.

Each entry should follow this format:

```markdown
---

## Session: YYYY-MM-DD HH:MM

**Project:** [project name or directory]

**Summary:**
- [Key point 1]
- [Key point 2]

**Decisions:**
- [Decision 1]

**Pending:**
- [ ] [Task 1]
- [ ] [Task 2]

**Notes:**
- [Anything else worth remembering]
```

### Step 3: Auto-setup session recovery (first run only)

Check if `~/.claude/CLAUDE.md` exists and contains a `## Session Recovery` section. If it doesn't, append the following block:

```markdown

## Session Recovery
At the start of every conversation, read ~/.claude/session-log.md to recover context from previous sessions. Use it to understand what the user was working on, pending tasks, and key decisions. Proactively mention relevant context when it applies.
```

This ensures that all future Claude Code sessions will automatically read the session log and pick up where the user left off. This step only runs once.

### Step 4: Update project CLAUDE.md (if applicable)

If the conversation produced project-specific context that would help future sessions (architecture decisions, conventions, workflow preferences), append it to the project's `CLAUDE.md` file under a `## Session Notes` section.

Only add information that is:
- **Project-specific**: Directly related to the current codebase
- **Lasting**: Not ephemeral or single-use
- **Actionable**: Helps Claude work better on this project next time

If no project-specific context was found, skip this step.

### Step 5: Present closing summary

Show the user a brief, friendly summary:

```
## Session Summary

**Saved to session log:**
- [short list of what was logged]

**Updated CLAUDE.md:**
- [what was added, or "No project-specific updates"]

**Pending items:**
- [tasks or to-dos, if any]

**Until next time!**
[Brief, warm goodbye — personalized if there's context]
```

## How context is recovered

When starting a new session, Claude can read:
- `~/.claude/session-log.md` for past session summaries
- The project's `CLAUDE.md` for project-specific context saved in previous sessions

This gives continuity across sessions without relying on memory APIs.

## Important rules

- **Never save sensitive information**: passwords, tokens, API keys, specific financial data, ID numbers
- **No duplicates**: Check session-log.md before appending to avoid repeating the same info
- **Ask when in doubt**: If unsure whether something is worth saving, ask the user
- **Match language**: Respect the language the user used during the conversation
- **Trivial sessions**: If the conversation was light (just a greeting, a simple question), don't invent things to save. Say something like "Light session today — nothing new to save. See you next time!"
- **Brevity**: The closing summary should be short. No more than 10 lines.
- **Session log size**: If `~/.claude/session-log.md` exceeds 200 lines, archive older entries to `~/.claude/session-log-archive.md` keeping only the last 50 entries in the main file.
