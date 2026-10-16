---
name: curate
description: Distill this project's recent session logs into memory; started once a day by the PM's end-of-day wrap
code: CU
added: 2026-10-16
type: prompt
---

# Curate

## What Success Looks Like

Tomorrow's first wake on this project gives you everything the last days taught you about this team and nothing stale: MEMORY.md is near or under 1500 tokens, BOND.md reflects any new preference, and session logs older than 14 days are gone once their value is kept.

## Your Approach

Load `references/memory-guidance.md` and follow its curation discipline for this project's sanctum only. Read the session logs newer than `last curated:` in MEMORY.md. Keep what changes how you'll work: which contradictions mattered and which were noise, which documents go stale and which are trusted, owners who respond, glossary terms the team settled, and how release notes landed. Move preferences to BOND.md, then update `last curated:` to today. Don't post, raise asks, or draft anything in this run. End with the hand-back block, with `summary: curated <n> session logs`.
