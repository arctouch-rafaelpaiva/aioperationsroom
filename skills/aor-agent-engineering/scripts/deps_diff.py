#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""aor-agent-engineering: what a change does to dependencies, without guessing.

Compares dependency manifests between two git refs (or two files) and reports every
dependency added, removed, or changed, flagging major version changes (for 0.x, a
minor change counts as major). Lockfiles are ignored; manifests state intent.

Manifests: package.json (dependencies, devDependencies, peerDependencies,
optionalDependencies), requirements*.txt, pyproject.toml (project dependencies and
optional-dependencies, dependency-groups, tool.poetry), go.mod, Cargo.toml.

Usage:
  uv run deps_diff.py git --repo <clone> --base <ref> --head <ref>
  uv run deps_diff.py files --base <old manifest> --head <new manifest> [--name package.json]

Output is JSON: {"ok", "manifests": [{"path", "added", "removed", "changed"}], "major": [...], "summary"}.
Exit codes: 0 ok (changes or not), 2 bad input (unknown manifest, unreadable file, git error).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

NPM_GROUPS = {"dependencies": "", "devDependencies": "dev", "peerDependencies": "peer", "optionalDependencies": "optional"}
REQ_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*?)\s*(?:;.*)?$")


class BadInput(Exception):
    pass


def kind(path: str) -> str | None:
    name = PurePosixPath(path).name
    if name in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml"):
        return name
    if re.fullmatch(r"requirements[\w.-]*\.txt", name):
        return "requirements.txt"
    return None


def norm_py(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(lines, group: str = "") -> dict:
    out = {}
    for raw in lines:
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith(("#", "-")) or "://" in line:
            continue
        m = REQ_LINE.match(line)
        if m:
            out[norm_py(m[1]) + (f" ({group})" if group else "")] = m[3].strip() or "*"
    return out


def parse(kind_: str, text: str) -> dict:
    if not text.strip():
        return {}
    try:
        if kind_ == "package.json":
            data = json.loads(text)
            return {f"{n} ({g})" if g else n: str(v) for key, g in NPM_GROUPS.items() for n, v in (data.get(key) or {}).items()}
        if kind_ == "requirements.txt":
            return parse_requirements(text.splitlines())
        if kind_ == "go.mod":
            out, block = {}, False
            for line in text.splitlines():
                line = line.split("//", 1)[0].strip()
                if line.startswith("require ("):
                    block = True
                elif block and line == ")":
                    block = False
                elif block or line.startswith("require "):
                    parts = line.removeprefix("require ").split()
                    if len(parts) >= 2:
                        out[parts[0]] = parts[1]
            return out
        data = tomllib.loads(text)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise BadInput(f"{kind_} does not parse: {exc}") from exc
    if kind_ == "Cargo.toml":
        out = {}
        for table, g in (("dependencies", ""), ("dev-dependencies", "dev"), ("build-dependencies", "build")):
            for n, v in (data.get(table) or {}).items():
                ver = v if isinstance(v, str) else v.get("version", v.get("git", v.get("path", "*")))
                out[f"{n} ({g})" if g else n] = str(ver)
        return out
    project = data.get("project") or {}
    out = parse_requirements(project.get("dependencies") or [])
    for g, reqs in (project.get("optional-dependencies") or {}).items():
        out |= parse_requirements(reqs, g)
    for g, reqs in (data.get("dependency-groups") or {}).items():
        out |= parse_requirements([r for r in reqs if isinstance(r, str)], g)
    poetry = (data.get("tool") or {}).get("poetry") or {}
    for n, v in (poetry.get("dependencies") or {}).items():
        if n.lower() != "python":
            out[norm_py(n)] = str(v if isinstance(v, str) else v.get("version", "*"))
    return out


def major_of(spec: str) -> tuple[int, ...] | None:
    m = re.search(r"v?(\d+)(?:\.(\d+))?", spec)
    if not m:
        return None
    major, minor = int(m[1]), int(m[2] or 0)
    return (0, minor) if major == 0 else (major,)


def diff(path: str, old: dict, new: dict) -> dict:
    added = [{"name": n, "version": new[n]} for n in sorted(new.keys() - old.keys())]
    removed = [{"name": n, "version": old[n]} for n in sorted(old.keys() - new.keys())]
    changed = []
    for n in sorted(old.keys() & new.keys()):
        if old[n] != new[n]:
            a, b = major_of(old[n]), major_of(new[n])
            changed.append({"name": n, "from": old[n], "to": new[n], "major": a is not None and b is not None and a != b})
    return {"path": path, "added": added, "removed": removed, "changed": changed}


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and res.returncode:
        raise BadInput(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res


def from_git(repo: str, base: str, head: str) -> list[dict]:
    fork = git(repo, "merge-base", base, head).stdout.strip()
    names = git(repo, "diff", "--name-only", fork, head).stdout.split()
    out = []
    for path in sorted(p for p in names if kind(p)):
        old = git(repo, "show", f"{fork}:{path}", check=False)
        new = git(repo, "show", f"{head}:{path}", check=False)
        out.append(diff(path, parse(kind(path), old.stdout if old.returncode == 0 else ""),
                        parse(kind(path), new.stdout if new.returncode == 0 else "")))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["git", "files"])
    p.add_argument("--repo", help="git: a clone of the project repo")
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--name", help="files: the manifest type when the file names don't show it")
    args = p.parse_args(argv)
    try:
        if args.mode == "git":
            if not args.repo:
                raise BadInput("git mode needs --repo")
            manifests = from_git(args.repo, args.base, args.head)
        else:
            k = kind(args.name or args.head)
            if not k:
                raise BadInput("not a known manifest; pass --name package.json|requirements.txt|pyproject.toml|go.mod|Cargo.toml")
            read = lambda f: Path(f).read_text(encoding="utf-8") if Path(f).exists() else ""
            manifests = [diff(args.name or Path(args.head).name, parse(k, read(args.base)), parse(k, read(args.head)))]
    except (BadInput, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    manifests = [m for m in manifests if m["added"] or m["removed"] or m["changed"]]
    major = [f"{m['path']}: {c['name']} {c['from']} -> {c['to']}" for m in manifests for c in m["changed"] if c["major"]]
    counts = {k: sum(len(m[k]) for m in manifests) for k in ("added", "removed", "changed")}
    summary = "no dependency changes" if not manifests else (
        f"{counts['added']} added, {counts['removed']} removed, {counts['changed']} changed ({len(major)} major)")
    print(json.dumps({"ok": True, "manifests": manifests, "major": major, "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
