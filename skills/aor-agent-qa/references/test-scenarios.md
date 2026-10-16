---
name: test-scenarios
description: Challenge a story before it's built and write the scenarios that trace every AC, including the ones that try to break it
code: TS
added: 2026-10-16
type: prompt
---

# Test Scenarios

## What Success Looks Like

A scenario file in `outputs/qa/` that `scripts/qa_matrix.py check` passes: every AC has at least one scenario and at least one that tries to break it, in the team's test format. Anything in the story that can't be tested as written is a challenge with an owner, raised while fixing it still costs a sentence. If the team wants the scenarios in Jira, there is one approved comment per story.

## Your Approach

Set your room status to `reading`. Read the story with its AC, rules, linked design, and dependencies, plus requirements' draft or review in `outputs/requirements/` when there is one.

**Challenge first.** For each AC ask: can a tester run this and get a yes or no? What happens at the edges (zero, the limit, one past it), in each state (empty, loading, error, offline, retried), for each kind of user (no permission, a second account), and with odd data (another currency, long text, accents)? Anything the story doesn't answer goes under `## Challenge` with the owner (usually requirements or design). Never answer it yourself with an assumption.

**Write the scenarios.** Set your status to `drafting`. Write `outputs/qa/<YYYY-MM-DD>-scenarios-<story key>.md` in the shape of `references/scenario-format.md`. Aim for the fewest scenarios that cover every AC and its edges, usually a happy path plus the breaks that matter, rather than every combination. Scenarios that depend on an open challenge are `blocked`. Link an existing automated test in `test:` when you find one in the repo.

**Check.** Run `uv run scripts/qa_matrix.py check --file <file>`. Fix every error, and treat each warning as a question.

**Raise your hand** if BOND says scenarios live in Jira, or the cue asks for it: one aor-signal `approval --target jira --action comment --target-url <story link>` whose payload is the scenarios as a short readable list (titles and Given/When/Then), plus the challenges. Otherwise the file is the deliverable.

**Log and hand back.** Log `[qa] <n> scenarios for <story>, <c> challenges` with the file path. Challenges become `questions` in the hand-back with their owners. Set your status to `idle`, and end with the hand-back block.
