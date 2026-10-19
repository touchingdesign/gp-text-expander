#!/usr/bin/env python3
"""Check faq-data.js against the 2026-10-19 CSV standard.

Applies the same cleanup the rebuild used: markdown-unescape (\\ before
punctuation), normalize CRLF, and strip trailing whitespace on each line.
The malformed abbreviation that is itself a reply becomes anchorthread.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "backup" / "GPCA_FAQ_Export_2026-10-19.csv"
DATA_PATH = ROOT / "faq-data.js"
OLD_BACKUP = ROOT / "backup" / "faq-data_before_2026-10-19.csv"
INDEX_PATH = ROOT / "index.html"

MD_SPECIAL = set("\\`*_{}[]()#+-.!|>")
MALFORMED_PREFIX = "The Jeep factory screw has extra blank/ non-threaded tip"


def unescape_md(text):
    out = []
    found = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in MD_SPECIAL:
            found.append(text[i : i + 2])
            out.append(text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out), found


def clean_field(text):
    unescaped, found = unescape_md(text)
    normalized = unescaped.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines), found


def load_faq():
    raw = DATA_PATH.read_text(encoding="utf-8")
    prefix = "const FAQ_DATA = "
    if not raw.startswith(prefix) or not raw.rstrip().endswith(";"):
        raise SystemExit("faq-data.js is not a FAQ_DATA assignment")
    body = raw[len(prefix) :].rstrip()
    if body.endswith(";"):
        body = body[:-1]
    data = json.loads(body)
    for entry in data:
        if set(entry) != {"a", "t", "q", "r"}:
            raise SystemExit(f"unexpected keys on {entry.get('a')}: {sorted(entry)}")
    return data


def main():
    index = INDEX_PATH.read_text(encoding="utf-8")
    if "backup/" in index or "faq-data_before" in index:
        raise SystemExit("index.html references the backup files")

    upload = Path("/home/ubuntu/.cursor/projects/workspace/uploads/GPCA_FAQ_Export_2026-10-19_3203.csv")
    if upload.exists() and upload.read_bytes() != CSV_PATH.read_bytes():
        raise SystemExit("backup CSV is not a byte-for-byte copy of the attached export")

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if rows[0] != ["Abbreviation", "Category", "Answer / Response"]:
        raise SystemExit(f"unexpected CSV header: {rows[0]}")
    data_rows = rows[1:]
    faq = load_faq()
    if len(faq) != 242 or len(data_rows) != 242:
        raise SystemExit(f"count mismatch csv={len(data_rows)} faq={len(faq)}")

    escapes = []
    for row, entry in zip(data_rows, faq):
        abbr, category, answer = row
        if abbr.startswith(MALFORMED_PREFIX):
            abbr = "anchorthread"
        category_clean, found_category = clean_field(category)
        answer_clean, found_answer = clean_field(answer)
        escapes.extend(found_category)
        escapes.extend(found_answer)
        if entry["a"] != abbr or entry["t"] != category_clean or entry["r"] != answer_clean:
            raise SystemExit(
                "mismatch for "
                + abbr
                + "\n faq abbr/cat: "
                + repr((entry["a"], entry["t"]))
                + "\n csv abbr/cat: "
                + repr((abbr, category_clean))
                + "\n answer equal: "
                + str(entry["r"] == answer_clean)
            )
        if not entry["q"].strip():
            raise SystemExit("empty question for " + abbr)

    with OLD_BACKUP.open(encoding="utf-8-sig", newline="") as handle:
        old_rows = list(csv.reader(handle))
    if old_rows[0] != ["Abbreviation", "Category", "Question", "Answer / Response"]:
        raise SystemExit("old backup header is wrong")
    if len(old_rows) - 1 != 238:
        raise SystemExit(f"old backup count {len(old_rows) - 1}, expected 238")

    print(f"OK {len(faq)} entries match the CSV word for word")
    print(f"markdown escapes unescaped: {escapes or 'none'}")
    print(f"old backup rows: {len(old_rows) - 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
