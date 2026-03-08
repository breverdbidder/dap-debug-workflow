#!/usr/bin/env python3
"""
Phase 3: Push code fixes to GitHub repos via API.

Reads fixed files from a local directory and pushes them to the
target repo on GitHub with descriptive commit messages.

Usage:
  python3 scripts/push_fixes.py --repo zonewise-scraper-v4 --files src/utils/supabase_writer.py
  python3 scripts/push_fixes.py --repo zonewise-scraper-v4 --dir /path/to/fixed/repo
"""

import json
import base64
import urllib.request
import urllib.error
import os
import sys
import argparse
import time


TOKEN = os.getenv("GITHUB_TOKEN", "")
ORG = "breverdbidder"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}


def github_api(method, url, data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers=HEADERS,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()[:200]}


def push_file(repo, filepath, local_path, message):
    """Push a local file to a GitHub repo."""
    url = f"https://api.github.com/repos/{ORG}/{repo}/contents/{filepath}"

    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    # Get current SHA
    existing = github_api("GET", url)
    sha = existing.get("sha")

    payload = {"message": message, "content": content}
    if sha:
        payload["sha"] = sha

    result = github_api("PUT", url, payload)

    if "content" in result or "commit" in result:
        action = "Updated" if sha else "Created"
        print(f"  ✅ {action}: {filepath}")
        return True
    else:
        print(f"  ❌ Failed: {filepath} — {result.get('message', '')[:80]}")
        return False


def push_fixes(repo, files=None, local_dir=None, message_prefix="fix"):
    """Push one or more fixed files to a GitHub repo."""
    print(f"\n{'=' * 60}")
    print(f"PUSHING FIXES TO {ORG}/{repo}")
    print(f"{'=' * 60}\n")

    success = 0
    failed = 0

    if files and local_dir:
        for filepath in files:
            local_path = os.path.join(local_dir, filepath)
            if not os.path.exists(local_path):
                print(f"  ⏭️  Skipping {filepath} — not found locally")
                continue

            message = f"{message_prefix}: update {os.path.basename(filepath)}\n\nDiagnosed with dap debugger."
            if push_file(repo, filepath, local_path, message):
                success += 1
            else:
                failed += 1
            time.sleep(0.5)

    elif local_dir:
        # Push all modified Python files
        for root, dirs, filenames in os.walk(local_dir):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
            for fname in filenames:
                if fname.endswith('.py'):
                    local_path = os.path.join(root, fname)
                    filepath = os.path.relpath(local_path, local_dir)
                    message = f"{message_prefix}: update {fname}\n\nDiagnosed with dap debugger."
                    if push_file(repo, filepath, local_path, message):
                        success += 1
                    else:
                        failed += 1
                    time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"Results: {success} pushed, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push code fixes to GitHub")
    parser.add_argument("--repo", required=True, help="Target GitHub repo")
    parser.add_argument("--files", nargs="+", help="Specific files to push")
    parser.add_argument("--dir", help="Local directory with fixed files")
    parser.add_argument("--message", default="fix", help="Commit message prefix")
    args = parser.parse_args()

    push_fixes(args.repo, files=args.files, local_dir=args.dir, message_prefix=args.message)
