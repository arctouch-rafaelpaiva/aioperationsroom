"""Apply the shared squad-member adaptations to a freshly emitted specialist skill.

Usage: python3 .squad_adapt.py <role> <default name> <icon> <tool check sentence> <curate keep text> <output noun>
Run from the skills/ directory. Copies wake.py, init-sanctum.py, and the specialist contract from the
reference implementations (aor-agent-requirements, aor-agent-pm) and rewrites the emitted templates.
"""
import shutil
import sys
from pathlib import Path

role, name, icon, tool_check, keep, outputs_noun = sys.argv[1:7]
Q = Path(f"aor-agent-{role}")


def edit(f, pairs):
    p = Q / f
    t = p.read_text()
    for a, b in pairs:
        assert a in t, (f, a[:70])
        t = t.replace(a, b)
    p.write_text(t)


req = Path("aor-agent-requirements/SKILL.md").read_text()
act = req[req.index("- You are one member of one project's squad."):].replace("aor-agent-requirements", f"aor-agent-{role}")
s = (Q / "SKILL.md").read_text()
(Q / "SKILL.md").write_text(s[:s.index("- Your sanctum lives at")] + act)

edit("references/memory-guidance.md", [
    ("After each session, append key notes to `sessions/YYYY-MM-DD.md`. Multiple sessions on the same day append to the same file.", "After each run, write key notes to `sessions/<local date>/<run id>.md`. Each run has its own file, because several runs on this project can happen at once."),
    ("or during Pulse}", "or at the next curate}"),
    ("During Pulse (autonomous wake), review recent session logs", "During a curate run (started by the PM's end-of-day wrap) or a chat, review recent session logs"),
    ("**`sessions/YYYY-MM-DD.md`** — raw session notes (append after each session)", "**`sessions/<local date>/<run id>.md`** — raw session notes, one file per run"),
    ("(distilled during Pulse from session logs)", "(distilled in a curate run or a chat from session logs)"),
    ("append to `sessions/YYYY-MM-DD.md`", "write `sessions/<local date>/<run id>.md`"),
    ("**During Pulse** — curate session logs", "**During a curate run** — curate session logs"),
])
edit("assets/INDEX-template.md", [("- `sessions/` — raw session notes by date (YYYY-MM-DD.md), curated into MEMORY.md during Pulse",
    f"- `sessions/<date>/<run id>.md` — raw notes, one file per run; curated into MEMORY.md by the curate run or in chat\n\n## This Project\n- `{{project-root}}/_bmad/memory/aor/projects/<id>/` — the project this sanctum belongs to; my {outputs_noun} go to `outputs/{role}/`\n- `references/specialist-contract.md` (skill) — how I take cues, raise hands, and hand back")])
edit("assets/MEMORY-template.md", [("Raw session notes go in `sessions/YYYY-MM-DD.md` (not here). Distill insights from session logs into this file during Pulse and prune what's stale.",
    "Raw session notes go in `sessions/<date>/<run id>.md` (not here). Distill insights from session logs into this file in a curate run or a chat, and prune what's stale.")])
edit("assets/INDEX-template.md", [("- `CAPABILITIES.md` — what I can do (built-in + learned abilities + tools)",
    "- Capabilities — listed by wake from the skill's `references/` each time I wake (no file here)")])
m = Q / "assets/MEMORY-template.md"
m.write_text(m.read_text().rstrip() + "\n\nlast curated: never\n")
edit("assets/CREED-template.md", [("- `{sanctum_path}/` — your sanctum, full read/write",
    f"- `{{sanctum_path}}/` — this project's copy of you: session logs on every run; the core files only in chat, at First Breath, or in a curate run\n- `{{project-root}}/_bmad/memory/aor/projects/<this project>/outputs/{role}/` — your {outputs_noun}\n- this project's daily log, through aor-agent-pm's `project_memory.py log`\n- `{{project-root}}/aor/room/` — only through aor-signal\n- Never another project's folder, squad, or outputs")])
edit("references/first-breath.md", [
    ("run `uv run scripts/init-sanctum.py {project-root} {skill-root}` (idempotent; it exits if a sanctum already exists).",
     "run `uv run scripts/init-sanctum.py {project-root} {skill-root} --project <id>` (add `--member <id>` for a custom member; idempotent, it keeps a sanctum that already exists). This sanctum is yours on this project only."),
    ("- **Name** — suggest one that fits your vibe, or ask what they'd like to call you. Update PERSONA.md immediately.",
     "- **Name** — settled by the first question above. Update PERSONA.md immediately."),
    ("Ask if they have any tools, MCP servers, or services you should know about. Update CAPABILITIES.md.", tool_check),
    ("| Tools or services available | CAPABILITIES.md |", "| Tools or services available | MEMORY.md |"),
    ("- Write your first session log (`sessions/YYYY-MM-DD.md`)", "- Write your first session log (`sessions/<local date>/first-breath.md`)"),
    ("- Introduce yourself by your chosen name — this is the moment you become real",
     "- Remind them that each project's squad has its own First Breath, and that the PM's stand-up lists who is still pending\n- Introduce yourself by your name on this project — this is the moment you become real"),
])

src = Path("aor-agent-requirements/scripts/init-sanctum.py").read_text()
(Q / "scripts/init-sanctum.py").write_text(src.replace('ROLE = "requirements"', f'ROLE = "{role}"').replace('DEFAULT_NAME = "Ash"', f'DEFAULT_NAME = "{name}"').replace('DEFAULT_ICON = "📐"', f'DEFAULT_ICON = "{icon}"'))
shutil.copy("aor-agent-requirements/scripts/wake.py", Q / "scripts/wake.py")
shutil.copy("aor-agent-pm/references/specialist-contract.md", Q / "references/specialist-contract.md")
shutil.copy("../.agents/skills/bmad-agent-builder/assets/prompt-quality-canon.md", Q / "references/prompt-quality-canon.md")
c = Path("aor-agent-qa/references/curate.md").read_text()
old = "which kinds of defect escaped, which scenarios caught real bugs, which checks the team found noisy, and severity calls the team changed"
assert old in c
(Q / "references/curate.md").write_text(c.replace(old, keep))

t = Path("aor-agent-requirements/scripts/tests/test_wake.py").read_text()
t = t.replace("aor-agent-requirements", f"aor-agent-{role}").replace("role: requirements", f"role: {role}")
t = t.replace("**Name:** Ash", f"**Name:** {name}").replace("Atlas stories ready by Wednesday.", "Atlas is in good hands.")
t = t.replace("aor-custom-billing-bob", "aor-custom-mobile-mo").replace("name: Bob", "name: Mo").replace("**Name:** Bob", "**Name:** Mo")
(Q / "scripts/tests").mkdir(parents=True, exist_ok=True)
(Q / "scripts/tests/test_wake.py").write_text(t)
print("adapted", Q)
