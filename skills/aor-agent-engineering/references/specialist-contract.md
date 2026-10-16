# Specialist Contract (v1)

How a squad member works inside one project of the AI Operations Room. The master copy lives in aor-agent-pm (`references/specialist-contract.md`); every specialist skill ships an identical copy. Change the master, then re-copy it everywhere.

## Squad and memory

Each project has its own squad: its PM and the members on its `project.yaml` roster. A member's id is its roster id: `aor-agent-<role>`, or `aor-custom-<slug>` for a custom member based on a specialist skill. Its name and persona overrides come from that roster entry.

A member's memory belongs to that project only, at `{project-root}/_bmad/memory/aor/projects/<project-id>/squad/<member id>/`:

| Path | Holds | Changes when |
|---|---|---|
| `PERSONA.md`, `CREED.md`, `BOND.md`, `INDEX.md` | Who this member is on this project, what it holds to, how this team works | First Breath or a chat with the operator, or a curate run |
| `MEMORY.md` | What it has learned on this project | A curate run or a chat |
| `sessions/<local date>/<run id>.md` | Raw notes, one file per run | Every run |

Never read or write another project's squad, and never carry what you learned on one project into another.

## The cue

The PM runs a specialist as a subagent with one scoped cue:

- **Wake:** `uv run scripts/wake.py {project-root} --project <id> --headless [--member <member id>] [--task <code>]`
- **Item:** the inbox item id and its link
- **Task:** the capability (code or name)
- **Done when:** what the output must let the next person do
- **Inputs:** links and memory paths

A cue without a project is invalid. In a chat with no project, ask which one, then wake with it.

## During the run

- **Room status:** aor-signal with `--project <id> --agent <member id>` (`reading`, `working`, `drafting`, then `idle`).
- **Outputs:** `outputs/<role>/<YYYY-MM-DD>-<slug>.md` (a custom member uses `outputs/<slug>/`). A rerun on the same item updates its own file.
- **Logs:** one line per meaningful step through aor-agent-pm's `project_memory.py log --project <id> --role <role>`.
- **Project files:** read anything in the project. Write only your outputs, your log lines, and your squad memory. Curated files and inbox statuses belong to the PM; new work you find goes into the hand-back as a follow-up.
- **External posts:** raise your own hand with aor-signal `approval --agent <member id>`, with the exact payload. Post only approved items, through your post-approved capability. Never post another member's item.
- **Calibration:** before this project's First Breath, work on the seed defaults and report `calibration: pending` in the hand-back. Never raise an ask for it; the PM's stand-up lists pending members once.
- **Questions:** at most one aor-signal `ask` per run, and only for what only the operator can decide. Anything else goes into the hand-back with a suggested owner.
- **Tools:** if a source's tool (Jira, Figma, GitHub, Notion MCP) isn't connected in this run, work from what you can read, mark the output as drafts only, and name the tool to connect.
- **Sync:** headless, don't sync; the PM's sync covers the project. In a chat, finish with `project_memory.py sync --project <id>`.

## The hand-back

End every headless run with exactly one fenced `handback` block. The PM closes the inbox item from it without re-reading your work.

```handback
status: done            # done | blocked | needs-operator | drafts-only
item: in-…              # the cue's inbox item, or none
summary: one line the stand-up can quote
outputs:
  - outputs/<role>/<file>.md
approvals: [ap-…]       # hands raised this run
asks: [q-…]
questions:
  - question: …
    owner: <role or person>
follow_ups:
  - one line per new piece of work for the PM to triage
decisions:              # optional: decisions found this run, for the PM's decisions.md
  - decision: …
    why: …
    by: <person>
    date: <YYYY-MM-DD>
    source: <link>
    supersedes: <earlier decision or none>
calibration: done       # pending until this project's First Breath
```

## Curate

The PM's end-of-day wrap starts `--task curate` once per day for every member with session logs since its last curation. Load `references/memory-guidance.md`, distill those logs into MEMORY.md (near or under 1500 tokens), update BOND.md and INDEX.md if something changed, record the date in MEMORY.md (`last curated: <date>`), and prune session logs older than 14 days once their value is captured. Nothing else runs in a curate.
