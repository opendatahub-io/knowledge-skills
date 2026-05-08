---
name: knowledge.repo
description: Scan merged PRs and propose updates to AI context files (CLAUDE.md, AGENTS.md) as a git-apply-able patch. Non-interactive.
user-invocable: true
allowed-tools: Bash, Read, Write, Agent, Glob
---

# knowledge.repo

Scan merged PRs from the last N days, extract knowledge relevant to AI agent
context, and propose updates to context files as a `git apply`-able patch.

## Arguments

Parse `$ARGUMENTS` for:
- `--days N` (default: 7) — how far back to scan merged PRs

## Pipeline

Execute these phases in order. Exit early where indicated.

### Phase 1: Setup

1. Run `bash $SKILL_DIR/scripts/detect-forge.sh` and capture the output.
   - Line 1 is the forge type (`github` or `gitlab`)
   - Line 2 is the owner/repo slug
   - If it fails, print the error and STOP.

2. Create the artifacts directory structure:
   ```bash
   mkdir -p artifacts/pr-data artifacts/pr-extractions
   ```

3. Run `bash $SKILL_DIR/scripts/list-context-files.sh artifacts/context-file-list.txt`
   - If exit code is non-zero (no context files found), write this run report
     and STOP:
     ```bash
     echo '{"early_exit":"no_context_files","prs_scanned":0}' > artifacts/run-report.json
     ```

### Phase 2: Fetch

1. Run:
   ```bash
   python3 $SKILL_DIR/scripts/fetch-prs.py --forge {forge} --repo {slug} --days {days}
   ```

2. Count the fetched PR files:
   ```bash
   ls artifacts/pr-data/*.json 2>/dev/null | wc -l
   ```
   If zero, write this run report and STOP:
   ```bash
   echo '{"early_exit":"no_prs","prs_scanned":0}' > artifacts/run-report.json
   ```

### Phase 3: Extract

For each `.json` file in `artifacts/pr-data/`:

1. Extract the PR ID from the filename (e.g., `123.json` → `123`).
2. Read the file `$SKILL_DIR/prompts/extract-agent.md`.
3. In the prompt text, replace every `{ID}` with the actual PR ID.
4. Dispatch a **background** Agent with the constructed prompt.

Dispatch in waves of up to 10 agents. After dispatching a wave:
- Poll every 30 seconds for the expected extraction files
  (`artifacts/pr-extractions/{id}.md`)
- Timeout after 5 minutes per wave
- Log any timed-out PR IDs and continue to the next wave

After all waves complete, check if any extraction file contains knowledge items.
Read each `artifacts/pr-extractions/*.md` file and look for content under the
`## Knowledge Items` heading beyond just the heading itself.

If NO extraction file contains any knowledge items, write this run report and STOP:
```bash
echo '{"early_exit":"no_knowledge","prs_scanned":N,"prs_with_knowledge":0}' > artifacts/run-report.json
```
(Replace N with the actual count of PR data files.)

### Phase 4: Synthesize

1. Read `$SKILL_DIR/prompts/synthesize-agent.md`.
2. Dispatch a **foreground** Agent with the prompt.
3. After the agent completes, check for changes:
   ```bash
   git diff --stat
   ```
   If the diff is empty (no tracked files were modified), write this run report
   and STOP:
   ```bash
   echo '{"early_exit":"no_changes","prs_scanned":N,"prs_with_knowledge":M,"changes_proposed":0}' > artifacts/run-report.json
   ```

4. Save the diff for the review agent:
   ```bash
   git diff > artifacts/proposed-diff.txt
   ```

### Phase 5: Review

1. Read `$SKILL_DIR/prompts/review-agent.md`.
2. Dispatch a **foreground** Agent with the prompt.
3. After the agent completes, read `artifacts/review.md` and parse the `verdict`
   from the YAML frontmatter.

### Phase 6: Revise (conditional)

If the review verdict is **PASS**, skip this phase entirely.

If the verdict is **REVISE**:
1. Read `$SKILL_DIR/prompts/revise-agent.md`.
2. Dispatch a **foreground** Agent with the prompt.

### Phase 7: Artifacts

1. Capture the final patch:
   ```bash
   git diff > artifacts/proposed-updates.patch
   ```

2. Reset the working tree:
   ```bash
   git checkout -- .
   ```

3. Write `artifacts/run-report.json` with these fields:
   - `forge`: the detected forge type
   - `repo`: the owner/repo slug
   - `date_range`: `{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}`
   - `prs_scanned`: count of files in `artifacts/pr-data/`
   - `prs_with_knowledge`: count of extraction files with non-empty knowledge items
   - `knowledge_items`: `{"high": N, "medium": N, "low": N}` counts from extractions
   - `changes_proposed`: count of changes listed in `artifacts/changes-summary.md`
   - `review_verdict`: the verdict from `artifacts/review.md`
   - `patch_file`: `"artifacts/proposed-updates.patch"`

   Build these counts by reading the extraction and summary files.

4. Print: `"Knowledge sync complete. Artifacts written to artifacts/"`
