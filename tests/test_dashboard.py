"""
tests/test_dashboard.py
────────────────────────
Unit tests for dashboard service helper functions.

These tests exercise the pure-Python helpers that process the CTE result —
no DB, no HTTP, no fixtures needed.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")

from app.services.dashboard_service import _clean_month_label, _parse_expiring_item
from app.services.attendance_service import _calculate_streak


# ── Dashboard helper tests ─────────────────────────────────────────────────

class TestDashboardHelpers:

    def test_clean_month_label_strips_padding(self):
        """PostgreSQL TO_CHAR pads month names — strip should clean it."""
        raw = "June      2026"
        assert _clean_month_label(raw) == "June 2026"

    def test_clean_month_label_already_clean(self):
        assert _clean_month_label("March 2026") == "March 2026"

    def test_parse_expiring_item_string_date(self):
        """row_to_json returns date as ISO string — must parse back to date."""
        item = {
            "member_id": "S2T101",
            "full_name": "Rahul Sharma",
            "plan_name": "Monthly",
            "membership_end_date": "2026-06-10",
            "days_remaining": 5,
        }
        parsed = _parse_expiring_item(item)
        assert parsed.member_id == "S2T101"
        assert parsed.membership_end_date == date(2026, 6, 10)
        assert parsed.days_remaining == 5

    def test_parse_expiring_item_zero_days(self):
        """Expiring today — days_remaining = 0."""
        today_str = date.today().isoformat()
        item = {
            "member_id": "S2T202",
            "full_name": "Priya",
            "plan_name": "Annually",
            "membership_end_date": today_str,
            "days_remaining": 0,
        }
        parsed = _parse_expiring_item(item)
        assert parsed.days_remaining == 0


# ── Streak calculation tests ───────────────────────────────────────────────

class TestStreakCalculation:
    """Tests for the attendance streak algorithm (shared with Phase 7)."""

    def test_empty_dates_returns_zero(self):
        assert _calculate_streak([], date.today()) == 0

    def test_only_today_returns_one(self):
        today = date.today()
        assert _calculate_streak([today], today) == 1

    def test_consecutive_streak_includes_today(self):
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(5)]
        assert _calculate_streak(dates, today) == 5

    def test_streak_stops_at_gap(self):
        today = date.today()
        # Attended today, yesterday, and 3 days ago (gap on day 2)
        dates = [today, today - timedelta(days=1), today - timedelta(days=3)]
        assert _calculate_streak(dates, today) == 2

    def test_no_attendance_today_streak_zero(self):
        """Even if attended 30 consecutive days before, no today = streak 0."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(1, 31)]
        assert _calculate_streak(dates, today) == 0

    def test_duplicate_dates_counted_once(self):
        """FN + AN on same day = 2 rows but 1 day in streak."""
        today = date.today()
        # Both FN and AN logged today — two entries for same date
        dates = [today, today, today - timedelta(days=1)]
        assert _calculate_streak(dates, today) == 2

    def test_non_contiguous_historical_dates_ignored(self):
        today = date.today()
        dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
            # Gap here
            today - timedelta(days=10),
            today - timedelta(days=11),
        ]
        assert _calculate_streak(dates, today) == 3
