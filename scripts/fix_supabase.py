#!/usr/bin/env python3
"""
Phase 4: Fix production Supabase data.

Operations:
  1. Assess: Count duplicates, orphans, missing columns
  2. Deduplicate: Remove duplicate permitted_uses rows
  3. Clean orphans: Remove records with no parent district
  4. Add constraints: Unique index + foreign keys to prevent recurrence
  5. Verify: Confirm all data integrity checks pass

Usage:
  python3 scripts/fix_supabase.py
  python3 scripts/fix_supabase.py --assess-only
  python3 scripts/fix_supabase.py --skip-constraints
"""

import json
import urllib.request
import urllib.error
import os
import sys
import argparse


MGMT_TOKEN = os.getenv("SUPABASE_MGMT_TOKEN", "")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "mocerqjnksmhcjzxrewo")
API_BASE = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"


def run_sql(query):
    """Execute SQL via Supabase Management API."""
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        API_BASE,
        data=data,
        headers={
            "Authorization": f"Bearer {MGMT_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  SQL ERROR: {body[:200]}")
        return None


def assess():
    """Step 1: Assess current data quality."""
    print(f"\n{'=' * 60}")
    print(f"STEP 1: ASSESSMENT")
    print(f"{'=' * 60}")

    # Duplicates
    result = run_sql(
        "SELECT COUNT(*) as groups, COALESCE(SUM(cnt - 1), 0) as excess "
        "FROM (SELECT zoning_district_id, use_description, use_type, COUNT(*) as cnt "
        "FROM permitted_uses GROUP BY zoning_district_id, use_description, use_type "
        "HAVING COUNT(*) > 1) sub"
    )
    if result:
        dupes = result[0]
        print(f"  Duplicate groups: {dupes['groups']}")
        print(f"  Excess rows: {dupes['excess']}")

    # Orphans
    result = run_sql(
        "SELECT "
        "(SELECT COUNT(*) FROM permitted_uses WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)) as orphan_uses, "
        "(SELECT COUNT(*) FROM zone_standards WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)) as orphan_standards"
    )
    if result:
        print(f"  Orphaned permitted_uses: {result[0]['orphan_uses']}")
        print(f"  Orphaned zone_standards: {result[0]['orphan_standards']}")

    # Totals
    result = run_sql(
        "SELECT "
        "(SELECT COUNT(*) FROM zoning_districts) as districts, "
        "(SELECT COUNT(*) FROM zone_standards) as standards, "
        "(SELECT COUNT(*) FROM permitted_uses) as uses"
    )
    if result:
        print(f"  Total districts: {result[0]['districts']}")
        print(f"  Total standards: {result[0]['standards']}")
        print(f"  Total uses: {result[0]['uses']}")

    # Missing columns
    result = run_sql(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'zone_standards' AND column_name IN ('min_lot_width_ft', 'min_lot_depth_ft')"
    )
    if result:
        found = {r['column_name'] for r in result}
        missing = {'min_lot_width_ft', 'min_lot_depth_ft'} - found
        if missing:
            print(f"  Missing columns: {missing}")
        else:
            print(f"  All required columns present ✅")

    return result is not None


def deduplicate():
    """Step 2: Remove duplicate permitted_uses."""
    print(f"\n{'=' * 60}")
    print(f"STEP 2: DEDUPLICATE")
    print(f"{'=' * 60}")

    before = run_sql("SELECT COUNT(*) as total FROM permitted_uses")
    if before:
        print(f"  Before: {before[0]['total']} rows")

    run_sql(
        "DELETE FROM permitted_uses WHERE id NOT IN "
        "(SELECT MIN(id) FROM permitted_uses "
        "GROUP BY zoning_district_id, use_description, use_type)"
    )

    after = run_sql("SELECT COUNT(*) as total FROM permitted_uses")
    if after and before:
        deleted = before[0]['total'] - after[0]['total']
        print(f"  After: {after[0]['total']} rows")
        print(f"  Deleted: {deleted} duplicates ✅")


def clean_orphans():
    """Step 3: Remove orphaned records."""
    print(f"\n{'=' * 60}")
    print(f"STEP 3: CLEAN ORPHANS")
    print(f"{'=' * 60}")

    run_sql(
        "DELETE FROM permitted_uses WHERE zoning_district_id "
        "NOT IN (SELECT id FROM zoning_districts)"
    )
    run_sql(
        "DELETE FROM zone_standards WHERE zoning_district_id "
        "NOT IN (SELECT id FROM zoning_districts)"
    )

    result = run_sql(
        "SELECT "
        "(SELECT COUNT(*) FROM permitted_uses WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)) as uses, "
        "(SELECT COUNT(*) FROM zone_standards WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)) as standards"
    )
    if result:
        print(f"  Remaining orphan uses: {result[0]['uses']}")
        print(f"  Remaining orphan standards: {result[0]['standards']}")
        if result[0]['uses'] == 0 and result[0]['standards'] == 0:
            print(f"  All orphans cleaned ✅")


