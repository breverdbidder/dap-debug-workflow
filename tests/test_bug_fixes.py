"""
ZoneWise Scraper V4.2 — Bug Fix Verification Suite
Tests each of the 4 dap-diagnosed fixes against actual code.

Run: python3 tests/test_bug_fixes.py
"""
import os
import sys
import re
import json
import inspect
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def test(name):
    """Decorator to run and report test results."""
    def decorator(func):
        global PASS, FAIL
        try:
            result = func()
            if result is True:
                print(f"  ✅ PASS: {name}")
                PASS += 1
            else:
                print(f"  ❌ FAIL: {name} — returned {result}")
                FAIL += 1
        except Exception as e:
            print(f"  ❌ FAIL: {name} — {type(e).__name__}: {e}")
            FAIL += 1
    return decorator


# ═══════════════════════════════════════════════════════════════
# BUG 1: _find_zoning_url fallback should use TOC chapter numbers
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("BUG 1: _find_zoning_url fallback uses TOC chapters")
print("=" * 60)


@test("Fallback extracts chapter numbers from TOC markdown")
def _():
    from src.pipeline.orchestrator import Orchestrator
    with patch.dict(os.environ, {
        "FIRECRAWL_API_KEY": "test", "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test"
    }):
        with patch("src.utils.supabase_writer.create_client"):
            orch = Orchestrator()

    # TOC with Chapter 34 (no zoning links, but chapter mentioned)
    toc = """
# Code of Ordinances
## Chapter 10 - Buildings
[Chapter 10](https://library.municode.com/fl/tampa/codes/code_of_ordinances?nodeId=PTIICOOR_CH10BU)
## Chapter 34 - Land Development
[Chapter 34](https://library.municode.com/fl/tampa/codes/code_of_ordinances?nodeId=PTIICOOR_CH34LADE)
## Chapter 50 - Parks
"""
    base = "https://library.municode.com/fl/tampa/codes/code_of_ordinances"
    result = orch._find_zoning_url(toc, base)

    # Should pick up chapters from TOC — should try CH34 or CH10 patterns, not blindly CH62
    assert result is not None, "Should return a URL"
    # Should NOT be CH62 since that's not in the TOC
    assert "CH62" not in result, f"Should not blindly return CH62, got: {result}"
    return True


@test("Fallback prefers TOC chapters over hardcoded fallbacks")
def _():
    from src.pipeline.orchestrator import Orchestrator
    with patch.dict(os.environ, {
        "FIRECRAWL_API_KEY": "test", "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test"
    }):
        with patch("src.utils.supabase_writer.create_client"):
            orch = Orchestrator()

    # TOC with only Chapter 27
    toc = "# Code\n## Chapter 27 - Zoning and Planning"
    base = "https://library.municode.com/fl/ocala/codes/code_of_ordinances"
    result = orch._find_zoning_url(toc, base)

    assert result is not None
    assert "CH27" in result, f"Should prefer CH27 from TOC, got: {result}"
    return True


@test("Fallback still works when TOC has no chapter numbers")
def _():
    from src.pipeline.orchestrator import Orchestrator
    with patch.dict(os.environ, {
        "FIRECRAWL_API_KEY": "test", "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test"
    }):
        with patch("src.utils.supabase_writer.create_client"):
            orch = Orchestrator()

    toc = "No chapter numbers here, just text about regulations."
    base = "https://library.municode.com/fl/naples/codes/code_of_ordinances"
    result = orch._find_zoning_url(toc, base)

    # Falls back to common chapter numbers
    assert result is not None, "Should still return fallback URL"
    return True


# ═══════════════════════════════════════════════════════════════
# BUG 2: Duplicate permitted_uses on re-scrape
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("BUG 2: permitted_uses deduplication on re-scrape")
print("=" * 60)


@test("write_districts deletes existing uses before inserting")
def _():
    source = inspect.getsource(
        __import__("src.utils.supabase_writer", fromlist=["SupabaseWriter"]).SupabaseWriter.write_districts
    )
    assert ".delete()" in source, "write_districts must call .delete() before inserting uses"
    assert "zoning_district_id" in source.split(".delete()")[1].split(".execute()")[0], \
        "delete must filter by zoning_district_id"
    return True


