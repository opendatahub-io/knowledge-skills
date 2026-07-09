# knowledge-skills

Claude Code skills for autonomous knowledge management across repositories.

## knowledge-repo

A skill that processes pre-fetched PR/MR data, extracts knowledge relevant to AI agent context, and proposes updates to context files (CLAUDE.md, AGENTS.md) and skill files (SKILL.md, prompts) as a `git apply`-able patch.

### How it works

The skill runs a linear pipeline with 7 phases:

1. **Setup** -- reads `artifacts/repo-context.json` (forge type and repo slug, provided by the CI runner), discovers which context and skill files exist
2. **Verify PR Data** -- checks that the CI runner has placed PR data files in `artifacts/pr-data/`
3. **Extract** -- dispatches one agent per PR (in parallel waves of 10, using sonnet) to identify what knowledge each PR contains
4. **Synthesize** -- a single agent (opus) reads all extractions plus the current context and skill files, then edits them with proposed updates
5. **Review** -- a separate agent (opus) critiques the proposed changes for accuracy, relevance, and redundancy (adversarial review -- this agent does not see the synthesis agent's rationale)
6. **Revise** -- if the reviewer found issues, a revision agent (opus) fixes them in a single pass
7. **Artifacts** -- captures the final changes as a `git diff` patch, writes a run report, and resets the working tree

The skill produces artifacts in `artifacts/` -- external tooling applies the patch, creates a branch, and opens a PR/MR for human review.

### Pipeline diagram

```
SETUP --> VERIFY --> EXTRACT --> SYNTHESIZE --> REVIEW --> REVISE --> ARTIFACTS
            |          |            |             |          |
         check PR    agents       agent         agent      agent
          data      (per-PR,    (one pass,    (one pass,  (one pass,
                     sonnet)      opus)         opus)       opus)
```

### CI runner contract

The skill does not fetch PR data or detect the forge type itself. It expects a CI runner to prepare these inputs before invocation:

| Input | Description |
|-------|-------------|
| `artifacts/repo-context.json` | JSON with `forge` (github/gitlab) and `slug` (owner/repo) |
| `artifacts/pr-data/{id}.json` | One file per merged PR, containing diff, description, commit messages, and review comments |

The [knowledge-sync](https://gitlab.com/redhat/rhel-ai/agentic-ci/knowledge-sync) project is the reference CI runner. It handles repo cloning, PR fetching via GitHub/GitLab REST APIs, forge detection, and -- after the skill runs -- branch creation, patch application, and PR/MR submission.

### Artifacts produced

| File | Description |
|------|-------------|
| `artifacts/pr-extractions/{id}.md` | Per-PR knowledge extraction with categories and evidence |
| `artifacts/proposed-updates.patch` | `git apply`-able patch with the proposed context and skill file changes |
| `artifacts/changes-summary.md` | Human-readable rationale for each change (becomes the PR description) |
| `artifacts/review.md` | Reviewer findings and verdict |
| `artifacts/run-report.json` | Machine-readable run metadata (counts, date range, verdict) |

### Usage

The skill is designed to run autonomously in a CI pipeline on a schedule. It accepts a `--days N` argument (default: 7) to control how far back to scan.

The skill is forge-agnostic -- it reads the forge type from `artifacts/repo-context.json` and the normalized PR data schema means downstream agents don't need to know which forge produced it.

### Stateless

Each run is independent -- the skill has no memory of prior runs. If it repeatedly proposes unwanted changes, add explicit guidance to the target repo's context files (e.g., "do not document X"). The context files themselves serve as the exclusion mechanism.

### Early exits

The pipeline exits early (with a run report) when:
- No context files (CLAUDE.md, AGENTS.md) or skill files exist in the repo
- No merged PRs in the time window
- No extractable knowledge found in any PR
- The synthesis agent decided no context updates are warranted
