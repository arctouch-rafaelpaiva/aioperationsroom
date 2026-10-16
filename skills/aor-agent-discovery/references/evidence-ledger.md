# Evidence Ledger

One ledger per project: `outputs/discovery/evidence.yaml`. Every run that reads feedback adds to it, and every theme, brief, and answer about "what users want" is computed from it with `scripts/evidence.py`, never from memory. Entries are append-only; fix a mistake by correcting the entry, never by deleting evidence you don't like.

```yaml
goals:
  G2: Cut support load 20% by Q1          # mirror BOND's Goals
themes:
  refund-delay: { name: Refunds take too long, goal: G2 }
  csv-export: { name: CSV export of orders }          # no goal yet: say so
evidence:
  - id: ev-014
    date: 2026-10-12                      # when it was said or happened
    source: support                       # jira notion slack support interview survey analytics stakeholder sales other
    ref: https://acme.atlassian.net/browse/SUP-311
    who: Customer C (Enterprise)          # anonymized; one stable label per person
    segment: enterprise
    quote: "We wait a week to know if a refund went through."
    themes: [refund-delay]
```

**Rules.** Quote exactly, in the original language, short enough to be one point. One entry per person per point: the same customer repeating themselves in one thread is one entry, a new channel or a new week is another. Keep each person's `who` label stable across entries, because the script counts distinct people by it. Never put names, emails, or phone numbers of end users in `who` or `quote` (the script rejects emails and phone numbers); stakeholders may be named only if BOND allows it. Evidence that fits no theme yet stays untagged until a pattern appears.

**Strength,** as the script computes it: **strong** is 3 or more people across 2 or more channels, **emerging** is 2 or more people, and **anecdote** is one person, however loud.
