# Daily Report Feature — Design Spec

**Date:** 2026-04-16
**Skill:** sign-off
**Status:** Approved for implementation planning

## Summary

Add a daily-report feature to the sign-off skill. On every sign-off (excluding light sessions and projects without a git remote), the skill synthesizes a scrum-daily-style report from the current conversation plus recent session-log entries for this project, drafts it as an email via the Gmail MCP, and shows it in the conversation. Recipients are maintained in a local JSON file, with a per-project default recipient bound on first use.

## Goals

- Capture progress from active work and communicate it to a stakeholder with minimal friction
- Build the recipient list incrementally as the user works on more projects
- Never send email without user review — always create a Gmail draft
- Isolate report content strictly by project — never mix logs from different projects

## Non-Goals

- Sending email automatically
- Supporting multiple mailer backends in v1 (Gmail MCP only)
- Generating reports on demand outside the sign-off flow
- Back-filling `Remote:` metadata on pre-existing session-log entries

## User Flow (Happy Path)

1. User signs off (`/sign-off`, "sign off", etc.)
2. Steps 1 through 4 of the existing protocol run as today
3. **New Step 4.5** runs:
   - Detects git remote → `remote_key`
   - Loads `~/.claude/report-recipients.json`
   - If a `project_defaults[remote_key]` already exists, asks "Draft report to <name> <email>? [Enter]=confirm, [C]=change, [S]=skip"
   - If not, shows the saved recipients list with add/skip options
   - Generates the report from conversation + project-scoped session-log entries since `last_reported_at`
   - Calls Gmail MCP `gmail_create_draft` — captures the draft id
   - Renders the same report text in the conversation
   - Updates `last_reported_at` on success
4. Step 5 closing summary now includes a "Report drafted" line item

## Data Model

### `~/.claude/report-recipients.json`

```json
{
  "recipients": [
    {"name": "Mike Agruss", "email": "mike@agrusslaw.com"}
  ],
  "project_defaults": {
    "github.com:bolivarbryan/pi-legal-ai": {
      "display_name": "pi-legal-ai",
      "recipient_email": "mike@agrusslaw.com",
      "last_reported_at": "2026-04-15T18:30:00Z"
    }
  }
}
```

Rules:

- `recipients[]` is an append-oriented flat list. A recipient remains even if unbound from every project.
- `project_defaults` keys are normalized git remote strings: `host:org/repo` (strip `https://`, `git@`, trailing `.git`, replace first `/` after host with `:`).
- `recipient_email` in `project_defaults` is a foreign key into `recipients[]`. If the referenced email is missing from `recipients[]`, treat the default as absent and re-prompt.
- `display_name` is set at bind time to `basename of the git toplevel (`git rev-parse --show-toplevel`)` and is not recomputed on later runs.
- `last_reported_at` is ISO 8601 UTC. Null/missing on first bind; updated only after a successful Gmail draft creation.

### Session-log entry shape (change)

Each entry written by Step 2 gains a `**Remote:**` line directly after `**Project:**`:

```markdown
## Session: 2026-04-16 14:30

**Project:** sign-off-skill
**Remote:** github.com:bolivarbryan/sign-off-skill

**Balance:** technical=60% planning=40%

**Summary:** ...
```

When Step 4.5 drafts a report, it appends a `**Report:**` line at the end of the entry:

```markdown
**Report:** drafted to Mike Agruss <mike@agrusslaw.com> (Gmail draft id r-8f3a2c)
```

Entries without a `**Remote:**` line are excluded from report source gathering — safe default, no back-filling required.

## Step 4.5 — Specification

### 4.5.1 Preconditions

1. Resolve `remote_key`:
   - Run `git remote get-url origin` in the cwd
   - If it fails or returns empty, **skip the entire step**; record "No git remote detected" as the skip reason for Step 5's summary
   - Parse and normalize to `host:org/repo`
2. Light-session check — **skip** with reason "Light session" if ALL of the following are true about this conversation:
   - No decisions were made (Step 1 "Decisions" is empty)
   - No pending tasks were surfaced (Step 1 "Pending tasks" is empty)
   - No project-specific context was produced (Step 1 "Project context" is empty)

   This mirrors the existing "Trivial sessions" behavior in Important rules: if there's nothing substantive to save, there's nothing substantive to report.
