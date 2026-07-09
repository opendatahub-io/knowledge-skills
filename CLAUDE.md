# knowledge-skills

## Project Structure

This repo hosts Claude Code skills in the `knowledge.*` namespace. Currently contains one skill:

- `skills/knowledge-repo/` -- scans merged PRs and proposes context and skill file updates

The skill is a Claude Code plugin skill (SKILL.md + agent prompts + helper scripts). It does NOT run from this repo -- it runs in target repos that have context files (CLAUDE.md, AGENTS.md) or skill files (SKILL.md, prompt files).

## Architecture

### Separation of concerns

- **SKILL.md** is a thin orchestrator. It runs scripts and dispatches agents but contains no domain logic.
- **Helper scripts** (`scripts/`) handle deterministic work: context and skill file discovery. Currently contains `list-context-files.sh`.
- **Agent prompts** (`prompts/`) handle judgment calls: knowledge extraction, synthesis, review, revision. Each gets its own isolated agent context.
- **CI runner** (external, e.g. [knowledge-sync](https://gitlab.com/redhat/rhel-ai/agentic-ci/knowledge-sync)) handles forge detection, PR data fetching, repo cloning, and post-run patch application/PR creation.

### Adversarial review pattern

The review agent is context-isolated from the synthesis agent. It receives the diff and raw PR extractions but NOT the changes-summary.md (the synthesis agent's rationale). This prevents the reviewer from being biased by the author's reasoning. The review-agent.md prompt explicitly instructs the agent not to read changes-summary.md.

### Artifact-based output

The skill produces files in `artifacts/` and never creates PRs/MRs itself. External tooling applies the patch and handles forge interactions. This keeps the skill's boundary clean -- it does analysis and proposal, not mechanical git/forge operations.

### Stateless by design

Each run is independent. No tracking of prior runs, no exclusion lists, no learning from rejected proposals. This keeps the implementation simple and avoids the complexity trap of building feedback loops before validating the basic forward path.

If the skill repeatedly proposes changes that reviewers reject, the right fix is to add explicit guidance to the target repo's context files (e.g., "do not document X" or "this pattern is intentional, do not suggest changing it"). The context files themselves become the exclusion mechanism -- no separate state needed.

## Design Decisions

### Forge-agnostic via normalized inputs

The skill reads forge type from `artifacts/repo-context.json` (provided by the CI runner). PR data is pre-fetched and normalized by the CI runner so downstream agents don't need to know which forge produced it. The skill itself does not call `gh`/`glab` or any forge API.

### CI runner contract

The skill expects the CI runner to prepare:
- `artifacts/repo-context.json` with `forge` and `slug` fields
- `artifacts/pr-data/{id}.json` with one file per merged PR (diff, description, commit messages, review comments)

The reference CI runner is [knowledge-sync](https://gitlab.com/redhat/rhel-ai/agentic-ci/knowledge-sync), which handles GitHub/GitLab API calls, diff truncation, and post-run forge operations (branch creation, patch application, PR/MR submission).

### Per-PR extraction agents (not batch)

Each PR gets its own agent context for extraction. This avoids context overflow from many PRs and allows parallel processing (dispatched in waves of 10). The synthesis agent then sees only compact extractions, not raw PR data.

### Model selection

Extract agents use sonnet (mechanical per-PR data extraction). Synthesize, review, and revise agents use opus (judgment, cross-PR reasoning, style matching).

### Single revision pass

The revise agent gets one pass. No re-review loop. The human reviewer on the resulting PR/MR is the final quality gate.

### CI environment assumptions

The skill runs in disposable CI environments. The working tree may be left dirty if the pipeline is killed mid-run -- this is acceptable because the environment is discarded.

## Conventions

- Scripts use `$SKILL_DIR` to reference files relative to the skill directory
- Agent prompts use `{ID}` as a placeholder that the SKILL.md replaces at dispatch time
- All agent prompts include a security directive about untrusted PR content
- All agent prompts end with a terminal instruction ("Your work is complete when...")
- Artifacts are written to `artifacts/` in the target repo's working directory
