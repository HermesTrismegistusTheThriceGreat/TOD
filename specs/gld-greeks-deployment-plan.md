# GLD Options Greeks Snapshots - Deployment Plan

**Created**: 2025-01-16
**Feature**: GLD Options Greeks Snapshots
**Status**: Ready for Deployment
**References**:
- Implementation Plan: `/specs/gld-greeks-snapshots-plan.md`
- Code Review: `/app_review/review_gld-greeks-snapshots-20250116.md`
- Migration: `/apps/orchestrator_db/migrations/12_option_greeks_snapshots.sql`
- Service: `/apps/orchestrator_3_stream/backend/modules/greeks_snapshot_service.py`
- Scheduler: `/apps/orchestrator_3_stream/backend/modules/greeks_scheduler.py`

---

## Executive Summary

This plan covers the safe deployment of the GLD Options Greeks Snapshots feature, including:
1. Database migration execution against Neon PostgreSQL
2. Schema and index verification
3. REST endpoint testing
4. Scheduler configuration verification
5. End-to-end data integrity checks

**Pre-Deployment Status**:
- [x] SQL migration file created
- [x] Pydantic model added to models.py
- [x] Models synced to backend
- [x] Service layer implemented
- [x] Scheduler module implemented
- [x] REST endpoints added to main.py
- [x] SQL injection vulnerability fixed (uses `make_interval()`)
- [ ] **Migration executed** (this plan)
- [ ] **Testing completed** (this plan)

---

## Phase 1: Database Migration Execution

### 1.1 Pre-Migration Checklist

| Step | Command/Action | Expected Result |
|------|----------------|-----------------|
| 1 | Verify `.env` file exists | `DATABASE_URL` is set |
| 2 | Test database connectivity | Connection successful |
| 3 | Backup current state (optional) | Snapshot created |
| 4 | Verify migration file syntax | SQL parses without errors |

**Verify Environment**:
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

# Check .env exists and has DATABASE_URL
cat .env | grep DATABASE_URL
```

**Test Database Connectivity**:
```bash
uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        version = await conn.fetchval('SELECT version()')
        print(f'✓ Connected to PostgreSQL')
        print(f'  Version: {version[:50]}...')
        await conn.close()
        return True
    except Exception as e:
        print(f'✗ Connection failed: {e}')
        return False

asyncio.run(test_connection())
"
```

### 1.2 Execute Migration

**Run the Migration**:
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    print('Starting migration: 12_option_greeks_snapshots.sql')
    print('=' * 60)

    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    try:
        # Read and execute migration
        with open('migrations/12_option_greeks_snapshots.sql', 'r') as f:
            migration_sql = f.read()

        await conn.execute(migration_sql)
        print('✓ Migration executed successfully!')

    except Exception as e:
        print(f'✗ Migration failed: {e}')
        raise
    finally:
        await conn.close()

asyncio.run(run_migration())
"
```

**Expected Output**:
```
Starting migration: 12_option_greeks_snapshots.sql
============================================================
✓ Migration executed successfully!
```

### 1.3 Migration Rollback Plan

If the migration fails or needs to be reverted:

```sql
-- ROLLBACK SCRIPT (run manually if needed)
-- WARNING: This will DROP the table and all data

DROP TABLE IF EXISTS option_greeks_snapshots CASCADE;

-- Verify table is dropped
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'option_greeks_snapshots'
);
-- Expected: false
```

**Execute Rollback**:
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def rollback_migration():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    try:
        await conn.execute('DROP TABLE IF EXISTS option_greeks_snapshots CASCADE')
        print('✓ Rollback complete: Table dropped')
    finally:
        await conn.close()

# UNCOMMENT TO RUN:
# asyncio.run(rollback_migration())
print('Rollback script loaded but not executed. Uncomment to run.')
"
```

---

## Phase 2: Schema Validation

### 2.1 Verify Table Exists

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_table():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    result = await conn.fetchval('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'option_greeks_snapshots'
        )
    ''')

    print(f'Table exists: {result}')
    assert result == True, 'Table does not exist!'
    print('✓ PASS: Table option_greeks_snapshots exists')

    await conn.close()

asyncio.run(check_table())
"
```

### 2.2 Verify Column Schema

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

