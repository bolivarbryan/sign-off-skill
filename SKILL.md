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

**Remote:** [host:org/repo — omit this line if no git remote is set]

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

**Deriving `**Remote:**`:** Run `git remote get-url origin` from the project directory. Normalize the result to `host:org/repo`:
- Strip leading `https://` or `git@` and trailing `.git`
- Replace the first `/` after the host with `:` (so `github.com/foo/bar` becomes `github.com:foo/bar`)
- For SSH URLs like `git@github.com:foo/bar.git`, the normalization already leaves `github.com:foo/bar`

If `git remote get-url origin` fails or returns empty, omit the `**Remote:**` line entirely. A later `**Report:**` trailing line may be appended by Step 4.5 — see that step for its format.

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

### Step 4.5: Generate & draft progress report

If the session produced real work, draft a scrum-daily-style progress report and send it to the stakeholder bound to this project. The draft is always created in Gmail's Drafts folder — never auto-sent.

#### 4.5.1 Preconditions (skip conditions)

Run these checks in order. If any triggers, skip the entire step and record the skip reason for the Step 5 summary.

1. **Resolve `remote_key`:** run `git remote get-url origin` in the current directory. If it fails or returns empty, skip with reason `"No git remote detected"`. Normalize the URL to `host:org/repo` using the same rules as Step 2's `**Remote:**` derivation.

2. **Light-session check:** skip with reason `"Light session"` if ALL of the following are true about this conversation:
   - Step 1 produced no Decisions
   - Step 1 produced no Pending tasks
   - Step 1 produced no Project context

   This mirrors the "Trivial sessions" rule in the Important rules section — if there's nothing substantive to save, there's nothing to report.

3. **Load `~/.claude/report-recipients.json`:** if missing, create it with `{"recipients": [], "project_defaults": {}}`. If present but unparseable, skip with reason `"recipients file corrupted — hand-edit required"`.

#### 4.5.2 Recipient selection

**Case A — no `project_defaults[remote_key]` exists:**

Ask the user:

```
First report for this project. Who should it go to?

Saved recipients:
  1) <name> <email>
  2) <name> <email>
  ...

  [A] Add new recipient
  [S] Skip report this time

Choice:
```

- `[1..N]` → bind the chosen recipient as the project default. Continue to 4.5.3.
- `[A]` → prompt "Name:" then "Email:". Run the email sanity check (4.5.2.1). On failure, re-prompt. On success, append to `recipients[]`, de-duplicating by email (if the email already exists, update the name in-place with last-write-wins). Bind as default. Continue.
- `[S]` → exit Step 4.5. Do NOT write `project_defaults[remote_key]`. Skip reason: `"User opted out (no default bound)"`.

**Case B — a default already exists:**

Ask:

```
Drafting report to <name> <email>.
  [Enter] Confirm
  [C]     Change recipient
  [S]     Skip this time
```

- `[Enter]` → continue to 4.5.3.
- `[C]` → run the Case A picker. The chosen recipient overwrites `project_defaults[remote_key].recipient_email`.
- `[S]` → exit. Do NOT update `last_reported_at`. Skip reason: `"User opted out"`.

##### 4.5.2.1 Email sanity check

Accept if the email matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` (one or more non-`@`, non-whitespace chars, then `@`, then same, then `.`, then same). This catches typos without enforcing RFC 5322.

#### 4.5.3 Content gathering

Two sources, both scoped to the current `remote_key`:

1. **Current conversation** — extract:
   - Concrete tasks completed this session ("done today")
   - Open items mentioned ("next up")
   - Blockers surfaced
   - Decisions agreed to
   - An overall status read (on track / blocked on X / ahead)

2. **Recent session-log entries** from `~/.claude/session-log.md`. Select entries where ALL apply:
   - The `**Remote:**` line equals `remote_key` exactly
   - The entry's `## Session: YYYY-MM-DD HH:MM` header parses cleanly
   - The parsed timestamp (treated as local time, converted to UTC) is strictly greater than `last_reported_at`

   If `last_reported_at` is null or missing, take the 5 most recent matching entries instead.

Entries missing a `**Remote:**` line or with an unparseable header are always excluded — safe default, no back-fill needed.

#### 4.5.4 Report template

Render this template as plain text. Omit the `Blockers` and `Decisions` sections entirely (header included) when they have no bullets — do NOT print "None".

```
Subject: [Daily Report] <display_name> — <YYYY-MM-DD>

Hi <recipient-first-name>,

Status: <one-line project status>

Done today
- <bullet>
- <bullet>

Next up
- <bullet>
- <bullet>

Blockers
- <bullet>

Decisions
- <bullet>

—
<user-display-name>
(Auto-drafted via Claude Code sign-off)
```

Rendering rules:
- `<recipient-first-name>` = first whitespace-delimited token of the recipient `name` field
- `<display_name>` = value stored in `project_defaults[remote_key].display_name`, set at bind time to the basename of `git rev-parse --show-toplevel`
- `<user-display-name>` = `git config user.name`, fallback `"me"` if unset
- Consolidate bullets to a max of ~8 per section
- Strip sensitive content before rendering: passwords, tokens, API keys, secret values, specific financial figures, government ID numbers (same rule as the Important rules section)

#### 4.5.5 Create Gmail draft

Call the Gmail MCP:

```
mcp__claude_ai_Gmail__gmail_create_draft(
  to = <recipient_email>,
  subject = "[Daily Report] <display_name> — <YYYY-MM-DD>",
  body = <rendered body from 4.5.4>
)
```

**On success:**
- Capture the returned draft id
- Set `project_defaults[remote_key].last_reported_at = <now, ISO 8601 UTC>`
- Save `~/.claude/report-recipients.json` atomically: write to `report-recipients.json.tmp`, then `mv` over the original
- Render the same report body in the conversation as a fenced code block so the user sees it here too
- Append `**Report:** drafted to <name> <email> (Gmail draft id <id>)` as the last line of the session-log entry just written in Step 2

**On failure (not authenticated, network error, MCP error):**
- Do NOT update `last_reported_at`
- Render the report body in the conversation under the header "Gmail draft could not be created — paste manually:"
- Record the reason for the Step 5 summary as `"Report drafting failed: <error>"`

#### 4.5.6 Output to closing summary

Emit one line item into the Step 5 summary block:
- On success: `**Report drafted:**` followed by a bullet `- To: <name> <email> — Gmail draft id <id>`
- On skip or failure: `**Report:**` followed by a bullet `- Skipped (<reason>)` or `- Failed (<reason>)`

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
