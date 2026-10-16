---
name: glossary-check
description: Keep the product's words consistent: find avoided terms in docs, tickets, and designs, propose glossary entries for undefined terms, and keep the glossary itself sound
code: GL
added: 2026-10-16
type: prompt
---

# Glossary Check

## What Success Looks Like

The glossary is sound (every term defined once, no word both preferred and avoided), every use of an avoided word in the sources in scope is listed with its location and the preferred term, and repeated terms nobody has defined are proposed as new entries. Corrections are drafted per document, not per word.

## Your Approach

Set your room status to `reading`. Load the glossary from where BOND says it lives (a Notion page or database), and write it as `outputs/docs/glossary.yaml` in this shape, updating that file on every run:

```yaml
terms:
  - term: Cancel order
    definition: Stops an unpaid order; nothing is charged.
    avoid: [Void, Cancel purchase]
```

Run `uv run scripts/glossary.py check --glossary outputs/docs/glossary.yaml` and treat its errors as findings about the glossary itself.

**Collect the text** in scope (the cue's pages, stories, frames, or the whole project's recent changes) and save each as plain text in a scratch directory outside the project, one file per source, with the source link on the first line. Run `glossary.py scan` over them for avoided words and `glossary.py candidates` for repeated undefined terms. The scan is literal: read each hit in context and drop the ones where the word means something else.

**Write and raise.** Write `outputs/docs/<YYYY-MM-DD>-glossary-<scope>.md`: glossary problems, hits grouped by document (with the line and the preferred term), and proposed entries with a draft definition from how the sources use the term. Raise one approval per document with hits (a comment on that page, story, or frame listing its corrections), and one approval to add the agreed entries to the glossary page (`--target notion --action update_page`).

**Log and hand back.** Log `[docs] glossary <scope>: <hits> hits in <d> documents, <c> new terms`. Set your status to `idle`, and end with the hand-back block.