@test("Re-scrape does not create duplicate use records")
def _():
    from src.utils.supabase_writer import SupabaseWriter

    all_calls = {"insert": [], "delete": []}
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    def track_insert(data):
        all_calls["insert"].append(data)
        r = MagicMock()
        r.execute.return_value = MagicMock(data=[{"id": len(all_calls["insert"])}])
        return r

    def track_upsert(data, **kwargs):
        r = MagicMock()
        r.execute.return_value = MagicMock(data=[{"id": 1}])
        return r

    def track_delete():
        all_calls["delete"].append(True)
        eq_mock = MagicMock()
        eq_mock.execute.return_value = MagicMock(data=[])
        chain = MagicMock()
        chain.eq.return_value = eq_mock
        return chain

    mock_table.insert.side_effect = track_insert
    mock_table.upsert.side_effect = track_upsert
    mock_table.delete.side_effect = track_delete

    with patch("src.utils.supabase_writer.create_client", return_value=mock_client):
        writer = SupabaseWriter(url="https://test.supabase.co", key="test")

    districts = [{
        "code": "R-1", "name": "Single Family", "category": "residential",
        "permitted_uses": [
            {"use_description": "Single-family dwelling", "use_category": "residential", "confidence": 0.9},
        ],
        "conditional_uses": []
    }]

    # Run twice
    writer.write_districts(jurisdiction_id=42, districts=districts)
    run1_inserts = len(all_calls["insert"])

    all_calls["insert"].clear()
    writer.write_districts(jurisdiction_id=42, districts=districts)
    run2_inserts = len(all_calls["insert"])

    # Delete should be called before each insert batch
    assert len(all_calls["delete"]) >= 2, f"delete() should be called on each run, got {len(all_calls['delete'])}"
    assert run1_inserts == run2_inserts == 1, f"Each run should insert 1 use, got {run1_inserts}, {run2_inserts}"
    return True


# ═══════════════════════════════════════════════════════════════
# BUG 3: Missing dimensional fields in writer
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("BUG 3: Dimensional fields completeness")
print("=" * 60)


@test("Writer stores min_lot_width_ft")
def _():
    source = inspect.getsource(
        __import__("src.utils.supabase_writer", fromlist=["SupabaseWriter"]).SupabaseWriter._write_zone_standards
    )
    assert 'dims.get("min_lot_width_ft")' in source
    return True


@test("Writer stores min_lot_depth_ft")
def _():
    source = inspect.getsource(
        __import__("src.utils.supabase_writer", fromlist=["SupabaseWriter"]).SupabaseWriter._write_zone_standards
    )
    assert 'dims.get("min_lot_depth_ft")' in source
    return True


@test("All Gemini extraction fields are stored by writer")
def _():
    from src.parsers.gemini_parser import ZONING_DISTRICTS_PROMPT
    from src.utils.supabase_writer import SupabaseWriter

    # Parse Gemini prompt for expected dimensional fields
    prompt_fields = set(re.findall(r'"(min_\w+|max_\w+)":\s*null', ZONING_DISTRICTS_PROMPT))

    # Parse writer source for stored fields
    source = inspect.getsource(SupabaseWriter._write_zone_standards)
    writer_fields = set(re.findall(r'dims\.get\("(\w+)"', source))

    missing = prompt_fields - writer_fields
    assert not missing, f"Writer missing Gemini fields: {missing}"
    return True


@test("Writer actually passes width/depth values to Supabase")
def _():
    from src.utils.supabase_writer import SupabaseWriter

    captured_record = {}
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    def capture_upsert(data, **kwargs):
        captured_record.update(data)
        r = MagicMock()
        r.execute.return_value = MagicMock(data=[{"id": 1}])
        return r

    mock_table.upsert.side_effect = capture_upsert

    with patch("src.utils.supabase_writer.create_client", return_value=mock_client):
        writer = SupabaseWriter(url="https://test.supabase.co", key="test")

    dims = {
        "min_lot_sqft": 7500, "min_lot_width_ft": 75, "min_lot_depth_ft": 100,
        "max_height_ft": 35, "confidence": 0.9
    }
    writer._write_zone_standards(district_id=1, dims=dims, source="test")

    assert captured_record.get("min_lot_width_ft") == 75, f"Expected 75, got {captured_record.get('min_lot_width_ft')}"
    assert captured_record.get("min_lot_depth_ft") == 100, f"Expected 100, got {captured_record.get('min_lot_depth_ft')}"
    return True


# ═══════════════════════════════════════════════════════════════
# BUG 4: Circuit breaker in scrape_with_actions
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("BUG 4: Circuit breaker in scrape_with_actions")
print("=" * 60)


@test("scrape_with_actions increments consecutive_failures on HTTP error")
def _():
    source = inspect.getsource(
        __import__("src.scrapers.firecrawl_scraper", fromlist=["FirecrawlScraper"]).FirecrawlScraper.scrape_with_actions
    )
    assert "consecutive_failures += 1" in source, "Must increment consecutive_failures"
    return True


@test("scrape_with_actions calls _trip_circuit on threshold")
def _():
    source = inspect.getsource(
        __import__("src.scrapers.firecrawl_scraper", fromlist=["FirecrawlScraper"]).FirecrawlScraper.scrape_with_actions
    )
    assert "_trip_circuit" in source, "Must call _trip_circuit when threshold reached"
    return True