EXPECTED_COLUMNS = {
    'id': 'uuid',
    'snapshot_at': 'timestamp with time zone',
    'snapshot_type': 'text',
    'symbol': 'text',
    'underlying': 'text',
    'expiry_date': 'date',
    'strike_price': 'numeric',
    'option_type': 'text',
    'delta': 'numeric',
    'gamma': 'numeric',
    'theta': 'numeric',
    'vega': 'numeric',
    'rho': 'numeric',
    'implied_volatility': 'numeric',
    'underlying_price': 'numeric',
    'bid_price': 'numeric',
    'ask_price': 'numeric',
    'mid_price': 'numeric',
    'last_trade_price': 'numeric',
    'volume': 'integer',
    'open_interest': 'integer',
    'raw_data': 'jsonb',
    'created_at': 'timestamp with time zone'
}

async def check_columns():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    rows = await conn.fetch('''
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'option_greeks_snapshots'
        ORDER BY ordinal_position
    ''')

    print(f'Found {len(rows)} columns:')
    print('-' * 50)

    errors = []
    for row in rows:
        col_name = row['column_name']
        col_type = row['data_type']
        expected_type = EXPECTED_COLUMNS.get(col_name)

        status = '✓' if col_type == expected_type else '✗'
        print(f'  {status} {col_name}: {col_type}')

        if expected_type and col_type != expected_type:
            errors.append(f'{col_name}: expected {expected_type}, got {col_type}')

    # Check for missing columns
    found_cols = {row['column_name'] for row in rows}
    for expected_col in EXPECTED_COLUMNS:
        if expected_col not in found_cols:
            errors.append(f'Missing column: {expected_col}')

    print('-' * 50)
    if errors:
        print('ERRORS:')
        for e in errors:
            print(f'  ✗ {e}')
        assert False, 'Schema mismatch!'
    else:
        print(f'✓ PASS: All {len(EXPECTED_COLUMNS)} columns present with correct types')

    await conn.close()

asyncio.run(check_columns())
"
```

### 2.3 Verify Indexes

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

EXPECTED_INDEXES = [
    'idx_greeks_snapshot_at',
    'idx_greeks_underlying',
    'idx_greeks_symbol',
    'idx_greeks_expiry',
    'idx_greeks_type',
    'idx_greeks_underlying_expiry',
    'idx_greeks_symbol_snapshot',
    'idx_greeks_underlying_snapshot_type',
    'unique_greeks_snapshot',  # Unique constraint
]

async def check_indexes():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    rows = await conn.fetch('''
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'option_greeks_snapshots'
    ''')

    found_indexes = {row['indexname'] for row in rows}

    print(f'Found {len(found_indexes)} indexes:')
    print('-' * 50)

    errors = []
    for idx in EXPECTED_INDEXES:
        if idx in found_indexes:
            print(f'  ✓ {idx}')
        else:
            print(f'  ✗ {idx} MISSING')
            errors.append(idx)

    # Show any extra indexes
    extra = found_indexes - set(EXPECTED_INDEXES) - {'option_greeks_snapshots_pkey'}
    if extra:
        print(f'  Extra indexes: {extra}')

    print('-' * 50)
    if errors:
        print(f'ERRORS: Missing {len(errors)} indexes')
        assert False, f'Missing indexes: {errors}'
    else:
        print(f'✓ PASS: All {len(EXPECTED_INDEXES)} indexes present')

    await conn.close()

asyncio.run(check_indexes())
"
```

### 2.4 Verify Constraints

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_constraints():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    # Check constraints
    rows = await conn.fetch('''
        SELECT conname, contype, pg_get_constraintdef(oid) as definition
        FROM pg_constraint
        WHERE conrelid = 'option_greeks_snapshots'::regclass
    ''')

    print('Constraints:')
    print('-' * 60)
    for row in rows:
        print(f'  {row[\"conname\"]} ({row[\"contype\"]}): {row[\"definition\"][:60]}...')

    # Verify unique constraint exists
    unique_exists = any(r['conname'] == 'unique_greeks_snapshot' for r in rows)
    assert unique_exists, 'Unique constraint missing!'
    print('-' * 60)
    print('✓ PASS: Unique constraint (symbol, snapshot_at) exists')

    # Verify check constraints for snapshot_type and option_type
    check_constraints = [r for r in rows if r['contype'] == 'c']
    print(f'✓ PASS: {len(check_constraints)} check constraints found')

    await conn.close()

