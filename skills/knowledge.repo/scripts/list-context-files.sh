#!/usr/bin/env bash
set -euo pipefail

output_file="${1:-artifacts/context-file-list.txt}"
mkdir -p "$(dirname "$output_file")"
> "$output_file"

for f in CLAUDE.md AGENTS.md .claude/CLAUDE.md; do
    [ -f "$f" ] && echo "$f" >> "$output_file"
done

count=$(wc -l < "$output_file" | tr -d ' ')
if [ "$count" -eq 0 ]; then
    echo "No context files found" >&2
    exit 1
fi

echo "Found $count context file(s):"
cat "$output_file"