def add_constraints():
    """Step 4: Add DB constraints to prevent recurrence."""
    print(f"\n{'=' * 60}")
    print(f"STEP 4: ADD CONSTRAINTS")
    print(f"{'=' * 60}")

    # Unique index
    run_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_permitted_uses_unique "
        "ON permitted_uses (zoning_district_id, use_description, use_type)"
    )
    print(f"  Unique index: created ✅")

    # Foreign keys
    run_sql("ALTER TABLE permitted_uses DROP CONSTRAINT IF EXISTS fk_permitted_uses_district")
    run_sql(
        "ALTER TABLE permitted_uses ADD CONSTRAINT fk_permitted_uses_district "
        "FOREIGN KEY (zoning_district_id) REFERENCES zoning_districts(id) ON DELETE CASCADE"
    )
    print(f"  FK permitted_uses → zoning_districts: created ✅")

    run_sql("ALTER TABLE zone_standards DROP CONSTRAINT IF EXISTS fk_zone_standards_district")
    run_sql(
        "ALTER TABLE zone_standards ADD CONSTRAINT fk_zone_standards_district "
        "FOREIGN KEY (zoning_district_id) REFERENCES zoning_districts(id) ON DELETE CASCADE"
    )
    print(f"  FK zone_standards → zoning_districts: created ✅")

    # Add missing columns if needed
    run_sql("ALTER TABLE zone_standards ADD COLUMN IF NOT EXISTS min_lot_width_ft NUMERIC")
    run_sql("ALTER TABLE zone_standards ADD COLUMN IF NOT EXISTS min_lot_depth_ft NUMERIC")
    print(f"  Columns min_lot_width_ft, min_lot_depth_ft: ensured ✅")


def verify():
    """Step 5: Final verification."""
    print(f"\n{'=' * 60}")
    print(f"STEP 5: VERIFICATION")
    print(f"{'=' * 60}")

    checks = {
        "Zero duplicates": (
            "SELECT COUNT(*) as cnt FROM (SELECT zoning_district_id, use_description, use_type "
            "FROM permitted_uses GROUP BY zoning_district_id, use_description, use_type HAVING COUNT(*) > 1) sub",
            lambda r: r[0]['cnt'] == 0
        ),
        "Zero orphan uses": (
            "SELECT COUNT(*) as cnt FROM permitted_uses WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)",
            lambda r: r[0]['cnt'] == 0
        ),
        "Zero orphan standards": (
            "SELECT COUNT(*) as cnt FROM zone_standards WHERE zoning_district_id NOT IN (SELECT id FROM zoning_districts)",
            lambda r: r[0]['cnt'] == 0
        ),
        "Unique index exists": (
            "SELECT COUNT(*) as cnt FROM pg_indexes WHERE tablename = 'permitted_uses' AND indexname = 'idx_permitted_uses_unique'",
            lambda r: r[0]['cnt'] == 1
        ),
        "FK constraints exist": (
            "SELECT COUNT(*) as cnt FROM information_schema.table_constraints "
            "WHERE constraint_type = 'FOREIGN KEY' AND table_name IN ('permitted_uses', 'zone_standards')",
            lambda r: r[0]['cnt'] >= 2
        ),
        "Width column exists": (
            "SELECT COUNT(*) as cnt FROM information_schema.columns WHERE table_name = 'zone_standards' AND column_name = 'min_lot_width_ft'",
            lambda r: r[0]['cnt'] == 1
        ),
        "Depth column exists": (
            "SELECT COUNT(*) as cnt FROM information_schema.columns WHERE table_name = 'zone_standards' AND column_name = 'min_lot_depth_ft'",
            lambda r: r[0]['cnt'] == 1
        ),
    }

    passed = 0
    failed = 0
    for name, (query, check) in checks.items():
        result = run_sql(query)
        if result and check(result):
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    print(f"\n  Results: {passed}/{passed + failed} passed")
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix production Supabase data")
    parser.add_argument("--assess-only", action="store_true", help="Only assess, don't fix")
    parser.add_argument("--skip-constraints", action="store_true", help="Skip adding constraints")
    args = parser.parse_args()

    print(f"\n{'═' * 60}")
    print(f"  SUPABASE DATA FIX PIPELINE")
    print(f"  Project: {PROJECT_REF}")
    print(f"{'═' * 60}")

    assess()

    if args.assess_only:
        sys.exit(0)

    deduplicate()
    clean_orphans()

    if not args.skip_constraints:
        add_constraints()

    success = verify()
    sys.exit(0 if success else 1)
