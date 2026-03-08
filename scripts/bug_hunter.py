#!/usr/bin/env python3
"""
Phase 2: Bug Hunter — Static analysis + pattern detection.

Scans a cloned repo for common bug patterns:
  - INSERT vs UPSERT mismatches (duplicate data risk)
  - Field extraction vs storage gaps (data loss)
  - Circuit breaker coverage gaps
  - Untested fallback code paths
  - Missing error handling in async chains

Usage:
  python3 scripts/bug_hunter.py --repo zonewise-scraper-v4
  python3 scripts/bug_hunter.py --path /path/to/local/repo
"""

import os
import re
import sys
import json
import argparse
import urllib.request
import base64

TOKEN = os.getenv("GITHUB_TOKEN", "")
ORG = "breverdbidder"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


class BugHunter:
    """Static analysis bug detector for Python codebases."""

    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.bugs = []
        self.warnings = []

    def scan_all(self):
        """Run all bug detection patterns."""
        py_files = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv'}]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))

        print(f"\nScanning {len(py_files)} Python files in {self.repo_path}\n")

        for filepath in py_files:
            with open(filepath) as f:
                try:
                    content = f.read()
                except Exception:
                    continue
            relpath = os.path.relpath(filepath, self.repo_path)

            self._check_insert_vs_upsert(relpath, content)
            self._check_field_gaps(relpath, content)
            self._check_circuit_breaker(relpath, content)
            self._check_bare_except(relpath, content)
            self._check_missing_await(relpath, content)
            self._check_hardcoded_fallbacks(relpath, content)

        self._print_results()
        return self.bugs

    def _check_insert_vs_upsert(self, filepath, content):
        """Detect tables using INSERT where UPSERT would prevent duplicates."""
        inserts = re.findall(r'\.table\(["\'](\w+)["\']\)\.insert\(', content)
        upserts = re.findall(r'\.table\(["\'](\w+)["\']\)\.upsert\(', content)

        insert_tables = set(inserts)
        upsert_tables = set(upserts)
        mixed = insert_tables & upsert_tables

        for table in insert_tables - {'insights', 'audit_logs', 'agent_events'}:
            if table not in upsert_tables:
                self.bugs.append({
                    "file": filepath,
                    "type": "DUPLICATE_RISK",
                    "severity": "HIGH",
                    "message": f"Table '{table}' uses INSERT only — duplicates on re-run. Consider UPSERT or DELETE+INSERT.",
                    "pattern": f".table('{table}').insert("
                })

    def _check_field_gaps(self, filepath, content):
        """Detect fields extracted by prompts but not stored by writers."""
        # Find dims.get("field") patterns
        gets = set(re.findall(r'dims\.get\(["\'](\w+)["\']', content))
        # Find JSON prompt field definitions
        prompt_fields = set(re.findall(r'"(min_\w+|max_\w+)":\s*null', content))

        if prompt_fields and gets:
            missing = prompt_fields - gets - {'confidence'}
            if missing:
                self.bugs.append({
                    "file": filepath,
                    "type": "DATA_LOSS",
                    "severity": "MEDIUM",
                    "message": f"Fields extracted but never stored: {missing}",
                    "pattern": f"Missing: {', '.join(missing)}"
                })

    def _check_circuit_breaker(self, filepath, content):
        """Detect methods that increment errors but not consecutive_failures."""
        # Find all methods in the file
        methods = re.findall(r'((?:async\s+)?def\s+(\w+)\([^)]*\).*?)(?=(?:async\s+)?def\s|\Z)', content, re.DOTALL)

        for method_body, method_name in methods:
            has_errors = "self.errors += 1" in method_body
            has_consecutive = "consecutive_failures" in method_body
            has_circuit = "_trip_circuit" in method_body or "_is_circuit_open" in method_body

            if has_errors and has_circuit and not has_consecutive:
                self.bugs.append({
                    "file": filepath,
                    "type": "CIRCUIT_BREAKER_GAP",
                    "severity": "MEDIUM",
                    "message": f"Method '{method_name}' tracks errors and checks circuit but never increments consecutive_failures",
                    "pattern": f"def {method_name}"
                })

    def _check_bare_except(self, filepath, content):
        """Detect bare except clauses that swallow errors silently."""
        for i, line in enumerate(content.split('\n'), 1):
            stripped = line.strip()
            if stripped == "except:" or stripped == "except Exception:":
                # Check if next lines have pass or just += 1
                lines = content.split('\n')
                if i < len(lines):
                    next_lines = '\n'.join(lines[i:i+3])
                    if 'pass' in next_lines and 'log' not in next_lines.lower():
                        self.warnings.append({
                            "file": filepath,
                            "type": "SILENT_FAILURE",
                            "severity": "LOW",
                            "message": f"Line {i}: bare except with pass — errors silently swallowed",
                            "line": i
                        })

    def _check_missing_await(self, filepath, content):
        """Detect async functions called without await."""
        async_funcs = set(re.findall(r'async\s+def\s+(\w+)', content))
        for func in async_funcs:
            # Find calls to this function without await
            calls_without_await = re.findall(rf'(?<!await\s)(?<!await\s\s)\bself\.{func}\(', content)
            if calls_without_await:
                self.warnings.append({
                    "file": filepath,
                    "type": "MISSING_AWAIT",
                    "severity": "HIGH",
                    "message": f"Async method '{func}' may be called without await",
                    "pattern": f"self.{func}("
                })

    def _check_hardcoded_fallbacks(self, filepath, content):
        """Detect hardcoded fallback values that should be dynamic."""
        hardcoded = re.findall(r'if\s+\w+\s+in\s+\[[\d,\s]+\]:\s*\n\s*return', content)
        if hardcoded:
            self.warnings.append({
                "file": filepath,
                "type": "HARDCODED_FALLBACK",
                "severity": "LOW",
                "message": "Hardcoded list used as fallback condition — may not cover all cases",
                "pattern": hardcoded[0][:80]
            })

    def _print_results(self):
        print(f"\n{'=' * 60}")
        print(f"BUG HUNT RESULTS")
        print(f"{'=' * 60}")

        if self.bugs:
            print(f"\n🐛 BUGS FOUND: {len(self.bugs)}")
            for b in self.bugs:
                print(f"\n  [{b['severity']}] {b['type']}")
                print(f"  File: {b['file']}")
                print(f"  {b['message']}")
                if 'pattern' in b:
                    print(f"  Pattern: {b['pattern']}")
        else:
            print(f"\n✅ No bugs detected")

        if self.warnings:
            print(f"\n⚠ WARNINGS: {len(self.warnings)}")
            for w in self.warnings:
                print(f"  [{w['severity']}] {w['file']}: {w['message']}")

        print(f"\n{'=' * 60}")
        print(f"Total: {len(self.bugs)} bugs, {len(self.warnings)} warnings")
        print(f"{'=' * 60}")


