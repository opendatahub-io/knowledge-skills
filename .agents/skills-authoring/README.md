# Skill Authoring

How to add or change a skill in this repository. The skill list stays in
`README.md`.

The invocable skill is
[`.agents/skills/knowledge-skills/SKILL.md`](../skills/knowledge-skills/SKILL.md).

## Setup

`make lint` runs skillsaw. It uses `SKILLSAW_BIN` when that variable is set,
and `uvx skillsaw` otherwise. CI runs the same linter via the skillsaw GitHub
Action (`.github/workflows/lint.yml`).

## Execution

Copy the closest existing skill under `skills/`. The skills-registry
marketplace entry for this plugin sets no `skills` path, so the installer only
picks up `skills/`, `.claude/skills/`, and `.opencode/skills/`.

| Piece | Path |
|-------|------|
| Prompt | `skills/<name>/SKILL.md` |
| Agent prompts | `skills/<name>/prompts/` |
| JSON schema | `skills/<name>/schemas/` |
| Writer script | `skills/<name>/scripts/` |
| Plugin manifest | `.claude-plugin/plugin.json` |

`name` in `SKILL.md` matches the directory.

`knowledge-repo` reads `artifacts/repo-context.json` (`forge`, `slug`) and
`artifacts/pr-data/{id}.json`. It writes `artifacts/`, including
`proposed-updates.patch`. The review prompt stays isolated from
`artifacts/changes-summary.md`. Extract agents run in the foreground, one PR
at a time. Revise runs once. Model choice is in that skill's `SKILL.md`.

`enrich-reports` reads `artifacts/case-study-skeletons/` and writes
`artifacts/enrichments/` through `scripts/write-enrichment.py`.

`knowledge-extraction` reads `artifacts/enriched-report.json` and edits `wiki/`
and `examples/`. `wiki-curator` edits the same trees. Both write `verdict.json`
through their own `scripts/write_json.py` and `schemas/`.

When a proposal keeps coming back rejected, add the exclusion to the target
repo's context file. This repository keeps no per-run memory.

## Validation

```bash
make lint
```

`make lint` is skillsaw. This repository has no unit-test target.

## Troubleshooting

| Symptom | Where to look |
|---------|----------------|
| Skill missing from the runner | Directory is not under `skills/`, `.claude/skills/`, or `.opencode/skills/` |
| skillsaw rejects the skill | `name` matches the directory. Limits are in `.skillsaw.yaml` |
| `knowledge-repo` stops in setup | `artifacts/repo-context.json` or `artifacts/pr-data/` is missing. knowledge-sync writes both |
| Review repeats the synthesis rationale | The review prompt must not receive `artifacts/changes-summary.md` |
| Extraction or curator finished with no verdict | `verdict.json` must pass that skill's `scripts/write_json.py` |
| Enrichment wrote a full case study | Field values go through `scripts/write-enrichment.py` into `artifacts/enrichments/` |

## Escalation

- Merge review: GitHub pull request on `opendatahub-io/knowledge-skills`
- Inputs, the sandbox image, and what happens to the patch: [knowledge-sync](https://gitlab.com/redhat/rhel-ai/agentic-ci/knowledge-sync)
- Marketplace skills path: `opendatahub-io/skills-registry` `.claude-plugin/marketplace.json`
