#!/usr/bin/env python3
"""
Phase 1: Deploy debug-skill to all breverdbidder GitHub repos.

Deploys 3 layers:
  Layer 1: skills/debugging-code/SKILL.md (DAP skill file)
  Layer 2: CLAUDE.md debug section (appended or created)
  Layer 3: scripts/install-debug-tools.sh (auto-installer)

Usage:
  python3 scripts/deploy_skill.py
  python3 scripts/deploy_skill.py --repos zonewise-scraper-v4 biddeed-ai-ui
  python3 scripts/deploy_skill.py --dry-run
"""

import json
import base64
import urllib.request
import urllib.error
import time
import argparse
import os
import sys

TOKEN = os.getenv("GITHUB_TOKEN", "")
ORG = "breverdbidder"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

SKILL_MD_URL = "https://api.github.com/repos/AlmogBaku/debug-skill/contents/skills/debugging-code/SKILL.md"

DEBUG_SECTION = """

## Debugging with DAP

**ALWAYS use `dap` instead of print-statement debugging.** The `dap` CLI wraps the Debug Adapter Protocol for surgical debugging.

### Setup (auto-install if missing)
```bash
which dap || curl -fsSL https://raw.githubusercontent.com/AlmogBaku/debug-skill/master/install.sh | bash
```

### When to use
- Program crashes or raises unexpected exceptions
- Wrong output and root cause isn't obvious from stack trace
- Data flows through multiple functions/files (pipeline bugs)
- Print-debugging would require 3+ iterations

### Quick reference
```bash
dap debug script.py --break script.py:42     # breakpoint at line 42
dap debug script.py --break-on-exception raised  # catch all exceptions
dap eval "len(items)"                         # inspect live state
dap step                                      # step over
dap step in                                   # step into function
dap step out                                  # return to caller
dap continue                                  # next breakpoint
dap stop                                      # end session
```

### Debugging mindset
1. Form hypothesis: "I believe the bug is in X because Y"
2. Set breakpoint upstream of where error manifests
3. Inspect locals and call stack at each stop
4. Confirm or refute hypothesis, adjust breakpoint
5. Fix only after understanding root cause

Full skill docs: `skills/debugging-code/SKILL.md`
"""

INSTALL_HOOK = """#!/bin/bash
# Auto-install dap debugger if not present
if ! command -v dap &> /dev/null; then
    echo "Installing dap debugger..."
    curl -fsSL https://raw.githubusercontent.com/AlmogBaku/debug-skill/master/install.sh | bash
fi
"""


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


def get_file(repo, path):
    result = github_api("GET", f"https://api.github.com/repos/{ORG}/{repo}/contents/{path}")
    if "content" in result:
        return base64.b64decode(result["content"]).decode(), result["sha"]
    return None, None


def put_file(repo, path, content, message, sha=None):
    payload = {"message": message, "content": base64.b64encode(content.encode()).decode()}
    if sha:
        payload["sha"] = sha
    return github_api("PUT", f"https://api.github.com/repos/{ORG}/{repo}/contents/{path}", payload)


def fetch_skill_md():
    """Fetch latest SKILL.md from AlmogBaku/debug-skill."""
    result = github_api("GET", SKILL_MD_URL)
    if "content" in result:
        return base64.b64decode(result["content"]).decode()
    # Fallback: use local copy
    skill_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills/debugging-code/SKILL.md")
    if os.path.exists(skill_path):
        with open(skill_path) as f:
            return f.read()
    raise RuntimeError("Cannot fetch SKILL.md from GitHub or local fallback")


def get_all_repos():
    """List all non-archived repos with debuggable languages."""
    repos = []
    page = 1
    while True:
        result = github_api("GET", f"https://api.github.com/users/{ORG}/repos?per_page=100&page={page}&sort=updated")
        if not result or isinstance(result, dict):
            break
        for r in result:
            lang = r.get("language")
            if lang in {"Python", "TypeScript", "JavaScript"} and not r["archived"]:
                repos.append(r["name"])
        if len(result) < 100:
            break
        page += 1
    return repos


