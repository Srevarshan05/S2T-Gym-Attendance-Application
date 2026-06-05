"""
app/services/dashboard_service.py
───────────────────────────────────
Admin Dashboard aggregation service.

SINGLE CTE DESIGN — all KPIs fetched in ONE database round-trip.

Why one CTE instead of multiple queries?
  The admin dashboard is the most frequently hit admin endpoint.
  Multiple sequential queries (N+1 style) would be 5-7 DB round-trips
  per page load. A single CTE:
    - Reduces latency by eliminating round-trip overhead.
    - Lets PostgreSQL plan all sub-queries in one pass — partial index
      scans for attendance, member_status filters, etc., are all
      optimised together.
    - Prevents stale data skew — all metrics are from the exact same
      DB snapshot (same transaction, same MVCC visibility).

CTE structure:
  1. member_stats   — COUNT(*) FILTER on membership_status variants
  2. today_att      — FN/AN counts + unique members for IST today
  3. pending_pay    — COUNT of PENDING_APPROVAL payment requests
  4. monthly_rev    — SUM from revenue_logs for current IST month_bucket
  5. expiring_rows  — ACTIVE members expiring within 7 days (IST)
  6. expiring_agg   — json_agg of expiring_rows INTO a JSON array
                      (aggregated inside CTE per Phase 2 feedback —
                       prevents cartesian product when joined to totals)
  Final SELECT:
    CROSS JOIN all scalar CTEs (each returns exactly one row) +
    CROSS JOIN expiring_agg (one JSON array column).

IST timezone:
  All date comparisons use (NOW() AT TIME ZONE 'Asia/Kolkata')::date
  to get the IST calendar date, matching the attendance service behaviour.

Empty-state handling:
  - COUNT()         → always returns 0, never NULL
  - COALESCE(SUM, 0) → revenue returns 0.00 when no approvals this month
  - COALESCE(json_agg, '[]') → expiring_soon returns [] when empty
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import DashboardOverviewResponse, ExpiringMemberItem

# ── The Dashboard CTE ──────────────────────────────────────────────────────

_DASHBOARD_CTE = text("""
WITH

-- ── 1. Membership status breakdown ───────────────────────────────────────
-- Joins users + members_profile.
-- FILTER (WHERE ...) is a PostgreSQL aggregate filter — one pass, zero sub-SELECTs.
-- Uses the partial index idx_members_profile_active_status (defined in migration).
member_stats AS (
    SELECT
        COUNT(*)                                                   AS total_members,
        COUNT(*) FILTER (WHERE mp.membership_status = 'ACTIVE')    AS active_count,
        COUNT(*) FILTER (WHERE mp.membership_status = 'EXPIRED')   AS expired_count,
        COUNT(*) FILTER (WHERE mp.membership_status = 'PENDING')   AS pending_count,
        COUNT(*) FILTER (WHERE mp.membership_status = 'SUSPENDED') AS suspended_count
    FROM users u
    JOIN members_profile mp ON mp.user_id = u.id
    WHERE u.role = 'member'
      AND u.is_active = TRUE
),

-- ── 2. Today's attendance (IST date) ─────────────────────────────────────
-- Uses idx_attendance_logs_date (BTREE on attendance_date).
-- (NOW() AT TIME ZONE 'Asia/Kolkata')::date is the IST calendar date.
-- Matches attendance_service._get_gym_date() exactly.
today_att AS (
    SELECT
        COUNT(*) FILTER (WHERE session = 'FN')  AS fn_count,
        COUNT(*) FILTER (WHERE session = 'AN')  AS an_count,
        COUNT(*)                                AS total_checkins,
        COUNT(DISTINCT user_id)                 AS unique_members
    FROM attendance_logs
    WHERE attendance_date = (NOW() AT TIME ZONE 'Asia/Kolkata')::date
),

-- ── 3. Pending payment requests ───────────────────────────────────────────
-- Uses partial index: idx_payment_requests_pending (WHERE status = 'PENDING_APPROVAL').
-- Single index scan — no table scan needed.
pending_pay AS (
    SELECT COUNT(*) AS count
    FROM payment_requests
    WHERE status = 'PENDING_APPROVAL'
),

