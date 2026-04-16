# Daily Report Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new Step 4.5 to the sign-off skill that drafts a scrum-daily-style progress report to a selected recipient via the Gmail MCP on every non-trivial sign-off.

**Architecture:** All changes are prose edits to `SKILL.md` — Claude reads and follows this file at sign-off time, so behavior is specified in natural language. A single JSON state file (`~/.claude/report-recipients.json`) stores recipients and per-project defaults, and session-log entries gain a `**Remote:**` line for strict project isolation. The Gmail MCP tool `mcp__claude_ai_Gmail__gmail_create_draft` is the delivery mechanism; drafts are never auto-sent.

**Tech Stack:** Markdown (SKILL.md), Gmail MCP, local JSON state file, git CLI for remote/toplevel detection.

**Reference:** Spec at `docs/superpowers/specs/2026-04-16-report-feature-design.md`.

**Fence convention:** `old_string` and `new_string` content is wrapped in 4-tick fences (` ```` `) so that any nested 3-tick fences inside the content render correctly.

---

## File Map

- **Modify:** `SKILL.md` — five sections touched (Step 2 template, new Step 4.5 insertion, Step 5 template, Important rules, new reference section)
- **Sync:** `~/.claude/skills/sign-off/SKILL.md` — installed copy, mirrored from repo after edits
- **Created at runtime (not by this plan):** `~/.claude/report-recipients.json`

---

## Task 1: Add `**Remote:**` line to Step 2 session-log template

**Why first:** Step 4.5's report-source filter relies on `**Remote:**` being present on future entries. Land this first so the metadata starts accumulating before the report step is live.

**Files:**
- Modify: `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md` (the Step 2 entry template block)

- [ ] **Step 1: Apply the template edit**

Use Edit with:

`old_string:`
````
## Session: YYYY-MM-DD HH:MM

**Project:** [project name or directory]

**Summary:**
````

`new_string:`
````
## Session: YYYY-MM-DD HH:MM

**Project:** [project name or directory]

**Remote:** [host:org/repo — omit this line if no git remote is set]

**Summary:**
````

- [ ] **Step 2: Append the "Deriving Remote" instruction block**

This edit spans the end of the Step 2 template (closing triple-tick fence) through to the `### Step 3` heading, replacing that range with the same closing fence plus a new paragraph plus the heading.

Use Edit with:

`old_string:`
````
**Notes:**
- [Anything else worth remembering]
```

### Step 3: Auto-setup session recovery (first run only)
````

`new_string:`
````
**Notes:**
- [Anything else worth remembering]
```

**Deriving `**Remote:**`:** Run `git remote get-url origin` from the project directory. Normalize the result to `host:org/repo`:
- Strip leading `https://` or `git@` and trailing `.git`
- Replace the first `/` after the host with `:` (so `github.com/foo/bar` becomes `github.com:foo/bar`)
- For SSH URLs like `git@github.com:foo/bar.git`, the normalization already leaves `github.com:foo/bar`

If `git remote get-url origin` fails or returns empty, omit the `**Remote:**` line entirely. A later `**Report:**` trailing line may be appended by Step 4.5 — see that step for its format.

### Step 3: Auto-setup session recovery (first run only)
````

- [ ] **Step 3: Visual verification**

Run:
```bash
sed -n '82,130p' /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md
```
Expected: the Step 2 section contains the `**Remote:**` placeholder in the template AND the "Deriving `**Remote:**`" paragraph after the template block.

- [ ] **Step 4: Commit**

```bash
cd /Users/bolivarbryan/Developer/claude-skill/sign-off-skill
git add SKILL.md
git commit -m "$(cat <<'EOF'
Add Remote line to session-log template

Step 2 now writes a **Remote:** host:org/repo line per entry.
Prepares session-log entries for project-scoped filtering by
the upcoming Step 4.5 report feature.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Insert Step 4.5 — Generate & Draft Report

**Why second:** This is the bulk of the feature. Lands as one commit because the six subsections form a single contract (preconditions → selection → gather → template → draft → summary output) that makes no sense partially applied.

**Files:**
- Modify: `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md` (insert a new section between Step 4 and Step 5)

- [ ] **Step 1: Apply the insertion**

Use Edit with:

`old_string:`
````
If no project-specific context was found, skip this step.

### Step 5: Present closing summary
````

`new_string:`
````
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
````

- [ ] **Step 2: Visual verification**

Run:
```bash
grep -n "### Step 4.5" /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md
```
Expected: exactly one match for `### Step 4.5: Generate & draft progress report`.

Run:
```bash
awk '/### Step 4.5/,/### Step 5/' /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md | wc -l
```
Expected: greater than 100 lines (the full Step 4.5 section plus the Step 5 heading line).

- [ ] **Step 3: Commit**

