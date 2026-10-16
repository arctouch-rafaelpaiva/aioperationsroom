#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""aor-agent-docs: keep the product's words consistent.

Glossary (YAML, references/glossary-check.md):
  terms:
    - term: Cancel order
      definition: Stops an unpaid order; nothing is charged.
      avoid: [Void, Cancel purchase]

  check       the glossary itself: every term has a definition, no duplicate terms, no
              word both a term and an avoid, no avoid listed under two terms.
  scan        text files (saved pages, tickets, exported copy) for avoided words; every
              hit has the file, line, the word found, the preferred term, and context.
  candidates  repeated Title Case phrases and acronyms in the files that the glossary
              doesn't define yet (--min occurrences, default 3).

Matching is case-insensitive on whole words. Lines inside fenced code blocks are skipped.

Usage:
  uv run glossary.py check --glossary <glossary.yaml>
  uv run glossary.py scan --glossary <glossary.yaml> --file <a.md> [--file <b.md> ...]
  uv run glossary.py candidates --glossary <glossary.yaml> --file <a.md> [...] [--min 3]

Exit codes: 0 ok (scan hits are reported, not failures), 1 invalid glossary, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

PHRASE = re.compile(r"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){1,3}|[A-Z]{2,6}s?)\b")
COMMON = {"The", "This", "That", "When", "Then", "Given", "And", "But", "If", "For", "In", "On", "As", "We", "It"}


def load(path: str) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    terms = data.get("terms") if isinstance(data, dict) else None
    if not isinstance(terms, list):
        raise ValueError("glossary needs terms: a list of {term, definition, avoid}")
    return [t for t in terms if isinstance(t, dict)]


def check(terms: list[dict]) -> dict:
    errors, seen, avoid_owner = [], {}, {}
    for t in terms:
        name = str(t.get("term", "")).strip()
        if not name:
            errors.append("an entry has no term")
            continue
        key = name.lower()
        if key in seen:
            errors.append(f"'{name}' is defined twice")
        seen[key] = name
        if not str(t.get("definition", "")).strip():
            errors.append(f"'{name}' has no definition")
        for a in t.get("avoid") or []:
            a_key = str(a).lower()
            if a_key in avoid_owner and avoid_owner[a_key] != name:
                errors.append(f"'{a}' is avoided under both '{avoid_owner[a_key]}' and '{name}'")
            avoid_owner[a_key] = name
    for a_key, owner in avoid_owner.items():
        if a_key in seen:
            errors.append(f"'{seen[a_key]}' is a term, but '{owner}' lists it under avoid")
    return {"ok": not errors, "terms": len(seen), "errors": errors}


def prose_lines(text: str):
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield n, line


def word_re(word: str) -> re.Pattern:
    return re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])", re.I)


def scan(terms: list[dict], files: list[str]) -> dict:
    rules = [(word_re(str(a)), str(a), t["term"]) for t in terms for a in t.get("avoid") or []]
    hits = []
    for f in files:
        for n, line in prose_lines(Path(f).read_text(encoding="utf-8")):
            for rx, _word, use in rules:
                for m in rx.finditer(line):
                    hits.append({"file": f, "line": n, "found": m[0], "use": use, "context": line.strip()[:160]})
    by_term = Counter(h["use"] for h in hits)
    return {"ok": True, "hits": hits, "summary": {t: c for t, c in by_term.most_common()}}


def candidates(terms: list[dict], files: list[str], minimum: int) -> dict:
    known = {str(t.get("term", "")).lower() for t in terms} | {str(a).lower() for t in terms for a in t.get("avoid") or []}
    counts: Counter[str] = Counter()
    where: dict[str, set[str]] = {}
    for f in files:
        for _n, line in prose_lines(Path(f).read_text(encoding="utf-8")):
            for m in PHRASE.finditer(line):
                words = m[0].split()
                before = re.sub(r"^[#>*\-\s]+", "", line[:m.start()]).rstrip()
                if len(words) > 1 and (not before or before[-1] in ".!?:"):
                    words = words[1:]
                while words and words[0] in COMMON:
                    words = words[1:]
                phrase = " ".join(words)
                if len(phrase) < 2 or phrase.lower() in known or phrase.rstrip("s").lower() in known:
                    continue
                counts[phrase] += 1
                where.setdefault(phrase, set()).add(f)
    out = [{"phrase": p, "count": c, "files": sorted(where[p])} for p, c in counts.most_common() if c >= minimum]
    return {"ok": True, "candidates": out}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "scan", "candidates"])
    p.add_argument("--glossary", required=True)
    p.add_argument("--file", action="append", default=[])
    p.add_argument("--min", type=int, default=3)
    args = p.parse_args(argv)
    try:
        terms = load(args.glossary)
        if args.cmd != "check" and not args.file:
            raise ValueError(f"{args.cmd} needs at least one --file")
        if args.cmd == "check":
            out = check(terms)
        elif args.cmd == "scan":
            out = scan(terms, args.file)
        else:
            out = candidates(terms, args.file, args.min)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "error": f"bad input: {exc}"}))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
