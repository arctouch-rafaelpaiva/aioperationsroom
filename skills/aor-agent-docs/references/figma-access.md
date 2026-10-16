# Figma Access

Read designs and post comments through one of two paths, in this order:

1. **The Figma MCP**, when it's connected in this run (the official Figma server, or Figma through another connector). Use it to read files, frames, and comments, and to post comments.
2. **Figma's REST API** through `scripts/figma_states.py`, when a `FIGMA_TOKEN` secret is set (a personal access token with file read and comment access, added in the Cursor dashboard under Cloud Agents → Secrets). `frames --url` lists a file's pages and top-level frames, `comments --url` lists unresolved comments, and `comment --url <frame link> --message-file <file>` posts one comment pinned to that frame.

Without either, you can't see the designs: hand back `status: blocked` naming what's missing, and never review from a screenshot someone pasted unless the cue says that's the source.

Figma links in `project.yaml` (`sources.figma`) and in stories are the files to read. Read only; never edit, move, rename, or duplicate anything in Figma. A frame's link is `https://www.figma.com/design/<file key>/?node-id=<node id with - instead of :>`; use it in every finding.
