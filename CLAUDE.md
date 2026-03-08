# CLAUDE.md — DAP Debug Workflow

## Zero Human-in-the-Loop
All operations PRE-APPROVED. Execute autonomously.

## Purpose
This repo automates the full debug-skill deployment and bug-fixing pipeline across all breverdbidder GitHub repos. It is the canonical source for DAP debugger integration.

## Commands
```bash
python3 scripts/deploy_skill.py          # Deploy to all repos
python3 scripts/bug_hunter.py            # Find bugs via static analysis
python3 scripts/fix_supabase.py          # Clean production DB
python3 tests/test_bug_fixes.py          # Verify all fixes
```

## Credentials
- GitHub PAT: Use `GITHUB_TOKEN` env var or hardcoded in scripts
- Supabase: Retrieved via Management API token `SUPABASE_MGMT_TOKEN`
- Project ref: `mocerqjnksmhcjzxrewo`

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
