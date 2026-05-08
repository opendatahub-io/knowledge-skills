# knowledge-skills

## Project Structure

This repo hosts Claude Code skills in the `knowledge.*` namespace. Currently contains one skill:

- `skills/knowledge.repo/` -- scans merged PRs and proposes context file updates

The skill is a Claude Code plugin skill (SKILL.md + agent prompts + helper scripts). It does NOT run from this repo -- it runs in target repos that have context files (CLAUDE.md, AGENTS.md).

## Architecture

### Separation of concerns

- **SKILL.md** is a thin orchestrator. It runs scripts and dispatches agents but contains no domain logic.
- **Helper scripts** (`scripts/`) handle deterministic work: forge detection, PR data fetching, context file discovery. These are bash/Python and call `gh`/`glab` CLI tools.
- **Agent prompts** (`prompts/`) handle judgment calls: knowledge extraction, synthesis, review, revision. Each gets its own isolated agent context.

### Adversarial review pattern

The review agent is context-isolated from the synthesis agent. It receives the diff and raw PR extractions but NOT the changes-summary.md (the synthesis agent's rationale). This prevents the reviewer from being biased by the author's reasoning. The review-agent.md prompt explicitly instructs the agent not to read changes-summary.md.

### Artifact-based output

The skill produces files in `artifacts/` and never creates PRs/MRs itself. External tooling applies the patch and handles forge interactions. This keeps the skill's boundary clean -- it does analysis and proposal, not mechanical git/forge operations.

### Stateless by design

Each run is independent. No tracking of prior runs, no exclusion lists, no learning from rejected proposals. This keeps the implementation simple and avoids the complexity trap of building feedback loops before validating the basic forward path.

If the skill repeatedly proposes changes that reviewers reject, the right fix is to add explicit guidance to the target repo's context files (e.g., "do not document X" or "this pattern is intentional, do not suggest changing it"). The context files themselves become the exclusion mechanism -- no separate state needed.

## Design Decisions

### Forge-agnostic via CLI tools

Uses `gh` for GitHub and `glab` for GitLab, detected from the `origin` remote URL. The PR data schema is normalized so downstream agents don't need to know which forge produced it. Always use CLI tools over raw API calls.

### Per-PR extraction agents (not batch)

Each PR gets its own agent context for extraction. This avoids context overflow from many PRs and allows parallel processing (dispatched in waves of 10). The synthesis agent then sees only compact extractions, not raw PR data.

### Diff truncation

Diffs exceeding 5000 lines are truncated by `fetch-prs.py` with a `diff_truncated: true` flag. The extract agent is instructed to note this limitation in its output.

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
