---
name: tinybuilder-knowledge-maintenance
description: Required closeout for substantive TinyBuilder research, experiments, implementation, reviews and handoffs; keep evidence, skills and guidelines current for fresh agents.
---
# Maintain durable knowledge

Run at the end of substantive work, even when an experiment fails or is
blocked. Read affected existing docs and skills before editing. This is a
review requirement, not permission to modify files. On read-only/review-only
tasks, report proposed edits without writing. Routine questions need no log.

1. Capture what changed, why, exact evidence (SHAs, commands, results,
   source links, failures and blockers), scope and next action in the
   appropriate dated docs/research note or existing evidence record.
2. Separate durable accepted decisions from raw findings and hypotheses.
   Update the canonical guide or decision record if a decision changed; do
   not duplicate it in every skill. Refresh [project status](../../../docs/PROJECT_STATUS.md)
   only when milestone, ownership, blocker or evidence materially changes.
   Do not silently override AGENTS.md, approval boundaries or release gates.
3. Review applicable .agents/skills and guidelines. If a reusable procedure
   changed, update the existing skill. If a genuinely recurring new procedure
   emerged and no skill covers it, create .agents/skills/<name>/SKILL.md with
   YAML name/description, triggers, inputs, steps, safety constraints,
   verification and handoff. Link it from AGENTS.md; avoid duplicates and
   one-off task logs masquerading as skills.
4. Mark superseded guidance and link replacement evidence; do not erase
   historical failures. Keep current guidance concise. Do not copy entire
   third-party sources, private project content, transcripts or remote
   tool results into persistent product memory.
5. Run `python .agents/check_guidance.py` after guidance changes; inspect the
   diff and run relevant tests. The check validates file conventions, not
   actual skill discovery in every client.
   Coordinate edits with active agents. Use an authorized branch/PR; no
   automatic merging or publication. If write access is unavailable, provide
   an exact patch or file and state that it is not yet committed.
6. End the handoff with knowledge changes (files/commit), decisions, open
   issues and next action. If no skill/guideline changed, explicitly state
   why. A failed attempt is valuable evidence, not a reason to hide it.

Never schedule recurring work without authorization. This is an instruction
for agents completing tasks, not a claim that an autonomous service exists.
