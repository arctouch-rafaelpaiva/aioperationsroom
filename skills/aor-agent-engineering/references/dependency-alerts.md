---
name: dependency-alerts
description: Report what a change does to dependencies (added, removed, major bumps) and to other stories and teams, and alert when it matters
code: DA
added: 2026-10-16
type: prompt
---

# Dependency Alerts

## What Success Looks Like

For the change in the cue, the room knows two things it would otherwise find out late: which packages changed (with every major bump and new dependency named, and what it breaks or risks), and which stories or teams this work blocks, unblocks, or now depends on. An alert that needs action is one raised hand; everything else is a line in the read.

## Your Approach

**Packages.** In the clone (`references/code-access.md`), run `uv run scripts/deps_diff.py git --repo <clone> --base <default branch> --head pr-<number>` (or the refs the cue names). It reports added, removed, and changed dependencies per manifest, and flags major versions. For each major bump, read the package's changelog or release notes for breaking changes, and search the clone for the APIs they remove. For each new dependency, note what it's for, its license if it's unusual, and whether something already in the repo does the same job.

**Work.** From the story and Jira links, find what this change blocks or is blocked by, and look for other stories touching the same code or contract (an API, a schema, an event). A contract change other code relies on is a dependency even without a manifest change.

**Write it.** Write `outputs/engineering/<YYYY-MM-DD>-deps-<slug>.md` with the script's summary, each major bump and its consequence, the new dependencies, and the work dependencies. When it needs a decision (a breaking bump, a contract change another team relies on, a new blocker), raise one aor-signal `ask` for the PM, or one approval for a PR comment if the engineers should answer. A security advisory on a dependency in use is a fire (`other`, the advisory as ref).

**Log and hand back.** Log `[eng] deps <slug>: <summary>` with the path. End with the hand-back block, with dependency risks in `follow_ups`.
