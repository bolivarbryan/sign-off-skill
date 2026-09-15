#!/usr/bin/env python3
"""Memory-card style session log (PlayStation memory card logic).

~/.claude/session-log.md          the CARD: one slot per project, holding that project's latest session
~/.claude/session-log-history.md  OLD SAVES: every session that was overwritten by a newer save

Commands
  memcard.py save <project-dir> <entry-file>   overwrite the project's slot with the session entry in
                                               <entry-file>; the previous save for that project (if any)
                                               is appended to the history. Rebuilds the slot table.
  memcard.py index                             rebuild the slot table at the top of the card
  memcard.py list                              print the slot table
  memcard.py show <project-dir>                print the slot for that project (nothing if none)

Entry format (what the sign-off skill writes to <entry-file>):
  ## Session: YYYY-MM-DD HH:MM
  **Project:** ...
  **Dir:** /abs/path/of/project      <- optional; added automatically from <project-dir> if missing
  ...
"""
import os
import re
import sys

HOME = os.path.expanduser('~')
CARD = os.path.join(HOME, '.claude', 'session-log.md')
HIST = os.path.join(HOME, '.claude', 'session-log-history.md')
MAX_SLOTS = 15

DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?')


def norm(path):
    return os.path.realpath(os.path.expanduser(path.strip().strip('`')))


def tilde(path):
    return '~' + path[len(HOME):] if path.startswith(HOME) else path


class Entry:
    def __init__(self, text, pos=0):
        self.text = text.strip('\n')
        self.pos = pos
        lines = self.text.split('\n')
        self.header = lines[0] if lines else ''
        self.title = re.sub(r'^##\s*(Session:\s*)?', '', self.header).strip()
        m = DATE_RE.search(self.header)
        self.date = f'{m.group(1)} {m.group(2) or "00:00"}' if m else ''
        self.project = ''
        self.dir = None
        for line in lines:
            if line.startswith('**Project:**') and not self.project:
                self.project = line[len('**Project:**'):].strip()
            elif line.startswith('**Dir:**') and self.dir is None:
                self.dir = norm(line[len('**Dir:**'):])

    def key(self):
        return (self.date, self.pos)

    def with_dir(self, d):
        """Return a copy of this entry with a **Dir:** line inserted (after **Project:** or the header)."""
        lines = self.text.split('\n')
        dir_line = f'**Dir:** {tilde(d)}'
        for i, line in enumerate(lines):
            if line.startswith('**Project:**'):
                lines.insert(i + 1, dir_line)
                break
        else:
            lines[1:1] = ['', dir_line]
        return Entry('\n'.join(lines), self.pos)


def split(text):
    """Split a log file into (header_text, [Entry]). Entries start at '## ' lines."""
    lines = text.split('\n')
    idx = [i for i, l in enumerate(lines) if l.startswith('## ')]
    if not idx:
        return text, []
    header = '\n'.join(lines[:idx[0]])
    entries = []
    for n, (a, b) in enumerate(zip(idx, idx[1:] + [len(lines)])):
        chunk = lines[a:b]
        while chunk and chunk[-1].strip() in ('', '---'):
            chunk.pop()
        entries.append(Entry('\n'.join(chunk), n))
    return header, entries


def read(path):
    return open(path, encoding='utf-8').read() if os.path.exists(path) else ''


def atomic_write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def slot_table(entries):
    rows = ['| # | Proyecto | Dir | Última sesión |', '|---|---|---|---|']
    for i, e in enumerate(entries, 1):
        proj = re.sub(r'\s+', ' ', e.project or e.title).replace('|', '/')
        if len(proj) > 48:
            proj = proj[:47] + '…'
        rows.append(f'| {i} | {proj} | {tilde(e.dir) if e.dir else "?"} | {e.date} |')
    return '\n'.join(rows)


def write_card(entries):
    entries = sorted(entries, key=Entry.key, reverse=True)  # newest save first
    header = (
        '# Session Log — Memory Card\n\n'
        f'Un slot por proyecto con su última sesión (máx. {MAX_SLOTS}). Al hacer sign-off, el save nuevo '
        'sobreescribe el slot del proyecto y el anterior pasa a `~/.claude/session-log-history.md` '
        '(buscar ahí con grep por proyecto o fecha; no leer ese archivo completo).\n\n'
        + slot_table(entries) + '\n'
    )
    body = '\n\n---\n\n'.join(e.text for e in entries)
    atomic_write(CARD, header + ('\n---\n\n' + body + '\n' if entries else ''))
    return entries


def append_history(entries):
    if not entries:
        return
    if not os.path.exists(HIST):
        atomic_write(HIST, '# Session Log — History\n')
    with open(HIST, 'a', encoding='utf-8') as f:
        for e in entries:
            f.write('\n---\n\n' + e.text + '\n')


def load_card():
    return split(read(CARD))[1]


def cmd_save(project_dir, entry_file):
    d = norm(project_dir)
    new = Entry(read(entry_file))
    if not new.header.startswith('## '):
        sys.exit('entry must start with a "## Session: YYYY-MM-DD HH:MM" header')
    if not new.date:
        sys.exit('entry header needs a date: "## Session: YYYY-MM-DD HH:MM"')
    if new.dir is None:
        new = new.with_dir(d)
    elif new.dir != d:
        sys.exit(f'entry **Dir:** ({new.dir}) does not match project dir ({d})')

    entries = load_card()
    evicted = [e for e in entries if e.dir == d]
    kept = [e for e in entries if e.dir != d]
    new.pos = 10**9  # newest wins ties
    kept.append(new)
    kept.sort(key=Entry.key, reverse=True)
    overflow, kept = kept[MAX_SLOTS:], kept[:MAX_SLOTS]
    evicted += overflow

    append_history(evicted)   # history first: a crash here duplicates at worst, never loses a save
    write_card(kept)
    what = f'overwrote slot ({evicted[0].date} -> history)' if evicted and evicted[0].dir == d else 'new slot'
    extra = f', {len(overflow)} oldest slot(s) evicted to history' if overflow else ''
    print(f'saved {tilde(d)}: {what}{extra}. {len(kept)}/{MAX_SLOTS} slots used.')


def cmd_index():
    entries = write_card(load_card())
    print(f'index rebuilt: {len(entries)}/{MAX_SLOTS} slots')


def cmd_list():
    print(slot_table(sorted(load_card(), key=Entry.key, reverse=True)))


def cmd_show(project_dir):
    d = norm(project_dir)
    for e in load_card():
        if e.dir == d:
            print(e.text)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ''
    if cmd == 'save' and len(argv) == 4:
        cmd_save(argv[2], argv[3])
    elif cmd == 'index':
        cmd_index()
    elif cmd == 'list':
        cmd_list()
    elif cmd == 'show' and len(argv) == 3:
        cmd_show(argv[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
