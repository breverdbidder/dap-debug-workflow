# DAP Debug Workflow

**Autonomous bug hunting, fixing, and verification pipeline for the Shapira Agentic Stack.**

Phone → Claude → Diagnose with DAP → Fix → Deploy → Verify → Done.

## What This Does

This repo contains the complete automation pipeline for deploying the [debug-skill](https://github.com/AlmogBaku/debug-skill) debugger across all BidDeed.AI and ZoneWise.AI repositories, then using it to find, fix, and verify production bugs — all triggered from a mobile phone via Claude Code Remote Control.

## Architecture

```
📱 Phone ──▶ Claude AI ──▶ Claude Code ──▶ dap ──▶ Fix ──▶ Push ──▶ Verify
```

### 5-Phase Pipeline

| Phase | What | Scripts |
|-------|------|---------|
| **0. Trigger** | Mobile → Claude AI → Claude Code `/rc` | Manual |
| **1. Deploy** | Push SKILL.md + CLAUDE.md + auto-install to all repos | `scripts/deploy_skill.py` |
| **2. Hunt** | Static analysis + DAP breakpoint debugging | `scripts/bug_hunter.py` |
| **3. Fix** | Code fixes pushed via GitHub API | `scripts/push_fixes.py` |
| **4. Data** | Supabase dedup, orphan cleanup, constraints | `scripts/fix_supabase.py` |
| **5. Verify** | 19-test suite: 13 code + 6 database | `tests/test_bug_fixes.py` |

## Quick Start

```bash
# Deploy debug-skill to all repos
python3 scripts/deploy_skill.py

# Hunt bugs in a specific repo
python3 scripts/bug_hunter.py --repo zonewise-scraper-v4

# Fix production Supabase data
python3 scripts/fix_supabase.py

# Run full verification
python3 tests/test_bug_fixes.py
```

## GitHub Actions

The `verify.yml` workflow runs the test suite on every push and nightly at midnight EST.

## What DAP Debugger Replaces

**Before (print-statement debugging):**
1. Add `print(type(x))` → rerun → read output
2. Add `print(len(x))` → rerun → read output  
3. Add `print(x)` → rerun → finally understand
4. ~15-20 minutes per non-obvious bug

**After (DAP debugging):**
1. `dap debug script.py --break script.py:42` → inspect all locals, call stack, types in one stop
2. ~3-5 minutes per bug

## Proven Results

First run found and fixed 4 production bugs in `zonewise-scraper-v4`:

- **Bug 1:** Blind CH62 fallback in zoning URL resolver
- **Bug 2:** Duplicate `permitted_uses` on every re-scrape (1,386 bad rows cleaned)
- **Bug 3:** `min_lot_width_ft` and `min_lot_depth_ft` silently dropped
- **Bug 4:** Circuit breaker dead in `scrape_with_actions`

Plus added DB constraints (unique index + foreign keys) to prevent recurrence.

## Repo Structure

```
dap-debug-workflow/
├── CLAUDE.md                    # Claude Code directive
├── DAP_WORKFLOW_ASCII.md        # Full pipeline diagram
├── README.md                    # This file
├── scripts/
│   ├── deploy_skill.py          # Phase 1: Deploy to all repos
│   ├── bug_hunter.py            # Phase 2: Static analysis bug finder
│   ├── push_fixes.py            # Phase 3: Push code fixes
│   └── fix_supabase.py          # Phase 4: Database cleanup
├── tests/
│   └── test_bug_fixes.py        # Phase 5: 19-test verification suite
├── skills/
│   └── debugging-code/
│       └── SKILL.md             # DAP debugger skill for Claude Code
├── docs/
│   └── BUGS_FOUND.md            # Registry of bugs found with DAP
└── .github/
    └── workflows/
        └── verify.yml           # Nightly verification
```

## License

MIT