def deploy(repos=None, dry_run=False):
    skill_md = fetch_skill_md()
    if repos is None:
        repos = get_all_repos()

    results = {"layer1": [], "layer2": [], "layer3": [], "skipped": [], "failed": []}

    print(f"\n{'=' * 60}")
    print(f"DAP DEBUG SKILL DEPLOYMENT")
    print(f"Repos: {len(repos)} | Dry run: {dry_run}")
    print(f"{'=' * 60}\n")

    for repo in repos:
        print(f"\n--- {repo} ---")

        # Layer 1: SKILL.md
        content, sha = get_file(repo, "skills/debugging-code/SKILL.md")
        if content and content.strip() == skill_md.strip():
            print(f"  L1 SKIP: SKILL.md already current")
        elif not dry_run:
            result = put_file(repo, "skills/debugging-code/SKILL.md", skill_md,
                            "Deploy debug-skill SKILL.md from AlmogBaku/debug-skill", sha)
            if "content" in result or "commit" in result:
                print(f"  L1 ✅: SKILL.md deployed")
                results["layer1"].append(repo)
            else:
                print(f"  L1 ❌: {result.get('message', '')[:80]}")
                results["failed"].append(f"{repo}/SKILL.md")
        else:
            print(f"  L1 DRY: Would deploy SKILL.md")

        time.sleep(0.3)

        # Layer 2: CLAUDE.md debug section
        content, sha = get_file(repo, "CLAUDE.md")
        if content and ("dap debug" in content):
            print(f"  L2 SKIP: CLAUDE.md already has DAP section")
        elif not dry_run:
            if content:
                new_content = content.rstrip() + "\n" + DEBUG_SECTION
                msg = "Append DAP debugging instructions to CLAUDE.md"
            else:
                new_content = f"# {repo} — Claude Code Directive\n\n## Zero Human-in-the-Loop\nAll operations PRE-APPROVED.\n" + DEBUG_SECTION
                msg = "Create CLAUDE.md with DAP debugging instructions"
            result = put_file(repo, "CLAUDE.md", new_content, msg, sha)
            if "content" in result or "commit" in result:
                print(f"  L2 ✅: CLAUDE.md {'updated' if content else 'created'}")
                results["layer2"].append(repo)
            else:
                print(f"  L2 ❌: {result.get('message', '')[:80]}")
                results["failed"].append(f"{repo}/CLAUDE.md")
        else:
            print(f"  L2 DRY: Would {'append to' if content else 'create'} CLAUDE.md")

        time.sleep(0.3)

        # Layer 3: auto-install hook (top repos only)
        content, sha = get_file(repo, "scripts/install-debug-tools.sh")
        if content and "dap" in content:
            print(f"  L3 SKIP: install hook already exists")
        elif not dry_run:
            result = put_file(repo, "scripts/install-debug-tools.sh", INSTALL_HOOK,
                            "Add dap auto-install script", sha)
            if "content" in result or "commit" in result:
                print(f"  L3 ✅: auto-install hook deployed")
                results["layer3"].append(repo)
            else:
                print(f"  L3 ❌: {result.get('message', '')[:80]}")
        else:
            print(f"  L3 DRY: Would deploy install hook")

        time.sleep(0.3)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"DEPLOYMENT SUMMARY")
    print(f"{'=' * 60}")
    print(f"Layer 1 (SKILL.md):     {len(results['layer1'])} repos")
    print(f"Layer 2 (CLAUDE.md):    {len(results['layer2'])} repos")
    print(f"Layer 3 (auto-install): {len(results['layer3'])} repos")
    if results["failed"]:
        print(f"Failed: {len(results['failed'])}")
        for f in results["failed"]:
            print(f"  ❌ {f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy debug-skill to GitHub repos")
    parser.add_argument("--repos", nargs="+", help="Specific repos to deploy to")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed")
    args = parser.parse_args()
    deploy(repos=args.repos, dry_run=args.dry_run)
