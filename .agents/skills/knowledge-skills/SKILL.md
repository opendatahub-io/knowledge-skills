---
name: knowledge-skills
description: >-
  Change a skill in this repo. Use when adding or editing a skill under
  skills/, its prompts, schemas, or scripts.
user-invocable: true
---

# knowledge-skills

Use this skill when changing this repo. Read
[the skill authoring guide](../../skills-authoring/README.md) for the
repo-specific workflow.

## Inputs

The skill, prompt, schema, or script to add or change.

## Change a skill

1. Read `README.md` and the closest skill under `skills/<name>/`.
2. Keep pipeline skills in `skills/<name>/`. `.agents/skills/` is this
   contributor skill only.
3. Keep the runner contract for that skill. knowledge-sync supplies inputs
   and applies outputs.
4. For `knowledge-repo`, keep review isolated from `artifacts/changes-summary.md`.
5. For `knowledge-extraction` and `wiki-curator`, verdicts go through that
   skill's `scripts/write_json.py` and `schemas/`.
6. For `enrich-reports`, field values go through `scripts/write-enrichment.py`.

Use the skill authoring guide for complete details.

## Validation

```bash
make lint
```
