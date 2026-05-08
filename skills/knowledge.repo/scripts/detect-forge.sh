#!/usr/bin/env bash
set -euo pipefail

remote_url=$(git remote get-url origin 2>/dev/null) || {
    echo "ERROR: no 'origin' remote found" >&2
    exit 1
}

case "$remote_url" in
    *github.com*)  forge="github" ;;
    *gitlab*)      forge="gitlab" ;;
    *)
        echo "ERROR: unrecognized forge in remote URL: $remote_url" >&2
        exit 1
        ;;
esac

# Strip protocol/host prefix and .git suffix to get owner/repo slug
slug=$(echo "$remote_url" | sed -E 's#^(https?://[^/]+/|git@[^:]+:)##' | sed 's/\.git$//')

echo "$forge"
echo "$slug"