asyncio.run(check_constraints())
"
```

---

## Phase 3: Service Verification

### 3.1 Verify Imports

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend

# Test service import
uv run python -c "
from modules.greeks_snapshot_service import GreeksSnapshotService, init_greeks_snapshot_service, get_greeks_snapshot_service
print('✓ greeks_snapshot_service imports OK')
"

# Test scheduler import
uv run python -c "
from modules.greeks_scheduler import init_greeks_scheduler, shutdown_greeks_scheduler
print('✓ greeks_scheduler imports OK')
"

# Test model import
uv run python -c "
from modules.orch_database_models import OptionGreeksSnapshot
print('✓ OptionGreeksSnapshot model imports OK')
"
```

### 3.2 Verify Service Configuration

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend

uv run python -c "
from modules.greeks_snapshot_service import GreeksSnapshotService
from modules.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, DATABASE_URL

print('Configuration Check:')
print('-' * 40)
print(f'  ALPACA_API_KEY: {\"SET\" if ALPACA_API_KEY else \"NOT SET\"}')
print(f'  ALPACA_SECRET_KEY: {\"SET\" if ALPACA_SECRET_KEY else \"NOT SET\"}')
print(f'  DATABASE_URL: {\"SET\" if DATABASE_URL else \"NOT SET\"}')
print('-' * 40)

service = GreeksSnapshotService()
print(f'  Service is_configured: {service.is_configured}')

if service.is_configured:
    print('✓ PASS: Service properly configured')
else:
    print('⚠ WARNING: Alpaca not configured - snapshots will be disabled')
"
```

---

## Phase 4: REST Endpoint Testing

### 4.1 Prerequisites

Ensure the backend is running:
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run uvicorn main:app --reload --port 8000
```

Or use the start-orchestrator skill to run in background mode.

### 4.2 Test Manual Snapshot Trigger

**Endpoint**: `POST /api/greeks/snapshot`

```bash
# Trigger manual snapshot for GLD
curl -X POST "http://localhost:8000/api/greeks/snapshot?underlying=GLD" \
  -H "Content-Type: application/json"
```

**Expected Response** (success):
```json
{
  "status": "success",
  "underlying": "GLD",
  "snapshot_type": "manual",
  "records_persisted": 500,
  "timestamp": "2025-01-16T15:30:00Z"
}
```

**Expected Response** (Alpaca not configured):
```json
{
  "status": "skipped",
  "reason": "Alpaca not configured",
  "records_persisted": 0
}
```

**Validation Criteria**:
- [ ] HTTP 200 response
- [ ] `status` is "success" or "skipped"
- [ ] `records_persisted` >= 0
- [ ] If Alpaca is configured, records > 0 expected

### 4.3 Test Latest Snapshots Query

**Endpoint**: `GET /api/greeks/latest`

```bash
# Get latest snapshots (default limit 100)
curl -X GET "http://localhost:8000/api/greeks/latest?underlying=GLD&limit=10"
```

**Expected Response**:
```json
{
  "status": "success",
  "underlying": "GLD",
  "count": 10,
  "snapshots": [
    {
      "id": "uuid...",
      "snapshot_at": "2025-01-16T15:30:00Z",
      "snapshot_type": "manual",
      "symbol": "GLD260117C00200000",
      "underlying": "GLD",
      "expiry_date": "2026-01-17",
      "strike_price": 200.0,
      "option_type": "call",
      "delta": 0.523456,
      "gamma": 0.012345,
      "theta": -0.05678,
      "vega": 0.234567,
      "rho": 0.123456,
      "implied_volatility": 0.15678,
      "bid_price": 5.25,
      "ask_price": 5.35,
      "mid_price": 5.30,
      "last_trade_price": 5.28
    }
  ]
}
```

**Validation Criteria**:
- [ ] HTTP 200 response
- [ ] `count` matches actual array length
- [ ] Each snapshot has required fields
- [ ] Greeks values are present (if data exists)

### 4.4 Test History Query

**Endpoint**: `GET /api/greeks/history/{symbol}`

```bash
# Get history for specific option (use a real symbol from latest query)
curl -X GET "http://localhost:8000/api/greeks/history/GLD260117C00200000?days=7"
```

**Expected Response**:
```json
{
  "status": "success",
  "symbol": "GLD260117C00200000",
  "days": 7,
  "count": 21,
  "history": [
    {
      "snapshot_at": "2025-01-10T13:00:00Z",
      "delta": 0.51234,
      ...
    }
  ]
}
```

