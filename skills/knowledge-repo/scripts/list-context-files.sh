#!/usr/bin/env bash
set -euo pipefail

output_file="${1:-artifacts/context-file-list.txt}"
mkdir -p "$(dirname "$output_file")"
true > "$output_file"

# AI context files
for f in CLAUDE.md AGENTS.md .claude/CLAUDE.md; do
    [ -f "$f" ] && echo "$f" >> "$output_file"
done

# Skill files: plugin skills (skills/*/SKILL.md and their prompts)
if [ -d "skills" ]; then
    find skills -maxdepth 2 -name 'SKILL.md' -type f -print >> "$output_file"
    find skills -path '*/prompts/*.md' -type f -print >> "$output_file"
fi

# Skill files: local skills (.claude/skills/*.md)
if [ -d ".claude/skills" ]; then
    find .claude/skills -maxdepth 1 -name '*.md' -type f -print >> "$output_file"
fi

count=$(wc -l < "$output_file" | tr -d ' ')
if [ "$count" -eq 0 ]; then
    echo "No context files found" >&2
    exit 1
fi

echo "Found $count context file(s):"
cat "$output_file"
