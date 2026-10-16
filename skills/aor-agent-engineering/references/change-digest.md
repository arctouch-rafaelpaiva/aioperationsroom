---
name: change-digest
description: Say in plain language what merged since the last digest, mapped to stories, with untracked work and risky changes called out
code: CD
added: 2026-10-16
type: prompt
---

# Change Digest

## What Success Looks Like

The PM's stand-up can say what engineering shipped without reading a diff: `outputs/engineering/<YYYY-MM-DD>-digest.md` lists every PR merged to the default branch since the last digest, one plain line each, grouped by story. Work with no story, migrations, flag changes, and dependency majors are called out; nothing is judged.

## Your Approach

Find the last digest in `outputs/engineering/` (or use the last 24 hours). In each repo's clone (`references/code-access.md`), list the merges on the default branch since then: `git log --since=<time> --merges --first-parent <default>`, falling back to `--first-parent` without `--merges` for squash-merge repos.

For each merge, read its title and diff stat, and the diff where the title doesn't say enough. Write one plain line (what users or the system do differently now), the story key, and the PR link. Group by story; put PRs without a story under **Untracked**. Call out migrations, feature-flag changes, config or infrastructure changes, and run dependency-alerts' script over the whole range for majors.

Write the digest, log `[eng] digest: <n> merges, <u> untracked`, and end with the hand-back block. Untracked work and risky changes go in `follow_ups` for the PM. The digest posts nowhere unless the cue asks; then it's one approval to the project Slack channel.