def clone_repo(repo_name, target_dir):
    """Download repo via GitHub API tarball."""
    os.makedirs(target_dir, exist_ok=True)
    tarball_url = f"https://api.github.com/repos/{ORG}/{repo_name}/tarball/main"

    req = urllib.request.Request(tarball_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            tarball = resp.read()
    except Exception:
        # Try master branch
        req = urllib.request.Request(tarball_url.replace("/main", "/master"), headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            tarball = resp.read()

    tar_path = os.path.join(target_dir, "repo.tar.gz")
    with open(tar_path, "wb") as f:
        f.write(tarball)

    import tarfile
    with tarfile.open(tar_path) as tar:
        tar.extractall(target_dir)

    os.remove(tar_path)
    # Find extracted directory
    for item in os.listdir(target_dir):
        if os.path.isdir(os.path.join(target_dir, item)):
            return os.path.join(target_dir, item)
    return target_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunt bugs in a repo")
    parser.add_argument("--repo", type=str, help="GitHub repo name to scan")
    parser.add_argument("--path", type=str, help="Local path to scan")
    args = parser.parse_args()

    if args.path:
        repo_path = args.path
    elif args.repo:
        print(f"Cloning {args.repo}...")
        repo_path = clone_repo(args.repo, f"/tmp/bug_hunt_{args.repo}")
    else:
        print("Usage: --repo <name> or --path <local_path>")
        sys.exit(1)

    hunter = BugHunter(repo_path)
    bugs = hunter.scan_all()
    sys.exit(1 if bugs else 0)
