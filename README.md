# knowledge-skills

Claude Code skills for autonomous knowledge management across repositories.

## knowledge.repo

A skill that scans merged PRs from the last N days, extracts knowledge relevant to AI agent context, and proposes updates to context files (CLAUDE.md, AGENTS.md) as a `git apply`-able patch.

### How it works

The skill runs a linear pipeline with 7 phases:

1. **Setup** -- detects whether the repo is on GitHub or GitLab, identifies which context files exist
2. **Fetch** -- calls `gh`/`glab` CLI to collect merged PR data (diffs, descriptions, review comments, CI results)
3. **Extract** -- dispatches one agent per PR (in parallel) to summarize what knowledge each PR contains
4. **Synthesize** -- a single agent reads all extractions plus the current context files, then edits the context files with proposed updates
5. **Review** -- a separate agent critiques the proposed changes for accuracy, relevance, and redundancy (adversarial review -- this agent does not see the synthesis agent's rationale)
6. **Revise** -- if the reviewer found issues, a revision agent fixes them
7. **Artifacts** -- captures the final changes as a `git diff` patch, writes a run report, and resets the working tree

The skill produces artifacts in `artifacts/` -- external tooling applies the patch, creates a branch, and opens a PR/MR for human review.

### Pipeline diagram

```
SETUP --> FETCH --> EXTRACT --> SYNTHESIZE --> REVIEW --> REVISE --> ARTIFACTS
            |         |            |             |          |
         scripts    agents       agent         agent      agent
                   (per-PR)    (one pass)    (one pass)  (one pass)
```

### Artifacts produced

| File | Description |
|------|-------------|
| `artifacts/pr-data/{id}.json` | Raw PR data fetched from the forge |
| `artifacts/pr-extractions/{id}.md` | Per-PR knowledge extraction with categories and evidence |
| `artifacts/proposed-updates.patch` | `git apply`-able patch with the proposed context file changes |
| `artifacts/changes-summary.md` | Human-readable rationale for each change (becomes the PR description) |
| `artifacts/review.md` | Reviewer findings and verdict |
| `artifacts/run-report.json` | Machine-readable run metadata (counts, date range, verdict) |

### Usage

The skill is designed to run autonomously in a CI pipeline on a schedule. It accepts a `--days N` argument (default: 7) to control how far back to scan.

The skill is forge-agnostic -- it detects GitHub or GitLab from the `origin` remote and uses the appropriate CLI (`gh` or `glab`).

### Stateless

Each run is independent -- the skill has no memory of prior runs. If it repeatedly proposes unwanted changes, add explicit guidance to the target repo's context files (e.g., "do not document X"). The context files themselves serve as the exclusion mechanism.

### Early exits

The pipeline exits early (with a run report) when:
- No context files (CLAUDE.md, AGENTS.md) exist in the repo
- No merged PRs in the time window
- No extractable knowledge found in any PR
- The synthesis agent decided no context updates are warranted
