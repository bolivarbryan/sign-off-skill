#!/usr/bin/env python3
"""Memory-card session log for the sign-off skill.

Works like a console memory card: one slot per project, each holding that
project's latest session. Saving over a slot moves the previous save to a
history file, so nothing is ever lost and the card stays small enough to be
read at the start of every conversation.

Files (in the log directory, ``~/.claude`` by default):

  session-log.md          the CARD: slot table + one entry per project
  session-log-history.md  OLD SAVES: every entry overwritten or evicted

Entry format (what the sign-off skill writes to <entry-file>)::

  ## Session: YYYY-MM-DD HH:MM
  **Project:** ...
  **Dir:** /abs/path/of/project   <- optional; added from <project-dir> if missing
  ...

Standard library only. Python 3.10+ is the supported target.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__version__ = "2.0.0"

HOME = os.path.expanduser("~")
DEFAULT_LOG_DIR = os.path.join(HOME, ".claude")
CARD_NAME = "session-log.md"
HISTORY_NAME = "session-log-history.md"
MAX_SLOTS = 15
ENV_LOG_DIR = "MEMCARD_DIR"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")
NEWEST = 10**9  # position given to a fresh save so it wins date ties


class MemcardError(Exception):
    """A user-facing error; the CLI prints it and exits non-zero."""


def norm(path: str) -> str:
    """Canonical form of a project directory (the slot key)."""
    return os.path.realpath(os.path.expanduser(path.strip().strip("`")))


def tilde(path: str) -> str:
    """Shorten a path under $HOME to ``~/...`` for display."""
    return "~" + path[len(HOME) :] if path.startswith(HOME) else path


@dataclass
class Entry:
    """One session entry: a ``## `` header line plus its body."""

    text: str
    pos: int = 0
    header: str = field(init=False)
    title: str = field(init=False)
    date: str = field(init=False)
    project: str = field(init=False)
    dir: str | None = field(init=False)

    def __post_init__(self) -> None:
        self.text = self.text.strip("\n")
        lines = self.text.split("\n")
        self.header = lines[0] if lines else ""
        self.title = re.sub(r"^##\s*(Session:\s*)?", "", self.header).strip()
        m = DATE_RE.search(self.header)
        self.date = f"{m.group(1)} {m.group(2) or '00:00'}" if m else ""
        self.project = ""
        self.dir = None
        for line in lines:
            if line.startswith("**Project:**") and not self.project:
                self.project = line[len("**Project:**") :].strip()
            elif line.startswith("**Dir:**") and self.dir is None:
                self.dir = norm(line[len("**Dir:**") :])

    def key(self) -> tuple[str, int]:
        """Sort key: date, then file position (later wins ties)."""
        return (self.date, self.pos)

    def with_dir(self, d: str) -> Entry:
        """Copy of this entry with a ``**Dir:**`` line (after ``**Project:**`` or the header)."""
        lines = self.text.split("\n")
        dir_line = f"**Dir:** {tilde(d)}"
        for i, line in enumerate(lines):
            if line.startswith("**Project:**"):
                lines.insert(i + 1, dir_line)
                break
        else:
            lines[1:1] = ["", dir_line]
        return Entry("\n".join(lines), self.pos)


def split(text: str) -> tuple[str, list[Entry]]:
    """Split a log file into ``(preamble, entries)``. Entries start at ``## `` lines."""
    lines = text.split("\n")
    idx = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not idx:
        return text, []
    preamble = "\n".join(lines[: idx[0]])
    entries = []
    bounds = [*idx, len(lines)]
    for n in range(len(idx)):
        chunk = lines[bounds[n] : bounds[n + 1]]
        while chunk and chunk[-1].strip() in ("", "---"):
            chunk.pop()
        entries.append(Entry("\n".join(chunk), n))
    return preamble, entries


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def slot_table(entries: Iterable[Entry]) -> str:
    """Markdown table summarising the slots, in the given order."""
    rows = ["| # | Project | Dir | Last session |", "|---|---|---|---|"]
    for i, e in enumerate(entries, 1):
        proj = re.sub(r"\s+", " ", e.project or e.title).replace("|", "/")
        if len(proj) > 48:
            proj = proj[:47] + "…"
        rows.append(f"| {i} | {proj} | {tilde(e.dir) if e.dir else '?'} | {e.date} |")
    return "\n".join(rows)


