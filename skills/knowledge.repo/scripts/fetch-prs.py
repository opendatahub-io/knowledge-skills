#!/usr/bin/env python3
"""Fetch merged PR/MR data from GitHub or GitLab using gh/glab CLI."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

MAX_DIFF_LINES = 5000


def run(cmd, check=True):
    """Run a shell command and return stdout. Returns empty string on failure if check=False."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    if not check and result.returncode != 0:
        return ""
    return result.stdout.strip()


def truncate_diff(diff):
    """Truncate diff to MAX_DIFF_LINES, return (diff, was_truncated)."""
    lines = diff.split("\n")
    if len(lines) > MAX_DIFF_LINES:
        return "\n".join(lines[:MAX_DIFF_LINES]), True
    return diff, False


def fetch_github_prs(slug, since_date, output_dir):
    """Fetch merged PRs from GitHub using gh CLI."""
    raw = run([
        "gh", "pr", "list", "-R", slug,
        "-s", "merged",
        "--search", f"merged:>={since_date}",
        "--json", "number,title,author,mergedAt,body,labels,files",
        "-L", "100",
    ])
    if not raw:
        return 0

    prs = json.loads(raw)

    for pr in prs:
        pr_id = pr["number"]
        print(f"  Fetching PR #{pr_id}: {pr['title']}")

        diff_raw = run(["gh", "pr", "diff", str(pr_id), "-R", slug], check=False)
        diff, diff_truncated = truncate_diff(diff_raw)

        comments_raw = run([
            "gh", "api", f"repos/{slug}/pulls/{pr_id}/comments",
            "--paginate",
        ], check=False)
        review_comments = []
        if comments_raw:
            for c in json.loads(comments_raw):
                review_comments.append({
                    "author": c.get("user", {}).get("login", ""),
                    "body": c.get("body", ""),
                    "path": c.get("path", ""),
                    "line": c.get("line"),
                })

        reviews_raw = run([
            "gh", "api", f"repos/{slug}/pulls/{pr_id}/reviews",
            "--paginate",
        ], check=False)
        review_threads = []
        if reviews_raw:
            for r in json.loads(reviews_raw):
                if r.get("body"):
                    review_threads.append({
                        "state": r.get("state", ""),
                        "comments": [r["body"]],
                    })

        commits_raw = run([
            "gh", "api", f"repos/{slug}/pulls/{pr_id}/commits",
            "--paginate",
        ], check=False)
        commits = []
        if commits_raw:
            for c in json.loads(commits_raw):
                commits.append({
                    "hash": c["sha"][:7],
                    "message": c["commit"]["message"],
                })

        checks_raw = run([
            "gh", "pr", "checks", str(pr_id), "-R", slug,
            "--json", "name,conclusion",
        ], check=False)
        ci_status = "unknown"
        ci_failed_jobs = []
        if checks_raw:
            checks = json.loads(checks_raw)
            failed = [c for c in checks if c.get("conclusion") == "FAILURE"]
            ci_status = "failed" if failed else "passed"
            ci_failed_jobs = [{"name": c["name"]} for c in failed]

        pr_data = {
            "id": pr_id,
            "title": pr["title"],
            "author": pr["author"]["login"],
            "url": f"https://github.com/{slug}/pull/{pr_id}",
            "merged_at": pr["mergedAt"],
            "description": pr.get("body", "") or "",
            "labels": [l["name"] for l in pr.get("labels", [])],
            "files_changed": [f["path"] for f in pr.get("files", [])],
            "commits": commits,
            "diff": diff,
            "diff_truncated": diff_truncated,
            "review_comments": review_comments,
            "review_threads": review_threads,
            "ci_status": ci_status,
            "ci_failed_jobs": ci_failed_jobs,
        }

        output_path = os.path.join(output_dir, f"{pr_id}.json")
        with open(output_path, "w") as f:
            json.dump(pr_data, f, indent=2)

    return len(prs)