3. Load `~/.claude/report-recipients.json`. If missing, create with the empty shape:
   ```json
   {"recipients": [], "project_defaults": {}}
   ```

### 4.5.2 Recipient selection

**Case A — no default bound for this `remote_key`:**

Present:

```
First report for this project. Who should it go to?

Saved recipients:
  1) Mike Agruss <mike@agrusslaw.com>
  2) Craig Smith <craig@sponsiv.com>

  [A] Add new recipient
  [S] Skip report this time

Choice:
```

- `[1..N]` → bind the chosen recipient as the project default; continue to 4.5.3
- `[A]` → prompt "Name:" then "Email:"; run the email sanity check (see 4.5.2.1); append to `recipients[]`; bind as default; continue
- `[S]` → exit Step 4.5 without drafting; **do not** write `project_defaults[remote_key]`; skip reason: "User opted out (no default bound)"

**Case B — default exists:**

Present:

```
Drafting report to <name> <email>.
  [Enter] Confirm
  [C]     Change recipient (pick/add someone else)
  [S]     Skip this time
```

- `[Enter]` → continue to 4.5.3
- `[C]` → run Case A picker; the selection overwrites `project_defaults[remote_key].recipient_email`
- `[S]` → exit without drafting; do not update `last_reported_at`; skip reason: "User opted out"

#### 4.5.2.1 Email sanity check

An email passes if it matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` — one or more non-whitespace non-`@` characters, an `@`, one or more non-whitespace non-`@` characters, a `.`, and one or more non-whitespace non-`@` characters. This is deliberately loose: it catches typos ("no @", "trailing space", missing domain) without trying to validate RFC 5322 edge cases. On failure, re-prompt.

### 4.5.3 Content gathering

Two sources, both scoped to the current `remote_key`:

1. **Current conversation** — Claude scans the thread for:
   - Concrete tasks completed this session ("done today")
   - Open/pending items mentioned ("next up")
   - Blockers or impediments surfaced
   - Decisions the user agreed to
   - An overall status read (on track / blocked on X / ahead)

2. **Recent session-log entries** — parse `~/.claude/session-log.md` and select entries where:
   - The `**Remote:**` line matches `remote_key` exactly, AND
   - The entry timestamp is strictly greater than `last_reported_at`
   - If `last_reported_at` is null or missing, take the most recent 5 matching entries

Entries missing a `**Remote:**` line are always excluded.

**Timestamp parsing.** Entries written by this feature follow the canonical Step 2 header format `## Session: YYYY-MM-DD HH:MM` (local time). Parse with that format; compare against `last_reported_at` by first converting both to absolute times (treat the header's HH:MM as the local time of the machine running sign-off, convert to UTC using the system timezone, then compare). If a header fails to parse (e.g., pre-feature format like `## Session: 2026-04-13` or `## Session: 2026-04-10 (morning)`), treat the entry as excluded — same safe default as a missing `**Remote:**` line. Because `**Remote:**` is itself only written going forward, any entry that includes `**Remote:**` will also include a parseable header, so the parse-failure branch exists only as a defensive fallback.

### 4.5.4 Template (rendered report)

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

Blockers                   ← section omitted entirely if empty
- <bullet>

Decisions                  ← section omitted entirely if empty
- <bullet>