```bash
cd /Users/bolivarbryan/Developer/claude-skill/sign-off-skill
git add SKILL.md
git commit -m "$(cat <<'EOF'
Add Step 4.5 Generate & Draft Report to sign-off protocol

Introduces a new step between CLAUDE.md update and closing summary:
resolves project remote key, selects/binds a recipient, gathers
session content filtered by **Remote:** line, renders a scrum-daily
template, and creates a Gmail MCP draft without sending.

Draft creation is non-destructive — Gmail MCP failures fall back to
rendering the report in-conversation for manual paste.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Update Step 5 closing summary template to include report line

**Files:**
- Modify: `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md` (Step 5 template block)

- [ ] **Step 1: Apply the template edit**

Use Edit with:

`old_string:`
````
## Session Summary

**Saved to session log:**
- [short list of what was logged]

**Updated CLAUDE.md:**
- [what was added, or "No project-specific updates"]

**Pending items:**
- [tasks or to-dos, if any]

**Until next time!**
[Brief, warm goodbye — personalized if there's context]
````

`new_string:`
````
## Session Summary

**Saved to session log:**
- [short list of what was logged]

**Updated CLAUDE.md:**
- [what was added, or "No project-specific updates"]

**Report drafted:**
- [To: <name> <email> — Gmail draft id <id>  OR  Skipped (<reason>)  OR  Failed (<reason>)]

**Pending items:**
- [tasks or to-dos, if any]

**Until next time!**
[Brief, warm goodbye — personalized if there's context]
````

- [ ] **Step 2: Visual verification**

Run:
```bash
grep -n "Report drafted" /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md
```
Expected: at least one match in Step 5's template.

- [ ] **Step 3: Commit**

```bash
cd /Users/bolivarbryan/Developer/claude-skill/sign-off-skill
git add SKILL.md
git commit -m "$(cat <<'EOF'
Add Report drafted line to closing summary template

Step 5 now surfaces the outcome of Step 4.5 (drafted, skipped, or
failed) as a line item in the Session Summary block so the user
can see at a glance whether a Gmail draft was created.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add Important rules entries and the "How the report sources content" reference section

**Files:**
- Modify: `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md` (Important rules section near the end of the file)

- [ ] **Step 1: Apply the edit**

Use Edit with:

`old_string:`
````
## Important rules

- **Never save sensitive information**: passwords, tokens, API keys, specific financial data, ID numbers
- **No duplicates**: Check session-log.md before appending to avoid repeating the same info
- **Ask when in doubt**: If unsure whether something is worth saving, ask the user
- **Match language**: Respect the language the user used during the conversation
- **Trivial sessions**: If the conversation was light (just a greeting, a simple question), don't invent things to save. Say something like "Light session today — nothing new to save. See you next time!"
- **Brevity**: The closing summary should be short. No more than 10 lines.
- **Session log size**: If `~/.claude/session-log.md` exceeds 200 lines, archive older entries to `~/.claude/session-log-archive.md` keeping only the last 50 entries in the main file.
````

`new_string:`
````
## Important rules

- **Never save sensitive information**: passwords, tokens, API keys, specific financial data, ID numbers
- **No duplicates**: Check session-log.md before appending to avoid repeating the same info
- **Ask when in doubt**: If unsure whether something is worth saving, ask the user
- **Match language**: Respect the language the user used during the conversation
- **Trivial sessions**: If the conversation was light (just a greeting, a simple question), don't invent things to save. Say something like "Light session today — nothing new to save. See you next time!"
- **Brevity**: The closing summary should be short. No more than 10 lines.
- **Session log size**: If `~/.claude/session-log.md` exceeds 200 lines, archive older entries to `~/.claude/session-log-archive.md` keeping only the last 50 entries in the main file.
- **Never auto-send reports**: Step 4.5 must create a Gmail draft only. Let the user review and hit send manually.
- **Strip sensitive content from reports**: apply the same rules as session-log saves — no passwords, tokens, keys, specific financial figures, or ID numbers in the draft body.
- **Recipient list is not memory**: `~/.claude/report-recipients.json` is the source of truth; it is hand-editable by the user.
- **Report lookup is by `remote_key`, not display name**: two projects sharing a folder name are correctly disambiguated by their git remote.

## How the report sources content

Step 4.5 synthesizes each report from two sources:

1. The current conversation — decisions, pending items, blockers, completed work, and an overall status read.
2. Session-log entries whose `**Remote:**` line matches the current project's `remote_key` exactly AND whose header timestamp is strictly greater than `last_reported_at` for this project.

Entries without a `**Remote:**` line, or with a header that does not match the canonical `## Session: YYYY-MM-DD HH:MM` format, are excluded. This is deliberate — the `**Remote:**` line was added in a specific version of this skill, and older entries have no safe way to be attributed to a project. Exclusion is the safe default.

`last_reported_at` is only updated after a successful Gmail draft creation. If drafting fails or the user skips, the cutoff stays put and the next report covers the same window.
````

- [ ] **Step 2: Visual verification**

Run:
```bash
grep -n "Never auto-send reports" /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md
grep -n "How the report sources content" /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md
```
Expected: each grep returns exactly one match.

- [ ] **Step 3: Commit**

