# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-11-18

### Added

- Claude Code plugin packaging: `.claude-plugin/plugin.json` and a single-repo
  `marketplace.json`, installable with
  `/plugin marketplace add bolivarbryan/sign-off-skill`.
- Spanish trigger phrases ("cierra la sesión", "guarda y salimos", ...) via the
  `when_to_use` frontmatter field.
- `memcard.py` CLI built on argparse: `--help`, `--version`, `--log-dir`, the
  `MEMCARD_DIR` environment variable, and `-` to read an entry from stdin.
- pytest suite for slot create, update, eviction and rotation to history, path
  normalization and the CLI.
- GitHub Actions CI: ruff lint and format checks, pytest on Python 3.10 to 3.13
  (Linux and macOS), manifest consistency check.
- `CHANGELOG.md`, `pyproject.toml`, design-docs index.

### Changed

- **Breaking:** repository layout follows the plugin spec. The skill now lives in
  `skills/sign-off/` and the script in `skills/sign-off/scripts/memcard.py`. Manual
  installs should copy `skills/sign-off` to `~/.claude/skills/sign-off`.
- **Breaking:** as a plugin the skill is invoked as `/sign-off:sign-off`; a manual
  install keeps `/sign-off`.
- `SKILL.md` uses progressive disclosure: session balance, entry format and the daily
  report protocol moved to `references/`. The protocol itself is unchanged.
- The script is referenced through `${CLAUDE_SKILL_DIR}` instead of a hardcoded path,
  and `allowed-tools` pre-approves only that script.
- The memory card header and slot table are written in English.
- Report drafting refers to the current Gmail MCP `create_draft` tool.
- `memcard.py` is typed (`MemoryCard` class, `Entry` dataclass); errors exit 1 with a
  `memcard: error:` message.
- Planning docs moved from `docs/superpowers/` to `docs/design/`, with personal data
  replaced by placeholders.

### Fixed

- Slots saved with the same timestamp could swap order after the card was re-read,
  which also made eviction drop the newer save first.

## [1.x]

Earlier, unversioned iterations: the initial sign-off ritual, session balance,
`**Remote:**` metadata, the daily report step, the last-session/history split, and
the memory-card session log.