-- ── 4. Monthly revenue (current IST month) ───────────────────────────────
-- Uses idx_revenue_logs_month_bucket (BTREE on month_bucket).
-- month_bucket is a stored 'YYYY-MM' string, so equality lookup is instant.
-- TO_CHAR with 'Asia/Kolkata' matches how month_bucket was stored at approval.
monthly_rev AS (
    SELECT
        COALESCE(SUM(amount), 0::numeric)                            AS total,
        TO_CHAR(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM')        AS bucket,
        TO_CHAR(NOW() AT TIME ZONE 'Asia/Kolkata', 'Month YYYY')     AS label
    FROM revenue_logs
    WHERE month_bucket = TO_CHAR(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM')
),

-- ── 5. Members expiring in the next 7 days ───────────────────────────────
-- Only ACTIVE members. Ordered by expiry date (most urgent first).
-- Uses the same partial membership_status filter + date range on indexed column.
expiring_rows AS (
    SELECT
        u.member_id,
        mp.full_name,
        gp.name                                                        AS plan_name,
        mp.membership_end_date,
        (mp.membership_end_date
            - (NOW() AT TIME ZONE 'Asia/Kolkata')::date)               AS days_remaining
    FROM users u
    JOIN members_profile mp ON mp.user_id = u.id
    JOIN gym_plans gp        ON gp.id = mp.plan_id
    WHERE u.role          = 'member'
      AND u.is_active     = TRUE
      AND mp.membership_status = 'ACTIVE'
      AND mp.membership_end_date BETWEEN
            (NOW() AT TIME ZONE 'Asia/Kolkata')::date
        AND (NOW() AT TIME ZONE 'Asia/Kolkata')::date + INTERVAL '7 days'
    ORDER BY mp.membership_end_date ASC
),

-- ── 6. Aggregate expiring list into a single JSON array ──────────────────
-- Aggregated INSIDE its own CTE before the final CROSS JOIN.
-- This prevents a cartesian product (noted in Phase 2 feedback):
--   If expiring_rows had 3 rows and we CROSS JOINed it with the 1-row
--   totals CTEs, we'd get 3 result rows. Aggregating here ensures
--   expiring_agg always returns exactly ONE row with a JSON array column.
-- COALESCE(..., '[]'::json) ensures empty result → [] not null.
expiring_agg AS (
    SELECT
        COALESCE(
            json_agg(row_to_json(er.*) ORDER BY er.membership_end_date ASC),
            '[]'::json
        ) AS expiring_soon
    FROM expiring_rows er
)

-- ── Final SELECT: one row, all metrics ────────────────────────────────────
-- CROSS JOIN scalar CTEs (each exactly 1 row) — no cartesian product risk.
SELECT
    ms.total_members,
    ms.active_count,
    ms.expired_count,
    ms.pending_count,
    ms.suspended_count,
    ta.fn_count,
    ta.an_count,
    ta.total_checkins,
    ta.unique_members,
    pp.count            AS pending_payments_count,
    mr.total            AS monthly_revenue,
    mr.label            AS month_label,
    ea.expiring_soon
FROM member_stats   ms
CROSS JOIN today_att     ta
CROSS JOIN pending_pay   pp
CROSS JOIN monthly_rev   mr
CROSS JOIN expiring_agg  ea
""")


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_expiring_item(item: dict) -> ExpiringMemberItem:
    """
    Parse a single dict from the JSON array into an ExpiringMemberItem schema.

    PostgreSQL's row_to_json serializes:
      - `date` columns   → ISO-8601 string "YYYY-MM-DD"
      - `integer` result → Python int (asyncpg deserialises JSON numbers)
      - `text` columns   → Python str

    We convert the date string back to a Python date object using
    date.fromisoformat() which handles "YYYY-MM-DD" natively.
    """
    raw_date = item["membership_end_date"]
    if isinstance(raw_date, str):
        end_date = date.fromisoformat(raw_date)
    else:
        end_date = raw_date  # asyncpg may already deserialise to date in some drivers

    return ExpiringMemberItem(
        member_id=item["member_id"],
        full_name=item["full_name"],
        plan_name=item["plan_name"],
        membership_end_date=end_date,
        days_remaining=int(item["days_remaining"]),
    )


def _clean_month_label(raw_label: str) -> str:
    """
    PostgreSQL TO_CHAR 'Month YYYY' pads month names with spaces:
    e.g., 'June      2026'. Strip internal padding for clean display.
    """
    parts = raw_label.strip().split()
    return " ".join(parts)  # e.g., "June 2026"


# ── Public Service Function ────────────────────────────────────────────────

async def get_overview(db: AsyncSession) -> DashboardOverviewResponse:
    """
    Fetch all Admin Dashboard KPIs in a single CTE round-trip.

    Returns a fully populated DashboardOverviewResponse schema.
    All fields default to 0 / [] if the database is empty.

    Performance profile (expected on Supabase PostgreSQL):
      - member_stats   → index scan on (role, is_active) + members_profile join
      - today_att      → BTREE range scan on attendance_date index
      - pending_pay    → partial index scan (status = 'PENDING_APPROVAL')
      - monthly_rev    → BTREE equality scan on month_bucket
      - expiring_rows  → composite index on (status, end_date) range
      Total: ~10-30ms on a warm Supabase instance.
    """
    result = await db.execute(_DASHBOARD_CTE)
    row = result.one_or_none()

    # Empty database edge case — return all-zero schema
    if row is None:
        return DashboardOverviewResponse(
            generated_at=datetime.now(timezone.utc),
            current_month_label=datetime.now(timezone.utc).strftime("%B %Y"),
        )

    # ── Parse the expiring_soon JSON array ─────────────────────────────────
    raw_expiring = row.expiring_soon
    if raw_expiring is None or raw_expiring == [] or raw_expiring == "[]":
        expiring_items: list[ExpiringMemberItem] = []
    else:
        # asyncpg deserialises json columns to Python list of dicts
        expiring_items = [_parse_expiring_item(item) for item in raw_expiring]

    # ── Build response ─────────────────────────────────────────────────────
    return DashboardOverviewResponse(
        # Membership
        total_members=int(row.total_members or 0),
        active_members=int(row.active_count or 0),
        expired_members=int(row.expired_count or 0),
        pending_members=int(row.pending_count or 0),
        suspended_members=int(row.suspended_count or 0),
        # Today's attendance
        today_fn_count=int(row.fn_count or 0),
        today_an_count=int(row.an_count or 0),
        today_total_checkins=int(row.total_checkins or 0),
        today_unique_members=int(row.unique_members or 0),
        # Payments
        pending_payments_count=int(row.pending_payments_count or 0),
        # Revenue
        monthly_revenue=Decimal(str(row.monthly_revenue or "0.00")),
        current_month_label=_clean_month_label(row.month_label or ""),
        # Expiring list
        expiring_soon=expiring_items,
        # Metadata
        generated_at=datetime.now(timezone.utc),
    )