```bash
cd /Users/bolivarbryan/Developer/claude-skill/sign-off-skill
git add SKILL.md
git commit -m "$(cat <<'EOF'
Add report-specific rules and sources reference section

Four new Important rules entries (never auto-send, strip sensitive
content, recipient list location, remote_key as lookup) and a new
"How the report sources content" reference section explaining the
Remote: filter and last_reported_at cutoff.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Sync installed skill copy

**Why:** The installed copy at `~/.claude/skills/sign-off/SKILL.md` is what Claude Code actually loads at session start. The repo copy is the source of truth but has no runtime effect until mirrored.

**Files:**
- Sync target: `~/.claude/skills/sign-off/SKILL.md`
- Source: `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md`

- [ ] **Step 1: Verify installed-skill directory exists**

Run:
```bash
ls -la ~/.claude/skills/sign-off/
```
Expected: the directory exists and contains a `SKILL.md` (the pre-feature version).

If it does not exist, stop and investigate — the installed skill may be under a different path.

- [ ] **Step 2: Copy the updated SKILL.md into the installed location**

Run:
```bash
cp /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md ~/.claude/skills/sign-off/SKILL.md
```

- [ ] **Step 3: Verify the sync**

Run:
```bash
diff /Users/bolivarbryan/Developer/claude-skill/sign-off-skill/SKILL.md ~/.claude/skills/sign-off/SKILL.md
```
Expected: no output (files identical). A non-zero exit code means the sync failed.

- [ ] **Step 4: No commit needed**

The installed copy lives outside the git repo; this task has no commit. Symlink-based sync is a possible follow-up improvement but out of scope here.

---

## Task 6: End-to-end dry-run test

**Why:** This is prose behavior; the only meaningful test is running the skill against a real session and checking the artifacts it produces.

**Exercises:** `SKILL.md`, `~/.claude/session-log.md`, `~/.claude/report-recipients.json`, Gmail Drafts.

- [ ] **Step 1: Baseline snapshot**

Run:
```bash
ls -la ~/.claude/report-recipients.json 2>&1 || echo "file does not exist yet (expected first time)"
tail -20 ~/.claude/session-log.md
```
Record: whether `report-recipients.json` exists, and the timestamp of the last session-log entry.

- [ ] **Step 2: Trigger a first-time sign-off in a fresh Claude Code session**

In a new Claude Code session running in `/Users/bolivarbryan/Developer/claude-skill/sign-off-skill`, do a small amount of real work (e.g., open SKILL.md and discuss one paragraph) so the session is non-trivial, then type `/sign-off`.

Expected: the skill proceeds through Steps 1–4, then Step 4.5 prompts for recipient selection using the Case A flow (first-time).

- [ ] **Step 3: Choose [A] Add new recipient**

Provide a test name and a real email address you can access. The skill should append the recipient to `recipients[]` and bind the default.

- [ ] **Step 4: Verify Gmail draft**

Open Gmail Drafts. Expected: a draft with subject `[Daily Report] sign-off-skill — 2026-04-16`, addressed to the chosen email, and a body rendered from the 4.5.4 template with Status / Done today / Next up sections populated.

- [ ] **Step 5: Verify `~/.claude/report-recipients.json`**

Run:
```bash
cat ~/.claude/report-recipients.json
```

Expected shape (values will differ):
```json
{
  "recipients": [{"name": "<name>", "email": "<email>"}],
  "project_defaults": {
    "github.com:bolivarbryan/sign-off-skill": {
      "display_name": "sign-off-skill",
      "recipient_email": "<email>",
      "last_reported_at": "2026-04-16T..."
    }
  }
}
```

- [ ] **Step 6: Verify session-log entry**

Run:
```bash
tail -40 ~/.claude/session-log.md
```

Expected: the new entry contains a `**Remote:** github.com:bolivarbryan/sign-off-skill` line AND a trailing `**Report:** drafted to <name> <email> (Gmail draft id <id>)` line.

- [ ] **Step 7: Second-run check (Case B)**

Start another fresh Claude Code session in the same directory. Do a tiny bit of work, then `/sign-off` again. Expected: the skill shows Case B: "Drafting report to <name> <email>. [Enter] Confirm [C] Change [S] Skip".

Press `[Enter]`. Verify a second Gmail draft is created. Verify `last_reported_at` in `report-recipients.json` has advanced.

- [ ] **Step 8: Light-session skip check**

Start one more fresh session. Immediately type `/sign-off` with no real work. Expected: the skill skips Step 4.5 with reason "Light session" and the Step 5 summary shows `**Report:** - Skipped (Light session)`.

- [ ] **Step 9: Record test outcome**

If any step deviated from expected, capture the actual output and either fix the SKILL.md prose or open a follow-up task. If everything passed, the feature is ready to use and the plan is complete.

---

## Notes

- **No automated test files** — SKILL.md is prose consumed by Claude at runtime. Task 6 is the manual end-to-end check.
- **Gmail MCP auth** — Task 6 assumes the Gmail MCP is already authenticated for this user (it is, per current environment). If a future engineer runs this plan on a fresh machine, they may need to authenticate first; the skill will record a failure with reason `"not authenticated"` until they do.
- **Worktree** — brainstorming did not create a worktree; changes land on `main` directly. This is acceptable for a personal skill repo with a small scope. For larger future features, consider a worktree.
