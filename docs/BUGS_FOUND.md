# Bugs Found with DAP Debugger

Registry of all production bugs discovered and fixed using the DAP debug workflow.

## 2026-03-08 — zonewise-scraper-v4

### BUG-001: Blind CH62 fallback in zoning URL resolver
- **File:** `src/pipeline/orchestrator.py` → `_find_zoning_url()`
- **Severity:** Medium
- **Impact:** Scraper returns wrong Municode URL for municipalities whose zoning code isn't in Chapter 62. Causes failed scrapes flagged as "No zoning URL in TOC" when the URL actually exists under a different chapter.
- **Root Cause:** Fallback logic iterated chapter numbers `[62, 34, 27, 26]` but returned the first match immediately with `if chapter_num in [62, 34, 27, 26]: return test_url` — never checking if the chapter actually exists in the TOC.
- **Fix:** Extract chapter numbers from TOC markdown via regex `r'Chapter\s+(\d+)'`, prioritize those, then fall back to common numbers.
- **DAP Session:** Not needed — found via static analysis of code path.

### BUG-002: Duplicate permitted_uses on re-scrape
- **File:** `src/utils/supabase_writer.py` → `_write_permitted_use()`
- **Severity:** HIGH
- **Impact:** Every re-scrape of a jurisdiction doubled its `permitted_uses` records. 1,386 duplicate rows found in production across 1,064 groups. Data analysis and reporting would show inflated use counts.
- **Root Cause:** `write_districts()` used `upsert()` for `zoning_districts` (idempotent) but `insert()` for `permitted_uses`. No dedup on re-run.
- **Fix:** Delete existing uses for a district before inserting new ones. Added DB unique index `idx_permitted_uses_unique` on `(zoning_district_id, use_description, use_type)` as safety net.
- **DAP Session:**
  ```
  dap debug bug_hunter.py --break src/utils/supabase_writer.py:43 --break src/utils/supabase_writer.py:121
  # Stopped at line 43: .upsert() for districts ← correct
  # Stopped at line 121: .insert() for uses ← BUG
  ```
- **Data Cleanup:** 1,386 rows deleted via `DELETE FROM permitted_uses WHERE id NOT IN (SELECT MIN(id) ... GROUP BY ...)`

### BUG-003: Missing dimensional fields in writer
- **File:** `src/utils/supabase_writer.py` → `_write_zone_standards()`
- **Severity:** Medium
- **Impact:** `min_lot_width_ft` and `min_lot_depth_ft` extracted by Gemini prompt but never stored in Supabase. Silent data loss on every scrape — the fields existed in the DB schema but writer never populated them.
- **Root Cause:** `_write_zone_standards()` built its record dict with 13 `dims.get()` calls but missed `min_lot_width_ft` and `min_lot_depth_ft` despite both being in the Gemini extraction prompt.
- **Fix:** Added `dims.get("min_lot_width_ft")` and `dims.get("min_lot_depth_ft")` to the record dict.
- **DAP Session:** Not needed — found via `inspect.getsource()` comparing prompt fields to writer fields.

### BUG-004: Circuit breaker gap in scrape_with_actions
- **File:** `src/scrapers/firecrawl_scraper.py` → `scrape_with_actions()`
- **Severity:** Medium
- **Impact:** `scrape_with_actions()` failure paths incremented `self.errors` but not `self.consecutive_failures`. Circuit breaker could never trip from action-based scrapes, allowing infinite retries against failing Municode sites that require JavaScript interaction.
- **Root Cause:** Copy-paste gap — `scrape()` had full circuit breaker logic in both `except` and `else` blocks, but `scrape_with_actions()` only had `self.errors += 1`.
- **Fix:** Added `self.consecutive_failures += 1` and `if self.consecutive_failures >= self.max_failures: self._trip_circuit()` to both failure paths.
- **DAP Session:** Not needed — found via `inspect.getsource()` comparing both methods.

### Database Constraints Added
- `CREATE UNIQUE INDEX idx_permitted_uses_unique ON permitted_uses (zoning_district_id, use_description, use_type)`
- `ALTER TABLE permitted_uses ADD CONSTRAINT fk_permitted_uses_district FOREIGN KEY (zoning_district_id) REFERENCES zoning_districts(id) ON DELETE CASCADE`
- `ALTER TABLE zone_standards ADD CONSTRAINT fk_zone_standards_district FOREIGN KEY (zoning_district_id) REFERENCES zoning_districts(id) ON DELETE CASCADE`