—
<user-display-name>
(Auto-drafted via Claude Code sign-off)
```

Rendering rules:

- Recipient first name = first whitespace-delimited token of the `name` field
- `<user-display-name>` = `git config user.name`; fallback to "me" if unset
- Omit `Blockers` and `Decisions` *sections, headers included*, when empty — do not print "None"
- Consolidate bullets to ~8 max per section
- Strip sensitive content before drafting: passwords, tokens, API keys, secret values, specific financial figures, government ID numbers. Same rule set as the existing "Important rules" in SKILL.md
- Plain text, no Markdown formatting in the email body (Gmail drafts render plain)

### 4.5.5 Draft creation

Call Gmail MCP:

```
mcp__claude_ai_Gmail__gmail_create_draft(
  to = <recipient_email>,
  subject = "[Daily Report] <display_name> — <YYYY-MM-DD>",
  body = <rendered body from 4.5.4>,
)
```

On success:
- Capture the returned draft id
- Update `project_defaults[remote_key].last_reported_at = <now, ISO 8601 UTC>`
- Write the file atomically (write to temp path, then rename)
- Render the same report text to the conversation as a fenced block (the "sent here too" requirement)
- Record `**Report:** drafted to <name> <email> (Gmail draft id <id>)` on the session-log entry that Step 2 just wrote

On failure (auth, network, MCP error):
- Do **not** update `last_reported_at`
- Render the report text in the conversation with a header line: "Gmail draft could not be created — paste manually:"
- Record in Step 5 summary: "Report drafting failed: <reason>"

### 4.5.6 Output to closing summary (Step 5)

Add one of these line items to the summary block:

```
**Report drafted:**
- To: <name> <email> — Gmail draft id <id>
```

or, on skip/failure:

```
**Report:**
- Skipped (<reason>)
```

## Changes to Existing SKILL.md Sections

- **Step 2** — add the `**Remote:**` line to the entry template; add the optional `**Report:**` trailing line
- **Step 5** — extend the summary template with the `Report drafted` block
- **Important rules** — add four items:
  - Never auto-send — always draft for user review
  - Sensitive content (passwords, tokens, keys, specific financial figures, ID numbers) must be stripped before drafting
  - Recipient list is not memory; it lives in `~/.claude/report-recipients.json` (hand-editable)
  - `remote_key` (not display name) is the lookup — two projects with the same folder name are disambiguated
- **New reference section "How the report sources content":** short paragraph explaining the `Remote:` filter + `last_reported_at` cutoff so maintainers understand why entries without a `Remote:` line are excluded

## Failure Modes & Edge Cases

| Scenario | Behavior |
|---|---|
| Project has no git remote | Skip Step 4.5; summary notes "No git remote detected" |
| Session is light/trivial | Skip Step 4.5; summary notes "Light session — report skipped" |
| `report-recipients.json` missing | Create with empty shape on first run |
| `report-recipients.json` malformed JSON | Abort Step 4.5 with error; do not overwrite; summary notes parse error |
| Gmail MCP not authenticated | Render report in conversation with paste-manually header; no `last_reported_at` update |
| Gmail MCP returns error | Same as unauthenticated |
| `last_reported_at` is null/missing | Use the most recent 5 matching session-log entries |
| No matching session-log entries and thin conversation | Still draft if session was not classified light; the template handles short bodies |
| Recipient email referenced in `project_defaults` no longer in `recipients[]` | Treat default as absent; run Case A picker |
| User adds a recipient with an email that already exists in `recipients[]` | De-duplicate by email; update name if different (last-write-wins); bind default to the existing entry |
| Two projects with the same display name | Both work — lookup is by `remote_key`, not display name |

## Implementation Notes

- The installed skill copy at `~/.claude/skills/sign-off/SKILL.md` must be updated alongside the repo copy. This is called out in the 2026-04-14 session log entry and should be repeated in the new step's implementation notes.
- No new dependencies. Gmail MCP is already connected in this environment.
- Atomic file writes for `report-recipients.json` — write to `report-recipients.json.tmp`, then rename over the original. Avoids corruption if the process is interrupted mid-write.
- Normalize git remotes both `https://github.com/foo/bar.git` and `git@github.com:foo/bar.git` to the same `github.com:foo/bar` key.

## Future Work (Out of Scope for v1)

- **Alternative mailer backends** — user flagged during brainstorm that Gmail MCP may not be the final answer. Candidates for v2: local `mail`/`sendmail`, `mailto:` link, SMTP config file, or Outlook/other-provider MCP. Design keeps the mailer call isolated to one place (Step 4.5.5) so a backend swap is a localized change.
- On-demand reports outside sign-off (`/report` trigger)
- Multi-recipient drafts (CC/BCC)
- Report templates per project (different sections for different stakeholder types)
- Back-fill of `Remote:` on old session-log entries via a one-time migration

## Open Questions

None at design time. Any surfacing during implementation should be captured in the plan doc.
