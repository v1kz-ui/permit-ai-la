"""Unit tests for analytics service."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import analytics_service


def _make_mock_session(execute_returns):
    """Create a mock AsyncSession that returns the given values for execute calls."""
    session = AsyncMock()
    results = []
    for ret in execute_returns:
        mock_result = MagicMock()
        if isinstance(ret, list):
            mock_result.all.return_value = ret
            mock_result.scalars.return_value.all.return_value = ret
        elif isinstance(ret, tuple):
            mock_result.one.return_value = ret
            mock_result.scalar.return_value = ret[0] if len(ret) == 1 else ret
        else:
            mock_result.scalar.return_value = ret
            mock_result.scalar_one_or_none.return_value = ret
            mock_result.all.return_value = []
        results.append(mock_result)

    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_pipeline_metrics_returns_expected_keys():
    """Pipeline metrics response should contain departments list and summary dict."""
    mock_rows = [
        ("ladbs", 20, 15, 5.5, 2),
        ("dcp", 10, 8, 3.2, 1),
        ("lafd", 5, 5, 2.0, 0),
    ]
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    session.execute = AsyncMock(return_value=mock_result)

    result = await analytics_service.get_pipeline_metrics(session)

    assert "departments" in result
    assert "summary" in result
    assert isinstance(result["departments"], list)
    assert len(result["departments"]) == 3

    summary = result["summary"]
    assert "total_clearances" in summary
    assert "total_completed" in summary
    assert "overall_completion_rate" in summary
    assert "total_bottlenecks" in summary

    # Check computed values
    assert summary["total_clearances"] == 35
    assert summary["total_completed"] == 28
    assert summary["total_bottlenecks"] == 3

    # Check department structure
    dept = result["departments"][0]
    assert "department" in dept
    assert "total" in dept
    assert "completed" in dept
    assert "completion_rate" in dept
    assert "avg_processing_days" in dept
    assert "bottleneck_count" in dept


@pytest.mark.asyncio
async def test_pipeline_metrics_with_date_range():
    """Pipeline metrics should accept optional date range."""
    mock_rows = [("ladbs", 10, 7, 4.0, 1)]
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    session.execute = AsyncMock(return_value=mock_result)

    date_range = (date(2025, 1, 1), date(2025, 6, 30))
    result = await analytics_service.get_pipeline_metrics(session, date_range)

    assert "departments" in result
    assert len(result["departments"]) == 1
    assert result["departments"][0]["department"] == "ladbs"


@pytest.mark.asyncio
async def test_pipeline_metrics_empty():
    """Pipeline metrics should handle empty results."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    result = await analytics_service.get_pipeline_metrics(session)

    assert result["departments"] == []
    assert result["summary"]["total_clearances"] == 0
    assert result["summary"]["overall_completion_rate"] == 0.0


@pytest.mark.asyncio
async def test_trend_data_valid_periods():
    """Trend data should work for day, week, and month periods."""
    for period in ("day", "week", "month"):
        mock_data = [
            (datetime(2025, 3, 1, tzinfo=timezone.utc), 5),
            (datetime(2025, 3, 2, tzinfo=timezone.utc), 8),
        ]
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = mock_data
        session.execute = AsyncMock(return_value=mock_result)

        result = await analytics_service.get_trend_data(
            session, "permits_issued", period
        )

        assert result["metric"] == "permits_issued"
        assert result["period"] == period
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["value"] == 5
        assert result["data"][1]["value"] == 8


@pytest.mark.asyncio
async def test_trend_data_unknown_metric():
    """Trend data should return an error for unknown metrics."""
    session = AsyncMock()

    result = await analytics_service.get_trend_data(
        session, "invalid_metric", "day"
    )

    assert "error" in result
    assert result["error"] == "Unknown metric"
    assert result["data"] == []


@pytest.mark.asyncio
async def test_trend_data_all_metric_types():
    """Trend data should support all three valid metric types."""
    for metric in ("permits_issued", "clearances_completed", "bottlenecks_detected"):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        result = await analytics_service.get_trend_data(session, metric, "day")

        assert result["metric"] == metric
        assert "error" not in result


@pytest.mark.asyncio
async def test_equity_metrics_structure():
    """Equity metrics should return areas, languages, pathways, and fire_zone_comparison."""
    session = AsyncMock()

    # Create mock results for the 4 sequential queries
    area_result = MagicMock()
    area_result.all.return_value = [
        ("Pacific Palisades", 15, 45.0, 50.2),
        ("Altadena", 12, 42.0, 48.5),
    ]

    lang_result = MagicMock()
    lang_result.all.return_value = [
        ("en", 20),
        ("es", 5),
        ("ko", 3),
    ]

    pathway_result = MagicMock()
    pathway_result.all.return_value = [
        ("eo1_like_for_like", 18, 30.0),
        ("standard", 8, 60.0),
    ]

    fire_result = MagicMock()
    fire_result.all.return_value = [
        (True, 20, 55.0),
        (False, 10, 35.0),
    ]

    session.execute = AsyncMock(
        side_effect=[area_result, lang_result, pathway_result, fire_result]
    )

    result = await analytics_service.get_equity_metrics(session)

    # Check top-level keys
    assert "areas" in result
    assert "languages" in result
    assert "pathways" in result
    assert "fire_zone_comparison" in result

    # Check areas structure
    assert len(result["areas"]) == 2
    assert result["areas"][0]["area"] == "Pacific Palisades"
    assert result["areas"][0]["project_count"] == 15
    assert result["areas"][0]["avg_predicted_days"] == 45.0
    assert result["areas"][0]["avg_actual_days"] == 50.2

    # Check languages
    assert len(result["languages"]) == 3
    assert result["languages"][0]["language"] == "en"
    assert result["languages"][0]["count"] == 20

    # Check pathways
    assert len(result["pathways"]) == 2
    assert result["pathways"][0]["pathway"] == "eo1_like_for_like"

    # Check fire zone comparison
    assert len(result["fire_zone_comparison"]) == 2


@pytest.mark.asyncio
async def test_department_performance_returns_data():
    """Department performance should return detailed stats for a department."""
    session = AsyncMock()

    # Stats query result (one row with 7 columns)
    stats_result = MagicMock()
    stats_result.one.return_value = (50, 30, 10, 5, 5, 4.5, 3)

    # Monthly trend
    monthly_result = MagicMock()
    monthly_result.all.return_value = [
        (datetime(2025, 1, 1, tzinfo=timezone.utc), 10, 7),
        (datetime(2025, 2, 1, tzinfo=timezone.utc), 12, 9),
    ]

    # Denial reasons
    denial_result = MagicMock()
    denial_result.all.return_value = [
        ("Missing documentation", 3),
        ("Non-compliant plans", 2),
    ]

    session.execute = AsyncMock(
        side_effect=[stats_result, monthly_result, denial_result]
    )

    result = await analytics_service.get_department_performance(session, "ladbs")

    assert result["department"] == "ladbs"
    assert result["total_clearances"] == 50
    assert result["approved"] == 30
    assert result["conditional"] == 10
    assert result["denied"] == 5
    assert result["in_review"] == 5
    assert result["approval_rate"] == 80.0  # (30 + 10) / 50 * 100
    assert result["avg_processing_days"] == 4.5
    assert result["bottleneck_count"] == 3

    # Monthly trend
    assert len(result["monthly_trend"]) == 2

    # Rejection reasons
    assert len(result["rejection_reasons"]) == 2
    assert result["rejection_reasons"][0]["reason"] == "Missing documentation"
    assert result["rejection_reasons"][0]["count"] == 3