**Validation Criteria**:
- [ ] HTTP 200 response
- [ ] History sorted by `snapshot_at` ASC
- [ ] Only data within specified `days` range
- [ ] Count matches array length

---

## Phase 5: Scheduler Verification

### 5.1 Verify Scheduler Jobs

After starting the backend, check scheduler status in logs:

```bash
# Look for scheduler initialization in logs
grep -i "Greeks scheduler" /path/to/logs

# Expected log entries:
# Greeks scheduler started (3 daily jobs scheduled)
```

**Programmatic Verification**:
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend

uv run python -c "
from modules.greeks_scheduler import init_greeks_scheduler, shutdown_greeks_scheduler, _scheduler
from unittest.mock import MagicMock

# Create mock app
app = MagicMock()
app.state = MagicMock()

# Initialize scheduler
scheduler = init_greeks_scheduler(app)

print('Scheduled Jobs:')
print('-' * 60)
for job in scheduler.get_jobs():
    print(f'  ID: {job.id}')
    print(f'  Name: {job.name}')
    print(f'  Trigger: {job.trigger}')
    print(f'  Next run: {job.next_run_time}')
    print()

# Verify 3 jobs exist
jobs = scheduler.get_jobs()
assert len(jobs) == 3, f'Expected 3 jobs, found {len(jobs)}'

# Verify job IDs
job_ids = {j.id for j in jobs}
expected_ids = {'greeks_london_session', 'greeks_us_session', 'greeks_asian_session'}
assert job_ids == expected_ids, f'Job IDs mismatch: {job_ids}'

print('✓ PASS: All 3 scheduler jobs configured correctly')

# Cleanup
shutdown_greeks_scheduler()
"
```

### 5.2 Verify Schedule Times

| Session | Schedule (ET) | CronTrigger |
|---------|--------------|-------------|
| London | 8:00 AM | `hour=8, minute=0` |
| US | 2:00 PM | `hour=14, minute=0` |
| Asian | 9:30 PM | `hour=21, minute=30` |

**Check Next Run Times** (already covered in 5.1 script above).

---

## Phase 6: Data Integrity Verification

### 6.1 Verify Data After Snapshot

After running a manual snapshot, verify data integrity:

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db

uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_data():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    # Count records
    count = await conn.fetchval('SELECT COUNT(*) FROM option_greeks_snapshots')
    print(f'Total records: {count}')

    if count == 0:
        print('⚠ No data yet - run manual snapshot first')
        await conn.close()
        return

    # Check data distribution
    print()
    print('Snapshot Type Distribution:')
    rows = await conn.fetch('''
        SELECT snapshot_type, COUNT(*) as count
        FROM option_greeks_snapshots
        GROUP BY snapshot_type
        ORDER BY count DESC
    ''')
    for row in rows:
        print(f'  {row[\"snapshot_type\"]}: {row[\"count\"]}')

    # Check option type distribution
    print()
    print('Option Type Distribution:')
    rows = await conn.fetch('''
        SELECT option_type, COUNT(*) as count
        FROM option_greeks_snapshots
        GROUP BY option_type
    ''')
    for row in rows:
        print(f'  {row[\"option_type\"]}: {row[\"count\"]}')

    # Check Greeks population (non-null)
    print()
    print('Greeks Population (% non-null):')
    for col in ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility']:
        non_null = await conn.fetchval(f'''
            SELECT ROUND(
                COUNT({col})::numeric / COUNT(*)::numeric * 100, 1
            )
            FROM option_greeks_snapshots
        ''')
        print(f'  {col}: {non_null}%')

    # Sample record
    print()
    print('Sample Record:')
    row = await conn.fetchrow('''
        SELECT symbol, expiry_date, strike_price, option_type, delta, theta, implied_volatility
        FROM option_greeks_snapshots
        LIMIT 1
    ''')
    if row:
        print(f'  Symbol: {row[\"symbol\"]}')
        print(f'  Expiry: {row[\"expiry_date\"]}')
        print(f'  Strike: {row[\"strike_price\"]}')
        print(f'  Type: {row[\"option_type\"]}')
        print(f'  Delta: {row[\"delta\"]}')
        print(f'  Theta: {row[\"theta\"]}')
        print(f'  IV: {row[\"implied_volatility\"]}')

    print()
    print('✓ PASS: Data integrity check complete')

    await conn.close()

asyncio.run(verify_data())
"
```

### 6.2 Verify Upsert Logic

