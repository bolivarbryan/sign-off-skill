# Daily progress report (Step 4.5)

Draft a scrum-daily-style progress report to the stakeholder bound to this project.
The report is always created as a **Gmail draft**; it is never sent automatically.

State lives in `~/.claude/report-recipients.json` (hand-editable, the source of truth):

```json
{
  "recipients": [{"name": "Jane Doe", "email": "jane@example.com"}],
  "project_defaults": {
    "github.com:acme/app": {
      "display_name": "app",
      "recipient_email": "jane@example.com",
      "last_reported_at": "2026-04-15T18:30:00Z"
    }
  }
}
```

## 1. Skip conditions

Check in order. If any applies, skip the whole step and record the reason for the
Step 5 summary.

1. **No remote**: `git remote get-url origin` fails or is empty. Reason:
   `"No git remote detected"`. Otherwise normalize it to `remote_key` (same rules as
   `**Remote:**` in [session-log.md](session-log.md)).
2. **Light session**: Step 1 found no decisions, no pending tasks and no project
   context. Reason: `"Light session"`.
3. **Recipients file**: if missing, create `{"recipients": [], "project_defaults": {}}`.
   If unparseable, skip with `"recipients file corrupted — hand-edit required"`.

## 2. Recipient selection

**No default bound for `remote_key`:**

```
First report for this project. Who should it go to?

Saved recipients:
  1) <name> <email>
  2) <name> <email>

  [A] Add new recipient
  [S] Skip report this time

Choice:
```

- `1..N`: bind that recipient as the project default (set `display_name` to the
  basename of `git rev-parse --show-toplevel`), then continue.
- `A`: ask for name and email, run the email check below (re-ask on failure), append
  to `recipients` de-duplicating by email (same email: update the name), bind as
  default, continue.
- `S`: stop. Do not write `project_defaults[remote_key]`. Reason:
  `"User opted out (no default bound)"`.

**Default already bound:**

```
Drafting report to <name> <email>.
  [Enter] Confirm
  [C]     Change recipient
  [S]     Skip this time
```

- `Enter`: continue.
- `C`: run the picker above; the choice overwrites `recipient_email`.
- `S`: stop without touching `last_reported_at`. Reason: `"User opted out"`.

**Email check:** accept if it matches `^[^@\s]+@[^@\s]+\.[^@\s]+$`. This catches
typos without enforcing RFC 5322.

## 3. Content sources

Both sources are scoped to the current `remote_key`; never mix projects.

1. **This conversation**: work completed ("done today"), open items ("next up"),
   blockers, decisions, and an overall status read (on track / blocked on X / ahead).
2. **Earlier session-log entries**: this project's slot in `~/.claude/session-log.md`
   (the entry just saved) and matching entries in `~/.claude/session-log-history.md`
   (grep for the `**Remote:**` value). Include an entry only if:
   - its `**Remote:**` equals `remote_key` exactly,
   - its `## Session: YYYY-MM-DD HH:MM` header parses, and
   - that timestamp (local time, converted to UTC) is strictly after
     `last_reported_at`. If `last_reported_at` is unset, take the 5 most recent.

Entries without `**Remote:**` or with an unparseable header are always excluded.
That is deliberate: older entries cannot be safely attributed to a project.

## 4. Template

Plain text. Omit `Blockers` and `Decisions` (header included) when empty; never
print "None".

```
Subject: [Daily Report] <display_name> — <YYYY-MM-DD>

Hi <recipient-first-name>,

Status: <one-line project status>

Done today
- <bullet>

Next up
- <bullet>

Blockers
- <bullet>

Decisions
- <bullet>

—
<user-display-name>
(Auto-drafted via Claude Code sign-off)
```

- `<recipient-first-name>`: first word of the recipient's `name`.
- `<display_name>`: `project_defaults[remote_key].display_name`.
- `<user-display-name>`: `git config user.name`, or `"me"` if unset.
- At most ~8 bullets per section.
- Strip secrets: passwords, tokens, API keys, specific financial figures, ID numbers.

## 5. Create the draft

Use the connected Gmail MCP server's create-draft tool (for example
`mcp__claude_ai_Gmail__create_draft`) with `to`, `subject` and the rendered `body`.
Never use a send tool.

**On success:**

- Keep the returned draft id.
- Set `project_defaults[remote_key].last_reported_at` to now (ISO 8601, UTC) and
  save the file atomically (write `report-recipients.json.tmp`, then `mv`).
- Show the report body in the conversation as a fenced code block.
- Append `**Report:** drafted to <name> <email> (Gmail draft id <id>)` as the last
  line of this project's slot in `~/.claude/session-log.md`.

**On failure** (no Gmail connector, not authenticated, network or MCP error):

- Do not update `last_reported_at`, so the next report covers the same window.
- Show the body under "Gmail draft could not be created — paste manually:".
- Reason: `"Report drafting failed: <error>"`.

## 6. Summary line for Step 5

- Success: `**Report drafted:**` then `- To: <name> <email> — Gmail draft id <id>`
- Skip or failure: `**Report:**` then `- Skipped (<reason>)` or `- Failed (<reason>)`

Lookup is always by `remote_key`, not display name, so two projects that share a
folder name stay separate.
