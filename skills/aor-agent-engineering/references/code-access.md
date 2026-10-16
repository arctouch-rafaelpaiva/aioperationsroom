# Code Access

Two kinds of access, and they come from different places.

**Reading code: git.** Cursor's GitHub connection (Integrations → Source Control) is what lets this run clone the project's repos. Clone each `sources.github` repo from `project.yaml` read-only into a scratch directory outside the ops repo, such as `<system temp dir>/aor/<project>/<repo>`: `git clone --filter=blob:none https://github.com/<owner>/<name>.git`. Reuse an existing clone with `git fetch`. A pull request's code is `git fetch origin pull/<number>/head:pr-<number>`; compare it against the default branch with `git diff <default>...pr-<number>`. Merged work since a date is `git log --since=<date> --merges` on the default branch. If cloning fails, the GitHub connection doesn't cover this repo: hand back `status: blocked` and say so.

**Talking to GitHub: a GitHub tool.** A PR's description, review comments, linked issues, CI check results, and posting a comment need a tool: the GitHub MCP when it's connected in this run, otherwise the `gh` CLI if `gh auth status` shows it's signed in. The GitHub event that started the triage run often carries the PR's title, description, and check results already; use what the cue contains first. Without a tool, read the code and work from the cue, and hand back drafts with `status: drafts-only` naming the missing tool. Never post another way.

Never copy secrets, keys, tokens, `.env` contents, or customer data from a repo into memory, outputs, or comments. Delete scratch clones you no longer need.