Test that duplicate snapshots update rather than error:

```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend

# Run manual snapshot twice - second should update, not duplicate
curl -X POST "http://localhost:8000/api/greeks/snapshot?underlying=GLD"
# Note the record count

# Wait a moment, then run again
sleep 2
curl -X POST "http://localhost:8000/api/greeks/snapshot?underlying=GLD"
# Record count should be similar (updates, not duplicates)
```

---

## Phase 7: Deployment Checklist

### 7.1 Pre-Deployment Checklist

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | `.env` file has DATABASE_URL | [ ] | Required |
| 2 | `.env` file has ALPACA_API_KEY | [ ] | Required for data |
| 3 | `.env` file has ALPACA_SECRET_KEY | [ ] | Required for data |
| 4 | Migration file created | [x] | `12_option_greeks_snapshots.sql` |
| 5 | Migration executed successfully | [ ] | Run Phase 1.2 |
| 6 | Table exists | [ ] | Run Phase 2.1 |
| 7 | All columns present | [ ] | Run Phase 2.2 |
| 8 | All indexes created | [ ] | Run Phase 2.3 |
| 9 | Service imports work | [ ] | Run Phase 3.1 |
| 10 | Scheduler jobs configured | [ ] | Run Phase 5.1 |

### 7.2 Post-Deployment Verification

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Manual snapshot returns 200 | [ ] | Phase 4.2 |
| 2 | Latest query returns data | [ ] | Phase 4.3 |
| 3 | History query works | [ ] | Phase 4.4 |
| 4 | Data has Greeks populated | [ ] | Phase 6.1 |
| 5 | Scheduler running | [ ] | Check logs |

### 7.3 Environment Variables Required

```bash
# Required in .env
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
```

---

## Troubleshooting

### Common Issues

**1. Migration fails with "table already exists"**
- The migration uses `CREATE TABLE IF NOT EXISTS`, so this shouldn't happen
- If indexes fail, they also use `IF NOT EXISTS`

**2. "Alpaca not configured" in logs**
- Check `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`
- Ensure `.env` is in the correct directory

**3. "GreeksSnapshotService not initialized"**
- Service must be initialized in FastAPI lifespan
- Check `main.py` includes `init_greeks_snapshot_service(app)`

**4. Empty snapshots returned**
- Market may be closed
- Alpaca Elite subscription required for OPRA feed
- Check Alpaca API status

**5. Scheduler jobs not running**
- Check if scheduler is initialized: look for "Greeks scheduler started" in logs
- Verify APScheduler is installed: `uv pip list | grep APScheduler`

---

## Acceptance Criteria

All items must pass before deployment is considered complete:

- [ ] **Database table exists** - `option_greeks_snapshots` table created with all columns
- [ ] **Indexes created** - All 8 indexes + unique constraint present
- [ ] **Manual trigger works** - POST `/api/greeks/snapshot` returns 200 and persists data
- [ ] **Query endpoints work** - GET `/api/greeks/latest` and `/api/greeks/history/{symbol}` return data
- [ ] **Scheduler configured** - 3 jobs scheduled for 8:00 AM, 2:00 PM, 9:30 PM ET
- [ ] **Greeks populated** - Delta, gamma, theta, vega, rho, IV have values in persisted data
- [ ] **Upsert works** - Duplicate snapshots update records instead of creating duplicates

---

## Quick Reference Commands

```bash
# Run migration
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db
uv run python -c "import asyncio; import asyncpg; import os; from dotenv import load_dotenv; load_dotenv(); asyncio.run((lambda: asyncpg.connect(os.getenv('DATABASE_URL')).execute(open('migrations/12_option_greeks_snapshots.sql').read()))())"

# Verify table exists
uv run python -c "import asyncio; import asyncpg; import os; from dotenv import load_dotenv; load_dotenv(); print(asyncio.run(asyncpg.connect(os.getenv('DATABASE_URL')).fetchval(\"SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name='option_greeks_snapshots')\")))"

# Test imports
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run python -c "from modules.greeks_snapshot_service import GreeksSnapshotService; print('OK')"

# Manual snapshot (backend must be running)
curl -X POST "http://localhost:8000/api/greeks/snapshot?underlying=GLD"

# Query latest
curl "http://localhost:8000/api/greeks/latest?underlying=GLD&limit=5"
```

---

**Plan Created**: 2025-01-16
**Author**: Planning Agent
**Review Status**: Ready for execution
