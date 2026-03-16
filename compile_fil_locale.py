"""
Compile locale/fil/LC_MESSAGES/django.po to django.mo using pure Python (no gettext, no polib).
Run from project root: python compile_fil_locale.py
"""
import os
import re
import struct
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
po_path = os.path.join(BASE_DIR, "locale", "fil", "LC_MESSAGES", "django.po")
mo_path = os.path.join(BASE_DIR, "locale", "fil", "LC_MESSAGES", "django.mo")


def parse_po(po_path):
    """Parse a .po file and yield (msgid, msgstr) pairs. Skips header (msgid "")."""
    with open(po_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Split by msgid, then for each block get msgid and msgstr (handle multiline)
    blocks = re.split(r"\nmsgid\s+", content, flags=re.MULTILINE)
    for block in blocks:
        if not block.strip():
            continue
        # First block may be empty or header (starts with "")
        if block.strip().startswith('"'):
            msgid = _extract_quoted_string(block)
            if msgid is None:
                continue
            # Skip the metadata entry (empty msgid)
            if msgid == "":
                continue
            msgstr = _extract_msgstr(block)
            if msgstr is not None:
                yield (msgid, msgstr)


def _extract_quoted_string(block):
    """Get the first quoted string from a block (handles multi-line "" strings)."""
    start = block.find('"')
    if start == -1:
        return None
    result = []
    i = start + 1
    while i < len(block):
        if block[i] == "\\":
            if i + 1 < len(block):
                n = block[i + 1]
                if n == "n":
                    result.append("\n")
                elif n == "t":
                    result.append("\t")
                elif n == '"':
                    result.append('"')
                elif n == "\\":
                    result.append("\\")
                else:
                    result.append(n)
                i += 2
                continue
        if block[i] == '"':
            # End of string (could be multiline: "line1"\n"line2")
            i += 1
            while i < len(block) and block[i] in " \t":
                i += 1
            if i < len(block) and block[i] == "\n":
                i += 1
                while i < len(block) and block[i] in " \t":
                    i += 1
                if i < len(block) and block[i] == '"':
                    i += 1
                    continue  # multiline, keep reading
            return "".join(result)
        result.append(block[i])
        i += 1
    return "".join(result) if result else None


def _extract_msgstr(block):
    """Extract msgstr value from a block (after msgid)."""
    match = re.search(r"\nmsgstr\s+", block)
    if not match:
        return None
    rest = block[match.end() :]
    return _extract_quoted_string(rest)


# Header required so gettext uses UTF-8 when decoding (avoids UnicodeDecodeError: 'ascii')
MO_HEADER = "Content-Type: text/plain; charset=UTF-8\n"


def write_mo(mo_path, entries):
    """
    Write a .mo file (GNU gettext binary format).
    entries: list of (msgid, msgstr) tuples. First entry must be ("", header) with charset=UTF-8.
    """
    # Ensure ( "", header ) is first so Python gettext decodes strings as UTF-8
    if not entries:
        entries = [("", MO_HEADER)]
    elif entries[0][0] != "":
        entries = [("", MO_HEADER)] + list(entries)
    else:
        entries = [("", MO_HEADER)] + list(entries)[1:]

    # Encode all strings as utf-8
    orig_list = []
    trans_list = []
    for o, t in entries:
        orig_list.append(o.encode("utf-8") if isinstance(o, str) else o)
        trans_list.append(t.encode("utf-8") if isinstance(t, str) else t)

    n = len(orig_list)
    # Offsets: 5 * 4 bytes after header; then hashing table (we use size 0), then two tables of 2*4 bytes each, then strings
    o_len = sum(len(x) + 1 for x in orig_list)  # +1 for trailing NUL
    t_len = sum(len(x) + 1 for x in trans_list)
    # Table: for each string we store length (4 bytes) and file offset (4 bytes)
    # Header: 7 * 4 = 28 bytes
    # Hash table: size 0, offset 0 -> we'll put offset to originals table at 28, translations at 28 + n*8
    # So: originals_table at 28, translations_table at 28 + n*8, originals data at 28 + n*16, translations data after
    originals_table_offset = 28
    translations_table_offset = 28 + n * 8
    originals_data_offset = 28 + n * 16
    translations_data_offset = originals_data_offset + o_len

    with open(mo_path, "wb") as f:
        # Magic (little endian)
        f.write(struct.pack("I", 0x950412DE))
        f.write(struct.pack("I", 0))  # revision
        f.write(struct.pack("I", n))
        f.write(struct.pack("I", originals_table_offset))
        f.write(struct.pack("I", translations_table_offset))
        f.write(struct.pack("I", 0))  # hash table size
        f.write(struct.pack("I", 0))  # hash table offset

        # Originals table: length, offset for each string
        o_off = originals_data_offset
        for s in orig_list:
            f.write(struct.pack("I", len(s)))
            f.write(struct.pack("I", o_off))
            o_off += len(s) + 1

        # Translations table: length, offset for each string
        t_off = translations_data_offset
        for s in trans_list:
            f.write(struct.pack("I", len(s)))
            f.write(struct.pack("I", t_off))
            t_off += len(s) + 1

        # Originals data (each string + NUL)
        for s in orig_list:
            f.write(s)
            f.write(b"\x00")

        # Translations data (each string + NUL)
        for s in trans_list:
            f.write(s)
            f.write(b"\x00")


def main():
    if not os.path.isfile(po_path):
        print(f"Not found: {po_path}", file=sys.stderr)
        sys.exit(1)

    entries = list(parse_po(po_path))
    write_mo(mo_path, entries)
    print(f"Compiled: {mo_path}")


if __name__ == "__main__":
    main()