def fetch_gitlab_prs(slug, since_date, output_dir):
    """Fetch merged MRs from GitLab using glab CLI."""
    project_path = slug.replace("/", "%2F")

    raw = run([
        "glab", "api", f"projects/{project_path}/merge_requests",
        "-X", "GET",
        "-f", "state=merged",
        "-f", f"updated_after={since_date}T00:00:00Z",
        "-f", "per_page=100",
    ], check=False)
    if not raw:
        return 0

    mrs = json.loads(raw)
    # Filter to only MRs actually merged after since_date
    mrs = [m for m in mrs if (m.get("merged_at") or "") >= since_date]

    for mr in mrs:
        mr_id = mr["iid"]
        print(f"  Fetching MR !{mr_id}: {mr['title']}")

        diff_raw = run(["glab", "mr", "diff", str(mr_id), "-R", slug], check=False)
        diff, diff_truncated = truncate_diff(diff_raw)

        files_changed = []
        for line in diff.split("\n"):
            if line.startswith("+++ b/"):
                path = line[6:]
                if path not in files_changed:
                    files_changed.append(path)

        notes_raw = run([
            "glab", "api",
            f"projects/{project_path}/merge_requests/{mr_id}/notes",
            "-f", "per_page=100",
        ], check=False)
        review_comments = []
        if notes_raw:
            for n in json.loads(notes_raw):
                if n.get("system"):
                    continue
                review_comments.append({
                    "author": n.get("author", {}).get("username", ""),
                    "body": n.get("body", ""),
                    "path": "",
                    "line": None,
                })

        pipelines_raw = run([
            "glab", "api",
            f"projects/{project_path}/merge_requests/{mr_id}/pipelines",
        ], check=False)
        ci_status = "unknown"
        ci_failed_jobs = []
        if pipelines_raw:
            pipelines = json.loads(pipelines_raw)
            if pipelines:
                latest = pipelines[0]
                ci_status = "passed" if latest.get("status") == "success" else "failed"
                if ci_status == "failed":
                    jobs_raw = run([
                        "glab", "api",
                        f"projects/{project_path}/pipelines/{latest['id']}/jobs",
                    ], check=False)
                    if jobs_raw:
                        for j in json.loads(jobs_raw):
                            if j.get("status") == "failed":
                                ci_failed_jobs.append({"name": j["name"]})

        commits_raw = run([
            "glab", "api",
            f"projects/{project_path}/merge_requests/{mr_id}/commits",
        ], check=False)
        commits = []
        if commits_raw:
            for c in json.loads(commits_raw):
                commits.append({
                    "hash": c["id"][:7],
                    "message": c["message"],
                })

        pr_data = {
            "id": mr_id,
            "title": mr["title"],
            "author": mr.get("author", {}).get("username", ""),
            "url": mr.get("web_url", ""),
            "merged_at": mr.get("merged_at", ""),
            "description": mr.get("description", "") or "",
            "labels": mr.get("labels", []),
            "files_changed": files_changed,
            "commits": commits,
            "diff": diff,
            "diff_truncated": diff_truncated,
            "review_comments": review_comments,
            "review_threads": [],
            "ci_status": ci_status,
            "ci_failed_jobs": ci_failed_jobs,
        }

        output_path = os.path.join(output_dir, f"{mr_id}.json")
        with open(output_path, "w") as f:
            json.dump(pr_data, f, indent=2)

    return len(mrs)


def main():
    parser = argparse.ArgumentParser(description="Fetch merged PR/MR data")
    parser.add_argument("--forge", required=True, choices=["github", "gitlab"])
    parser.add_argument("--repo", required=True, help="owner/repo slug")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output-dir", default="artifacts/pr-data")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
    print(f"Fetching merged PRs since {since} from {args.forge}:{args.repo}")

    if args.forge == "github":
        count = fetch_github_prs(args.repo, since, args.output_dir)
    else:
        count = fetch_gitlab_prs(args.repo, since, args.output_dir)

    print(f"Fetched {count} PR(s) to {args.output_dir}/")


if __name__ == "__main__":
    main()
