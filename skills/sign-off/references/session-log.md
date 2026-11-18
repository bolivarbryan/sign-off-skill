# Session-log entry format (Step 2)

`memcard.py save` takes one entry per call. The slot key is the project directory
(`**Dir:**`); the header date decides slot order and eviction.

## Template

```markdown
## Session: YYYY-MM-DD HH:MM

**Project:** [project name]
**Dir:** [absolute project directory — the slot key; use `$PWD` of the project]

**Remote:** [host:org/repo — omit this line if no git remote is set]

**Balance:** technical=40% planning=30% ...

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

Rules enforced by the script:

- The first line must be `## Session: YYYY-MM-DD HH:MM`; entries without a dated
  header are rejected.
- `**Dir:**` is optional. If missing it is inserted after `**Project:**`. If present
  it must resolve to the same directory passed to `save`.
- Do not use other `## ` headings inside an entry: a line starting with `## ` begins
  a new entry.

Step 4.5 may later append one trailing line to the saved slot:
`**Report:** drafted to <name> <email> (Gmail draft id <id>)`.

## Deriving `**Remote:**`

Run `git remote get-url origin` in the project directory and normalize the result to
`host:org/repo`:

- Strip a leading `https://` or `git@` and a trailing `.git`.
- Replace the first `/` after the host with `:` (`github.com/foo/bar` becomes
  `github.com:foo/bar`).
- SSH URLs such as `git@github.com:foo/bar.git` already normalize to
  `github.com:foo/bar`.

If the command fails or prints nothing, omit the `**Remote:**` line. Step 4.5 uses
this value as the project's `remote_key`.

## Commands

```bash
memcard.py save <project-dir> <entry-file|->   # overwrite the slot; old save -> history
memcard.py show <project-dir>                  # print the project's slot
memcard.py list                                # print the slot table
memcard.py index                               # rebuild the slot table
memcard.py --log-dir DIR ...                   # use another directory (default ~/.claude, or $MEMCARD_DIR)
```
