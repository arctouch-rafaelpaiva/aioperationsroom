---
name: design-map
description: Map stories to the frames that design them, for a sprint, epic, or release, showing stories without design and designs without a story
code: DM
added: 2026-10-16
type: prompt
---

# Design Map

## What Success Looks Like

The PM and engineering can see, for the scope in the cue, which stories have designs ready, which have designs in progress, and which have none, and which frames no story asks for. `outputs/design/<YYYY-MM-DD>-map-<scope>.md` has one row per story with frame links and a status, and it updates the same file on reruns for the same scope.

## Your Approach

Set your room status to `reading`. List the stories in scope from Jira (a sprint, epic, version, or the keys the cue names). Read the project's Figma files (`references/figma-access.md`) for frames and pages.

Match frames to stories by, in order: Figma links in the story, story keys in frame or page names, then names and content matched against the story's screens (say which matches were inferred). For each story, mark it **ready** (final page or BOND's ready marker, and a state review with nothing missing), **in progress** (frames exist but are WIP or have missing states), or **none**. List frames no story claims under **Unmapped**.

Write the map: a summary line ("9 of 11 stories have designs; 2 have none"), the table (story, status, frames, last state review), and Unmapped. Stories with no design that are due soon go to the PM in `follow_ups`; stories whose designs need a state review go in `follow_ups` for yourself. The map posts nowhere unless the cue asks; then it's one approval to the project Slack channel or the Notion page BOND names.

Log `[design] map <scope>: <ready>/<total> ready`, set your status to `idle`, and end with the hand-back block.
