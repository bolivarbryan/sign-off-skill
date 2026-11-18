"""Tests for skills/sign-off/scripts/memcard.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import memcard
from memcard import Entry, MemcardError, MemoryCard, split

SCRIPT = Path(memcard.__file__)


def entry(date: str, project: str = "Demo", dir_: str | None = None, note: str = "") -> str:
    lines = [f"## Session: {date}", "", f"**Project:** {project}"]
    if dir_ is not None:
        lines.append(f"**Dir:** {dir_}")
    lines += ["", "**Summary:**", f"- {note or 'did things'}"]
    return "\n".join(lines) + "\n"


@pytest.fixture
def card(tmp_path: Path) -> MemoryCard:
    return MemoryCard(tmp_path / "logs")


@pytest.fixture
def projects(tmp_path: Path) -> list[Path]:
    dirs = [tmp_path / f"proj{i}" for i in range(20)]
    for d in dirs:
        d.mkdir()
    return dirs


# -- parsing -----------------------------------------------------------------


def test_entry_parses_header_project_and_dir(tmp_path: Path) -> None:
    e = Entry(entry("2026-11-18 09:30", "Alpha", str(tmp_path)))
    assert e.date == "2026-11-18 09:30"
    assert e.title == "2026-11-18 09:30"
    assert e.project == "Alpha"
    assert e.dir == str(tmp_path.resolve())


def test_entry_date_without_time_defaults_to_midnight() -> None:
    assert Entry("## Session: 2026-01-02\n").date == "2026-01-02 00:00"


def test_split_strips_separators_between_entries() -> None:
    text = "# Card\n\n---\n\n" + entry("2026-01-01 10:00") + "\n---\n\n" + entry("2026-01-02 10:00")
    preamble, entries = split(text)
    assert preamble.startswith("# Card")
    assert len(entries) == 2
    assert all(not e.text.rstrip().endswith("---") for e in entries)


# -- create ------------------------------------------------------------------


def test_save_creates_slot_and_card(card: MemoryCard, projects: list[Path]) -> None:
    msg = card.save(str(projects[0]), entry("2026-11-18 10:00", "Alpha"))

    assert "new slot" in msg and "1/15" in msg
    assert card.card.exists()
    assert not card.history.exists()
    [slot] = card.load()
    assert slot.project == "Alpha"
    assert slot.dir == str(projects[0].resolve())
    text = card.card.read_text(encoding="utf-8")
    assert "| 1 | Alpha |" in text
    assert "**Dir:**" in text  # added automatically after **Project:**


def test_save_inserts_dir_after_header_when_no_project_line(card: MemoryCard, projects: list[Path]) -> None:
    card.save(str(projects[0]), "## Session: 2026-11-18 10:00\n\n- note\n")
    [slot] = card.load()
    assert slot.text.split("\n")[2].startswith("**Dir:**")


def test_save_rejects_missing_header(card: MemoryCard, projects: list[Path]) -> None:
    with pytest.raises(MemcardError, match="header"):
        card.save(str(projects[0]), "**Project:** x\n")


def test_save_rejects_header_without_date(card: MemoryCard, projects: list[Path]) -> None:
    with pytest.raises(MemcardError, match="date"):
        card.save(str(projects[0]), "## Session: today\n")


def test_save_rejects_mismatched_dir(card: MemoryCard, projects: list[Path]) -> None:
    with pytest.raises(MemcardError, match="does not match"):
        card.save(str(projects[0]), entry("2026-11-18 10:00", dir_=str(projects[1])))
    assert not card.card.exists()


# -- update ------------------------------------------------------------------


def test_save_overwrites_slot_and_moves_previous_to_history(card: MemoryCard, projects: list[Path]) -> None:
    p = str(projects[0])
    card.save(p, entry("2026-11-17 10:00", "Alpha", note="first"))
    msg = card.save(p, entry("2026-11-18 10:00", "Alpha", note="second"))

    assert "overwrote slot (2026-11-17 10:00 -> history)" in msg
    [slot] = card.load()
    assert "second" in slot.text and "first" not in slot.text
    history = card.history.read_text(encoding="utf-8")
    assert history.startswith("# Session Log — History")
    assert "first" in history and "second" not in history


def test_update_leaves_other_projects_untouched(card: MemoryCard, projects: list[Path]) -> None:
    card.save(str(projects[0]), entry("2026-11-16 10:00", "Alpha"))
    card.save(str(projects[1]), entry("2026-11-17 10:00", "Beta"))
    card.save(str(projects[0]), entry("2026-11-18 10:00", "Alpha", note="again"))

    slots = card.slots()
    assert [s.project for s in slots] == ["Alpha", "Beta"]  # newest first
    assert "Beta" not in card.history.read_text(encoding="utf-8")


def test_same_timestamp_newest_save_wins(card: MemoryCard, projects: list[Path]) -> None:
    card.save(str(projects[0]), entry("2026-11-18 10:00", "Alpha"))
    card.save(str(projects[1]), entry("2026-11-18 10:00", "Beta"))
    assert card.slots()[0].project == "Beta"


def test_show_matches_tilde_and_symlinked_paths(
    card: MemoryCard, projects: list[Path], tmp_path: Path
) -> None:
    card.save(str(projects[0]), entry("2026-11-18 10:00", "Alpha"))
    link = tmp_path / "link"
    link.symlink_to(projects[0])
    assert [e.project for e in card.find(str(link))] == ["Alpha"]
    assert card.find(str(projects[1])) == []


# -- rotate to history ---------------------------------------------------------


def test_full_card_evicts_oldest_slot_to_history(tmp_path: Path, projects: list[Path]) -> None:
    card = MemoryCard(tmp_path / "logs", max_slots=3)
    for i in range(3):
        card.save(str(projects[i]), entry(f"2026-11-1{i} 10:00", f"P{i}"))

    msg = card.save(str(projects[3]), entry("2026-11-18 10:00", "P3"))

    assert "1 oldest slot(s) evicted to history" in msg and "3/3" in msg
    assert [s.project for s in card.slots()] == ["P3", "P2", "P1"]
    history = card.history.read_text(encoding="utf-8")
    assert "**Project:** P0" in history


def test_default_card_holds_fifteen_slots(card: MemoryCard, projects: list[Path]) -> None:
    for i in range(16):
        card.save(str(projects[i]), entry(f"2026-10-{i + 1:02d} 10:00", f"P{i}"))
    assert len(card.load()) == memcard.MAX_SLOTS == 15
    assert "**Project:** P0\n" in card.history.read_text(encoding="utf-8")


def test_history_is_append_only(card: MemoryCard, projects: list[Path]) -> None:
    p = str(projects[0])
    for day in range(1, 5):
        card.save(p, entry(f"2026-11-0{day} 10:00", "Alpha", note=f"day{day}"))
    history = card.history.read_text(encoding="utf-8")
    assert [n for n in ("day1", "day2", "day3", "day4") if n in history] == ["day1", "day2", "day3"]
    assert history.index("day1") < history.index("day2") < history.index("day3")


def test_reindex_rebuilds_table(card: MemoryCard, projects: list[Path]) -> None:
    card.save(str(projects[0]), entry("2026-11-18 10:00", "Alpha"))
    text = card.card.read_text(encoding="utf-8").replace("| 1 | Alpha |", "| 1 | stale |")
    card.card.write_text(text, encoding="utf-8")
    assert card.reindex() == "index rebuilt: 1/15 slots"
    assert "| 1 | Alpha |" in card.card.read_text(encoding="utf-8")


# -- CLI ---------------------------------------------------------------------


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    for cmd in ("save", "index", "list", "show"):
        assert cmd in result.stdout


def test_cli_round_trip(tmp_path: Path, projects: list[Path]) -> None:
    logs = str(tmp_path / "logs")
    entry_file = tmp_path / "entry.md"
    entry_file.write_text(entry("2026-11-18 10:00", "Alpha"), encoding="utf-8")

    saved = run_cli("--log-dir", logs, "save", str(projects[0]), str(entry_file))
    assert saved.returncode == 0, saved.stderr
    assert "new slot" in saved.stdout

    listed = run_cli("--log-dir", logs, "list")
    assert "| 1 | Alpha |" in listed.stdout

    shown = run_cli("--log-dir", logs, "show", str(projects[0]))
    assert shown.stdout.startswith("## Session: 2026-11-18 10:00")


def test_cli_save_from_stdin(tmp_path: Path, projects: list[Path]) -> None:
    logs = str(tmp_path / "logs")
    result = run_cli("--log-dir", logs, "save", str(projects[0]), "-", stdin=entry("2026-11-18 10:00"))
    assert result.returncode == 0, result.stderr


def test_cli_reports_errors_with_nonzero_exit(tmp_path: Path, projects: list[Path]) -> None:
    result = run_cli("--log-dir", str(tmp_path), "save", str(projects[0]), str(tmp_path / "missing.md"))
    assert result.returncode == 1
    assert "memcard: error:" in result.stderr


def test_log_dir_from_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(memcard.ENV_LOG_DIR, str(tmp_path / "env-logs"))
    assert MemoryCard().card == tmp_path / "env-logs" / memcard.CARD_NAME
