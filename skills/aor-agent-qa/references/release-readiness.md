---
name: release-readiness
description: Give a release a go, go-with-risks, or no-go verdict from the evidence: AC results, open defects, and the team's release gates
code: RE
added: 2026-10-16
type: prompt
---

# Release Readiness

## What Success Looks Like

The operator and the team decide whether to ship by reading one page: `outputs/qa/<YYYY-MM-DD>-release-<name>.md`. It opens with the verdict, then every reason for it, each with a link, then a story-by-story table. The verdict comes from `scripts/qa_matrix.py verdict` and the team's release gates, never from a feeling, and every risk in a go-with-risks is named.

## Your Approach

Set your room status to `reading`. Identify the release scope the cue names (a version, sprint, or date in Jira) and its stories. For each story, make sure its scenario file is current: run coverage-check on its merged PRs if results are missing, and leave an AC untested rather than guess.

**Collect defects.** From Jira, every defect linked to the scope or found since the last release, as JSON for the script: `[{"key", "summary", "severity", "open", "story"}]`, using the team's severities.

**Compute.** Run `uv run scripts/qa_matrix.py verdict --file <each scenario file> --defects <file> --block <BOND's blocking severities> --format md`. Then apply any extra gates BOND names (a regression suite run, a sign-off). A failed gate makes it no-go; an unchecked gate makes it at best go-with-risks.

**Write it.** Write the release page: the verdict and the one-line why; the blocking reasons; the risks, each with what would retire it and who owns it; the script's table; the gates and their state; and the evidence links. Stay neutral; the decision is the operator's.

**Share it** when the cue asks or BOND names a place: one aor-signal approval to post the page's summary to the project Slack channel (`--target slack --action post_message`) or the Notion release page (`--target notion --action update_page`). A no-go on a release due today is also a fire (`missed_deadline`, the release as ref).

**Log and hand back.** Log `[qa] release <name>: <verdict>` with the page path. Set your status to `idle`, and end with the hand-back block, quoting the verdict in `summary`.