@test("scrape_with_actions exception path trips circuit breaker")
def _():
    source = inspect.getsource(
        __import__("src.scrapers.firecrawl_scraper", fromlist=["FirecrawlScraper"]).FirecrawlScraper.scrape_with_actions
    )
    # Find the except block and verify it has consecutive_failures
    except_blocks = source.split("except")
    assert len(except_blocks) >= 2, "Should have at least one except block"
    last_except = except_blocks[-1]
    assert "consecutive_failures" in last_except, "Exception handler must track consecutive_failures"
    return True


@test("Circuit breaker actually trips after max_failures action scrapes")
def _():
    from src.scrapers.firecrawl_scraper import FirecrawlScraper

    scraper = FirecrawlScraper(api_key="test")
    scraper.max_failures = 3

    # Simulate 3 consecutive failures via exception path
    for i in range(3):
        with patch("httpx.AsyncClient") as mock:
            mock.return_value.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock.return_value.__aexit__ = AsyncMock(return_value=False)
            result = asyncio.get_event_loop().run_until_complete(
                scraper.scrape_with_actions("https://test.com", [{"type": "click"}])
            )
            assert result.status == "error"

    assert scraper.consecutive_failures >= 3, f"Should have 3+ failures, got {scraper.consecutive_failures}"
    assert scraper._is_circuit_open(), "Circuit breaker should be OPEN after 3 failures"

    # Next call should be blocked by circuit breaker
    result = asyncio.get_event_loop().run_until_complete(
        scraper.scrape_with_actions("https://test.com", [{"type": "click"}])
    )
    assert "Circuit breaker" in result.error, f"Should be blocked, got: {result.error}"
    return True


# ═══════════════════════════════════════════════════════════════
# DATABASE VERIFICATION (via Supabase Management API)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("DATABASE: Production data integrity")
print("=" * 60)

import urllib.request

MGMT_TOKEN = ""
PROJECT_REF = "mocerqjnksmhcjzxrewo"


def run_sql(query):
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
        data=data,
        headers={"Authorization": f"Bearer {MGMT_TOKEN}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


@test("Zero duplicate permitted_uses in production")
def _():
    result = run_sql(
        "SELECT COUNT(*) as dupes FROM (SELECT zoning_district_id, use_description, use_type "
        "FROM permitted_uses GROUP BY zoning_district_id, use_description, use_type HAVING COUNT(*) > 1) sub"
    )
    dupes = result[0]["dupes"]
    assert dupes == 0, f"Found {dupes} duplicate groups"
    return True


@test("Unique constraint exists on permitted_uses")
def _():
    result = run_sql(
        "SELECT COUNT(*) as cnt FROM pg_indexes WHERE tablename = 'permitted_uses' "
        "AND indexname = 'idx_permitted_uses_unique'"
    )
    assert result[0]["cnt"] == 1, "Unique index missing"
    return True


@test("Zero orphaned permitted_uses rows")
def _():
    result = run_sql(
        "SELECT COUNT(*) as orphaned FROM permitted_uses pu "
        "WHERE NOT EXISTS (SELECT 1 FROM zoning_districts zd WHERE zd.id = pu.zoning_district_id)"
    )
    assert result[0]["orphaned"] == 0, f"Found {result[0]['orphaned']} orphans"
    return True


@test("Zero orphaned zone_standards rows")
def _():
    result = run_sql(
        "SELECT COUNT(*) as orphaned FROM zone_standards zs "
        "WHERE NOT EXISTS (SELECT 1 FROM zoning_districts zd WHERE zd.id = zs.zoning_district_id)"
    )
    assert result[0]["orphaned"] == 0, f"Found {result[0]['orphaned']} orphans"
    return True


@test("zone_standards table has min_lot_width_ft column")
def _():
    result = run_sql(
        "SELECT COUNT(*) as cnt FROM information_schema.columns "
        "WHERE table_name = 'zone_standards' AND column_name = 'min_lot_width_ft'"
    )
    assert result[0]["cnt"] == 1, "Column min_lot_width_ft missing"
    return True


@test("zone_standards table has min_lot_depth_ft column")
def _():
    result = run_sql(
        "SELECT COUNT(*) as cnt FROM information_schema.columns "
        "WHERE table_name = 'zone_standards' AND column_name = 'min_lot_depth_ft'"
    )
    assert result[0]["cnt"] == 1, "Column min_lot_depth_ft missing"
    return True


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL FIXES VERIFIED ✅")
else:
    print(f"⚠ {FAIL} TEST(S) FAILED — INVESTIGATE")
print("=" * 60)

sys.exit(1 if FAIL > 0 else 0)