class MemoryCard:
    """The card and its history file, rooted at ``log_dir``."""

    def __init__(
        self,
        log_dir: str | os.PathLike[str] | None = None,
        max_slots: int = MAX_SLOTS,
    ) -> None:
        root = log_dir or os.environ.get(ENV_LOG_DIR) or DEFAULT_LOG_DIR
        self.dir = Path(root).expanduser()
        self.card = self.dir / CARD_NAME
        self.history = self.dir / HISTORY_NAME
        self.max_slots = max_slots

    # -- reading -------------------------------------------------------
    def load(self) -> list[Entry]:
        """Entries on the card, in file order.

        The card is stored newest-first, so an entry nearer the top gets the higher
        ``pos``; that keeps same-timestamp saves in the order they were made.
        """
        entries = split(_read(self.card))[1]
        for n, e in enumerate(entries):
            e.pos = len(entries) - n
        return entries

    def slots(self) -> list[Entry]:
        """Current slots, newest save first."""
        return sorted(self.load(), key=Entry.key, reverse=True)

    def find(self, project_dir: str) -> list[Entry]:
        """Slots whose ``**Dir:**`` matches ``project_dir`` (normally zero or one)."""
        d = norm(project_dir)
        return [e for e in self.load() if e.dir == d]

    # -- writing -------------------------------------------------------
    def write_card(self, entries: Iterable[Entry]) -> list[Entry]:
        """Rewrite the card (slot table + entries, newest first)."""
        ordered = sorted(entries, key=Entry.key, reverse=True)
        header = (
            "# Session Log — Memory Card\n\n"
            f"One slot per project holding its latest session (max {self.max_slots}). "
            "On sign-off the new save overwrites the project's slot and the previous one "
            f"moves to `{tilde(str(self.history))}` (grep it by project or date; "
            "do not read that file whole).\n\n" + slot_table(ordered) + "\n"
        )
        body = "\n\n---\n\n".join(e.text for e in ordered)
        self.dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.card, header + ("\n---\n\n" + body + "\n" if ordered else ""))
        return ordered

    def append_history(self, entries: Sequence[Entry]) -> None:
        """Append entries to the history file, creating it if needed."""
        if not entries:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.history.exists():
            _atomic_write(self.history, "# Session Log — History\n")
        with self.history.open("a", encoding="utf-8") as f:
            for e in entries:
                f.write("\n---\n\n" + e.text + "\n")

    def save(self, project_dir: str, entry_text: str) -> str:
        """Overwrite the project's slot with ``entry_text``. Returns a status line."""
        d = norm(project_dir)
        new = Entry(entry_text)
        if not new.header.startswith("## "):
            raise MemcardError('entry must start with a "## Session: YYYY-MM-DD HH:MM" header')
        if not new.date:
            raise MemcardError('entry header needs a date: "## Session: YYYY-MM-DD HH:MM"')
        if new.dir is None:
            new = new.with_dir(d)
        elif new.dir != d:
            raise MemcardError(f"entry **Dir:** ({new.dir}) does not match project dir ({d})")

        entries = self.load()
        replaced = [e for e in entries if e.dir == d]
        kept = [e for e in entries if e.dir != d]
        new.pos = NEWEST
        kept.append(new)
        kept.sort(key=Entry.key, reverse=True)
        overflow, kept = kept[self.max_slots :], kept[: self.max_slots]

        # History first: a crash in between duplicates a save at worst, never loses one.
        self.append_history(replaced + overflow)
        self.write_card(kept)

        what = f"overwrote slot ({replaced[0].date} -> history)" if replaced else "new slot"
        extra = f", {len(overflow)} oldest slot(s) evicted to history" if overflow else ""
        return f"saved {tilde(d)}: {what}{extra}. {len(kept)}/{self.max_slots} slots used."

    def reindex(self) -> str:
        """Rebuild the slot table from the entries on the card."""
        entries = self.write_card(self.load())
        return f"index rebuilt: {len(entries)}/{self.max_slots} slots"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memcard.py",
        description="Memory-card session log: one slot per project; older saves go to history.",
        epilog=f"The log directory defaults to ${ENV_LOG_DIR}, then ~/.claude.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--log-dir",
        metavar="DIR",
        help=f"directory holding {CARD_NAME} and {HISTORY_NAME}",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_save = sub.add_parser(
        "save",
        help="overwrite a project's slot with a new entry",
        description=(
            "Overwrite the project's slot with the entry in ENTRY_FILE. The previous save for "
            "that project, and any slot evicted because the card is full, is appended to the "
            "history; then the slot table is rebuilt."
        ),
    )
    p_save.add_argument("project_dir", help="project directory (the slot key)")
    p_save.add_argument("entry_file", help="markdown file with the new entry ('-' reads stdin)")

    sub.add_parser("index", help="rebuild the slot table at the top of the card")
    sub.add_parser("list", help="print the slot table")

    p_show = sub.add_parser("show", help="print the slot for a project (nothing if none)")
    p_show.add_argument("project_dir", help="project directory (the slot key)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    card = MemoryCard(args.log_dir)
    try:
        if args.command == "save":
            text = sys.stdin.read() if args.entry_file == "-" else _read(Path(args.entry_file))
            print(card.save(args.project_dir, text))
        elif args.command == "index":
            print(card.reindex())
        elif args.command == "list":
            print(slot_table(card.slots()))
        elif args.command == "show":
            for entry in card.find(args.project_dir):
                print(entry.text)
    except MemcardError as exc:
        print(f"memcard: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
