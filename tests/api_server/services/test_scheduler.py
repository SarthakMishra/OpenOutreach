# tests/api_server/services/test_scheduler.py
"""Test scheduler cron calculation (isolated from executor to avoid circular imports)."""
from datetime import datetime, timezone

from croniter import croniter


def _calculate_next_run(cron: str, from_time: datetime | None = None) -> datetime:
    """Calculate next run time from cron expression (duplicated from scheduler for testing)."""
    if from_time is None:
        from_time = datetime.now(timezone.utc)
    iter = croniter(cron, from_time)
    return iter.get_next(datetime)


class TestCalculateNextRun:
    """Test _calculate_next_run() function."""

    def test_daily_cron(self):
        """Test daily cron expression."""
        cron = "0 0 * * *"  # Every day at midnight
        from_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        next_run = _calculate_next_run(cron, from_time)
        assert next_run > from_time
        assert next_run.hour == 0
        assert next_run.minute == 0

    def test_hourly_cron(self):
        """Test hourly cron expression."""
        cron = "0 * * * *"  # Every hour at minute 0
        from_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        next_run = _calculate_next_run(cron, from_time)
        assert next_run > from_time
        # Should be next hour (13:00)
        assert next_run.hour == 13
        assert next_run.minute == 0

    def test_weekly_cron(self):
        """Test weekly cron expression."""
        cron = "0 0 * * 1"  # Every Monday at midnight
        from_time = datetime(2024, 1, 3, 12, 0, 0, tzinfo=timezone.utc)  # Wednesday
        next_run = _calculate_next_run(cron, from_time)
        assert next_run > from_time
        # Should be next Monday
        assert next_run.weekday() == 0  # Monday

    def test_every_minute_cron(self):
        """Test every minute cron expression."""
        cron = "* * * * *"  # Every minute
        from_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        next_run = _calculate_next_run(cron, from_time)
        assert next_run > from_time
        # Should be very close to from_time (within 1 minute)
        diff = (next_run - from_time).total_seconds()
        assert 0 < diff <= 60

    def test_default_from_time(self):
        """Test that default from_time is current time."""
        cron = "0 0 * * *"  # Daily at midnight
        next_run = _calculate_next_run(cron)
        # Should be in the future
        assert next_run > datetime.now(timezone.utc)

    def test_complex_cron(self):
        """Test complex cron expression."""
        cron = "30 14 * * 1-5"  # 2:30 PM on weekdays
        from_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)  # Monday 10 AM
        next_run = _calculate_next_run(cron, from_time)
        assert next_run > from_time
        assert next_run.hour == 14
        assert next_run.minute == 30
        assert next_run.weekday() < 5  # Weekday

