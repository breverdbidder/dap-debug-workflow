
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                            ║
║                    DAP DEBUG WORKFLOW — AUTONOMOUS BUG HUNTING & FIXING PIPELINE                            ║
║                    ─────────────────────────────────────────────────────────────                             ║
║                    BidDeed.AI + ZoneWise.AI · Everest Capital USA                                           ║
║                    Phone → Claude → Diagnose → Fix → Deploy → Verify                                       ║
║                                                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝


 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 0: TRIGGER (Mobile)                                          │
 │                                                                                                         │
 │    📱 Phone                    Claude AI (claude.ai)               Claude Code (Remote Control)         │
 │    ┌──────────┐               ┌──────────────────┐                ┌────────────────────┐                │
 │    │  "Fix    │──── chat ────▶│  AI Architect    │──── /rc ──────▶│  Agentic Engineer  │                │
 │    │  bugs"   │               │  Plans workflow  │                │  Executes on host  │                │
 │    └──────────┘               └──────────────────┘                └─────────┬──────────┘                │
 │                                                                             │                           │
 └─────────────────────────────────────────────────────────────────────────────┼───────────────────────────┘
                                                                               │
                                                                               ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 1: DEPLOY DEBUG SKILL                                        │
 │                                                                                                         │
 │  ┌───────────────────┐     ┌──────────────────────┐     ┌──────────────────────────────────────────┐   │
 │  │  GitHub API        │     │  For each repo:      │     │  3 Layers Deployed:                      │   │
 │  │  ┌──────────────┐ │     │  ┌──────────────────┐ │     │                                          │   │
 │  │  │ List repos   │─┼────▶│  │ skills/debugging- │ │     │  Layer 1: skills/debugging-code/SKILL.md │   │
 │  │  │ Filter by:   │ │     │  │ code/SKILL.md     │ │     │  Layer 2: CLAUDE.md debug section        │   │
 │  │  │  - Language  │ │     │  │                   │ │     │  Layer 3: scripts/install-debug-tools.sh  │   │
 │  │  │  - Active    │ │     │  ├──────────────────┤ │     │                                          │   │
 │  │  │  - !Archived │ │     │  │ Append CLAUDE.md  │ │     │  Repos: 23 active repositories           │   │
 │  │  └──────────────┘ │     │  │ w/ DAP section    │ │     │  Languages: Python, TypeScript, JS       │   │
 │  │                    │     │  ├──────────────────┤ │     │                                          │   │
 │  │  Token:            │     │  │ Push auto-install │ │     │  Auto-install: dap binary if missing     │   │
 │  │  ghp_ij7L...MEv9C  │     │  │ hook script      │ │     │  Source: AlmogBaku/debug-skill v0.1.3    │   │
 │  └───────────────────┘     │  └──────────────────┘ │     └──────────────────────────────────────────┘   │
 │                             └──────────────────────┘                                                    │
 └──────────────────────────────────────────────────────────────────────┬──────────────────────────────────┘
                                                                        │
                                                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 2: BUG HUNTING                                               │
 │                                                                                                         │
 │  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐    │
 │  │                              Static Analysis + Code Inspection                                  │    │
 │  │                                                                                                  │    │
 │  │   inspect.getsource() ──▶ Parse function bodies ──▶ Compare INSERT vs UPSERT patterns           │    │
 │  │   re.findall()         ──▶ Extract field names    ──▶ Compare prompt fields vs writer fields      │    │
 │  │   AST comparison       ──▶ Check both code paths  ──▶ Verify circuit breaker coverage            │    │
 │  │                                                                                                  │    │
 │  │   Output: bug_hunter.py ──▶ Confirms 4 bugs reproducible without external APIs                   │    │
 │  └─────────────────────────────────────────────────────────────────────────────────────────────────┘    │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────┐                                       │
 │  │                    DAP Debugger Session                       │                                       │
 │  │                                                              │                                       │
 │  │   dap debug script.py                                        │                                       │
 │  │     --break file.py:50        ◀── Hypothesis: type mismatch  │                                       │
 │  │     --break file.py:83        ◀── Hypothesis: wrong count    │                                       │
 │  │                                                              │                                       │
 │  │   ┌─────────────────────────────────────────────┐            │                                       │
 │  │   │ Stopped: breakpoint                          │            │                                       │
 │  │   │ Function: tier2_gemini_parse                 │            │                                       │
 │  │   │ File: pipeline_bug.py:54                     │            │                                       │
 │  │   │                                              │            │                                       │
 │  │   │ Locals:                                      │            │                                       │
 │  │   │   districts_raw (list) = ['R-1','R-2',...]   │  ◀── Good │                                       │
 │  │   │   districts (str) = 'R-1, R-2, ...'          │  ◀── BUG! │                                       │
 │  │   │                                              │            │                                       │
 │  │   │ Stack:                                       │            │                                       │
 │  │   │   #0 tier2_gemini_parse:54                   │            │                                       │
 │  │   │   #1 run_pipeline:109                        │            │                                       │
 │  │   └─────────────────────────────────────────────┘            │                                       │
 │  │                                                              │                                       │
 │  │   dap eval "type(districts).__name__"  ──▶ 'str'    ◀── ROOT │                                       │
 │  │   dap eval "len(districts)"            ──▶ 28       ◀── CAUSE│                                       │
 │  │   dap eval "districts.split(', ')"     ──▶ [6 items]◀── FIX  │                                       │
 │  │   dap stop                                                   │                                       │
 │  └──────────────────────────────────────────────────────────────┘                                       │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │                                BUGS FOUND                                                        │   │
 │  │                                                                                                  │   │
 │  │  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐ │   │
 │  │  │ BUG 1              │ │ BUG 2              │ │ BUG 3              │ │ BUG 4                  │ │   │
 │  │  │ orchestrator.py    │ │ supabase_writer.py │ │ supabase_writer.py │ │ firecrawl_scraper.py   │ │   │
 │  │  │                    │ │                    │ │                    │ │                        │ │   │
 │  │  │ _find_zoning_url   │ │ INSERT not UPSERT  │ │ min_lot_width_ft   │ │ consecutive_failures   │ │   │
 │  │  │ always returns     │ │ on permitted_uses  │ │ min_lot_depth_ft   │ │ not incremented in     │ │   │
 │  │  │ CH62 blindly       │ │ duplicates on      │ │ extracted but      │ │ scrape_with_actions    │ │   │
 │  │  │                    │ │ every re-scrape    │ │ never stored       │ │                        │ │   │
 │  │  │ SEVERITY: Medium   │ │ SEVERITY: HIGH     │ │ SEVERITY: Medium   │ │ SEVERITY: Medium       │ │   │
 │  │  └────────────────────┘ └────────────────────┘ └────────────────────┘ └────────────────────────┘ │   │
 │  └──────────────────────────────────────────────────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┬──────────────────────────────────┘
                                                                        │
                                                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 3: FIX CODE                                                  │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │  orchestrator.py                          supabase_writer.py          firecrawl_scraper.py       │   │
 │  │  ┌────────────────────────┐               ┌──────────────────┐       ┌──────────────────────┐   │   │
 │  │  │ BEFORE:                │               │ BEFORE:          │       │ BEFORE:              │   │   │
 │  │  │ if ch in [62,34,27,26]:│               │ .insert(record)  │       │ self.errors += 1     │   │   │
 │  │  │   return test_url      │               │                  │       │ return ScrapeResult() │   │   │
 │  │  │                        │               │ Missing:         │       │                      │   │   │
 │  │  │ AFTER:                 │               │  min_lot_width   │       │ AFTER:               │   │   │
 │  │  │ toc_chapters = set()   │               │  min_lot_depth   │       │ self.errors += 1     │   │   │
 │  │  │ re.findall(Chapter\d+) │               │                  │       │ consecutive_failures │   │   │
 │  │  │ prioritize TOC matches │               │ AFTER:           │       │   += 1               │   │   │
 │  │  │ then fallback          │               │ .delete().eq()   │       │ if >= max_failures:  │   │   │
 │  │  │                        │               │ .insert(record)  │       │   _trip_circuit()    │   │   │
 │  │  │                        │               │                  │       │                      │   │   │
 │  │  │                        │               │ Added:           │       │                      │   │   │
 │  │  │                        │               │  min_lot_width   │       │                      │   │   │
 │  │  │                        │               │  min_lot_depth   │       │                      │   │   │
 │  │  └────────────────────────┘               └──────────────────┘       └──────────────────────┘   │   │
 │  └──────────────────────────────────────────────────────────────────────────────────────────────────┘   │
 │                                                                                                         │
 │                               GitHub API PUT ──▶ 3 commits pushed to main                               │
 │                               Repo: breverdbidder/zonewise-scraper-v4                                   │
 └──────────────────────────────────────────────────────────────────────┬──────────────────────────────────┘
                                                                        │
                                                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 4: FIX DATA (Production Supabase)                            │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │                          Supabase Management API                                                 │   │
 │  │                          Project: mocerqjnksmhcjzxrewo                                           │   │
 │  │                                                                                                  │   │
 │  │   Step 1: ASSESS                                                                                 │   │
 │  │   ┌─────────────────────────────────────────────────────────┐                                    │   │
 │  │   │ SELECT COUNT(*) ... GROUP BY ... HAVING COUNT(*) > 1    │                                    │   │
 │  │   │ Result: 1,064 duplicate groups, 1,386 rows to delete    │                                    │   │
 │  │   │ Total: 13,969 ──▶ Target: 12,583 unique rows            │                                    │   │
 │  │   └─────────────────────────────────────────────────────────┘                                    │   │
 │  │                                                                                                  │   │
 │  │   Step 2: DEDUPLICATE                                                                            │   │
 │  │   ┌─────────────────────────────────────────────────────────┐                                    │   │
 │  │   │ DELETE FROM permitted_uses                               │                                    │   │
 │  │   │ WHERE id NOT IN (                                        │                                    │   │
 │  │   │   SELECT MIN(id) FROM permitted_uses                     │                                    │   │
 │  │   │   GROUP BY zoning_district_id, use_description, use_type │                                    │   │
 │  │   │ )                                                        │                                    │   │
 │  │   │ Result: 1,386 rows deleted ✅                            │                                    │   │
 │  │   └─────────────────────────────────────────────────────────┘                                    │   │
 │  │                                                                                                  │   │
 │  │   Step 3: CLEAN ORPHANS                                                                          │   │
 │  │   ┌─────────────────────────────────────────────────────────┐                                    │   │
 │  │   │ DELETE FROM permitted_uses WHERE zoning_district_id      │                                    │   │
 │  │   │   NOT IN (SELECT id FROM zoning_districts)               │                                    │   │
 │  │   │ DELETE FROM zone_standards WHERE zoning_district_id      │                                    │   │
 │  │   │   NOT IN (SELECT id FROM zoning_districts)               │                                    │   │
 │  │   │ Result: 4 orphans cleaned ✅                             │                                    │   │
 │  │   └─────────────────────────────────────────────────────────┘                                    │   │
 │  │                                                                                                  │   │
 │  │   Step 4: PREVENT RECURRENCE                                                                     │   │
 │  │   ┌─────────────────────────────────────────────────────────┐                                    │   │
 │  │   │ CREATE UNIQUE INDEX idx_permitted_uses_unique            │                                    │   │
 │  │   │   ON permitted_uses (zoning_district_id,                 │                                    │   │
 │  │   │   use_description, use_type)                             │                                    │   │
 │  │   │                                                          │                                    │   │
 │  │   │ ALTER TABLE permitted_uses ADD CONSTRAINT                │                                    │   │
 │  │   │   fk_permitted_uses_district FOREIGN KEY                 │                                    │   │
 │  │   │   (zoning_district_id) REFERENCES zoning_districts(id)   │                                    │   │
 │  │   │   ON DELETE CASCADE                                      │                                    │   │
 │  │   │                                                          │                                    │   │
 │  │   │ ALTER TABLE zone_standards ADD CONSTRAINT                │                                    │   │
 │  │   │   fk_zone_standards_district FOREIGN KEY                 │                                    │   │
 │  │   │   (zoning_district_id) REFERENCES zoning_districts(id)   │                                    │   │
 │  │   │   ON DELETE CASCADE                                      │                                    │   │
 │  │   └─────────────────────────────────────────────────────────┘                                    │   │
 │  └──────────────────────────────────────────────────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┬──────────────────────────────────┘
                                                                        │
                                                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     PHASE 5: VERIFY                                                    │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │  tests/test_bug_fixes.py — 19 Total Tests                                                       │   │
 │  │                                                                                                  │   │
 │  │  ┌───────────────────────────────────┐  ┌───────────────────────────────────────────────────┐    │   │
 │  │  │ CODE TESTS (13)                   │  │ DATABASE TESTS (6)                                │    │   │
 │  │  │                                   │  │                                                   │    │   │
 │  │  │ Bug 1: 3 tests                   │  │ ✅ Zero duplicates in permitted_uses              │    │   │
 │  │  │  ✅ Extracts TOC chapters         │  │ ✅ Unique constraint idx_permitted_uses_unique    │    │   │
 │  │  │  ✅ Prefers TOC over hardcoded    │  │ ✅ Zero orphaned permitted_uses                   │    │   │
 │  │  │  ✅ Graceful fallback             │  │ ✅ Zero orphaned zone_standards                   │    │   │
 │  │  │                                   │  │ ✅ min_lot_width_ft column exists                 │    │   │
 │  │  │ Bug 2: 2 tests                   │  │ ✅ min_lot_depth_ft column exists                 │    │   │
 │  │  │  ✅ delete() before insert()      │  │                                                   │    │   │
 │  │  │  ✅ Re-scrape = same row count    │  │ Verified via:                                     │    │   │
 │  │  │                                   │  │ Supabase Management API                           │    │   │
 │  │  │ Bug 3: 4 tests                   │  │ POST /v1/projects/{ref}/database/query             │    │   │
 │  │  │  ✅ Stores width field            │  │                                                   │    │   │
 │  │  │  ✅ Stores depth field            │  └───────────────────────────────────────────────────┘    │   │
 │  │  │  ✅ All Gemini fields matched     │                                                           │   │
 │  │  │  ✅ Values pass through correctly │                                                           │   │
 │  │  │                                   │                                                           │   │
 │  │  │ Bug 4: 4 tests                   │                                                           │   │
 │  │  │  ✅ Increments failures           │                                                           │   │
 │  │  │  ✅ Calls _trip_circuit           │                                                           │   │
 │  │  │  ✅ Exception path covered        │                                                           │   │
 │  │  │  ✅ Circuit trips + blocks        │                                                           │   │
 │  │  └───────────────────────────────────┘                                                           │   │
 │  └──────────────────────────────────────────────────────────────────────────────────────────────────┘   │
 │                                                                                                         │
 │                                        RESULT: 19/19 PASSED ✅                                          │
 └──────────────────────────────────────────────────────────────────────┬──────────────────────────────────┘
                                                                        │
                                                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     FINAL STATE                                                        │
 │                                                                                                         │
 │  ┌──────────────────────────────┐  ┌──────────────────────────────┐  ┌───────────────────────────────┐  │
 │  │ GITHUB                       │  │ SUPABASE                     │  │ PROTECTION                    │  │
 │  │                              │  │                              │  │                               │  │
 │  │ 23 repos: SKILL.md deployed  │  │ 5,937 zoning districts      │  │ ✅ Unique index on uses       │  │
 │  │ 21 repos: CLAUDE.md updated  │  │ 2,359 zone standards        │  │ ✅ FK cascade on uses         │  │
 │  │  8 repos: auto-install hook  │  │ 12,582 permitted uses       │  │ ✅ FK cascade on standards    │  │
 │  │  3 files: bug fixes pushed   │  │ 367 jurisdictions scraped   │  │ ✅ Code: delete-before-insert │  │
 │  │  1 file:  test suite pushed  │  │ 0 duplicates                │  │ ✅ Code: all fields stored    │  │
 │  │                              │  │ 0 orphans                   │  │ ✅ Code: circuit breaker full │  │
 │  └──────────────────────────────┘  └──────────────────────────────┘  └───────────────────────────────┘  │
 │                                                                                                         │
 │  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │  ARCHITECTURE: How it works going forward                                                        │   │
 │  │                                                                                                  │   │
 │  │   📱 Phone ──▶ Claude AI ──▶ Claude Code ──▶ dap ──▶ Fix ──▶ Push ──▶ Verify                    │   │
 │  │                                                                                                  │   │
 │  │   Claude Code reads CLAUDE.md ──▶ Sees "ALWAYS use dap" ──▶ Sets breakpoints ──▶ Inspects        │   │
 │  │   locals + call stack ──▶ Pinpoints root cause ──▶ Fixes in 1 pass (not 4 print-rerun cycles)   │   │
 │  │                                                                                                  │   │
 │  │   dap debug script.py --break script.py:42                                                       │   │
 │  │     └──▶ Unix socket ──▶ Daemon ──▶ DAP protocol ──▶ debugpy ──▶ your program                   │   │
 │  └──────────────────────────────────────────────────────────────────────────────────────────────────┘   │
 │                                                                                                         │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘


 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │  REPO MAP                                                                                               │
 │                                                                                                         │
 │  breverdbidder/dap-debug-workflow          ◀── THIS REPO (workflow + automation scripts)                │
 │  breverdbidder/zonewise-scraper-v4         ◀── Primary target (4 bugs found + fixed)                   │
 │  breverdbidder/biddeed-ai-ui              ◀── debug-skill deployed                                     │
 │  breverdbidder/zonewise-agents            ◀── debug-skill deployed                                     │
 │  breverdbidder/zonewise-web               ◀── debug-skill deployed                                     │
 │  breverdbidder/api-layer                  ◀── debug-skill deployed                                     │
 │  breverdbidder/life-os                    ◀── debug-skill deployed                                     │
 │  breverdbidder/qa-agentic-pipeline        ◀── debug-skill deployed                                     │
 │  + 16 more repos                           ◀── debug-skill deployed                                     │
 │                                                                                                         │
 │  Source: github.com/AlmogBaku/debug-skill  ◀── dap CLI + skill (MIT, v0.1.3)                           │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
