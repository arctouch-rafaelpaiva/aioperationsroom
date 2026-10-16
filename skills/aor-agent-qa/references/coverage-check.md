---
name: coverage-check
description: Check a pull request against its story: which AC its tests and CI results cover, what's missing, and one drafted review comment
code: CC
added: 2026-10-16
type: prompt
---

# Coverage Check

## What Success Looks Like

For the PR in the cue, the scenario file of each linked story is updated with what this PR proves: tests found, results from its CI run, and evidence links. Every AC the PR claims to implement but doesn't test is named. If there are gaps, one review comment waits for approval, with the exact AC and the missing scenarios. A red default branch is a fire.

## Your Approach

Set your room status to `reading`. Read the PR through the GitHub tool: its description, the linked issues, the changed files (tests especially), and its latest CI run. If GitHub isn't connected in this run, stop here, and hand back `status: drafts-only` naming the tool.

**Find the story.** Use the PR's linked Jira keys, then the branch name or title. Without a story, note it in the hand-back as a follow-up ("PR #n has no story") and check the tests against the PR description only.

**Trace.** Open or create the story's scenario file (`references/scenario-format.md`; run test-scenarios first if none exists). For each scenario, set `test:` to the test in this PR that exercises it, and `status:` and `evidence:` from this PR's CI run (pass or fail, with the job link). Leave scenarios with no test `untested`. Run `scripts/qa_matrix.py check` and read the matrix.

**Report.** Write `outputs/qa/<YYYY-MM-DD>-coverage-pr<number>.md`: the AC the PR covers with evidence, the gaps (AC without a test, breaks without a test, failing tests), and anything the change touches that no story mentions. If there are gaps, raise one aor-signal `approval --target github --action comment --target-url <PR link>` with the review comment: the gaps as a short list, each with the scenario that would close it. Never approve or block the PR.

**Red builds.** If the default branch's latest CI run failed, raise `fire --project <id> --agent <member id> --reason failed_build --detail "<job: what failed>" --ref <run URL>`. If a fire for the same ref is active and the branch is green again, clear it with `fire --clear` and the same ref.

**Log and hand back.** Log `[qa] PR #<n>: <covered>/<total> AC covered` with the report path. Set your status to `idle`, and end with the hand-back block.
