import sqlite3
from datetime import date, datetime, timedelta, timezone

from snip_url.common.errors import AppError
from snip_url.models.analytics import (
    DailyStat,
    LinkAnalyticsResponse,
    SummaryResponse,
    TopLink,
)
from snip_url.repo import link_repo, stats_repo

TOP_LINKS_LIMIT = 10


# Return the first day of the window as YYYY-MM-DD.
def window_start_day(today: date, days: int) -> str:
    return (today - timedelta(days=days - 1)).isoformat()


# Return the days of the window, oldest first, ending with today.
def build_day_list(today: date, days: int) -> list[str]:
    result: list[str] = []
    for offset in range(days - 1, -1, -1):
        result.append((today - timedelta(days=offset)).isoformat())
    return result


# Return the current UTC date.
def utc_today() -> date:
    return datetime.now(timezone.utc).date()


# Build one DailyStat per day of the window, with zeros for missing days.
def build_daily(
    conn: sqlite3.Connection, code: str, today: date, days: int
) -> list[DailyStat]:
    by_day: dict[str, dict] = {}
    start = window_start_day(today, days)
    for row in stats_repo.get_daily_stats(conn, code, start):
        by_day[row["day"]] = row
    daily: list[DailyStat] = []
    for day in build_day_list(today, days):
        row = by_day.get(day, {"click_count": 0, "unique_visitors": 0})
        daily.append(
            DailyStat(
                day=day,
                clicks=row["click_count"],
                unique_visitors=row["unique_visitors"],
            )
        )
    return daily


# Build the per-day analytics for one link.
def get_link_analytics(
    conn: sqlite3.Connection, code: str, days: int, today: date | None = None
) -> LinkAnalyticsResponse:
    if link_repo.get_link(conn, code) is None:
        raise AppError(404, "link_not_found", "Short code not found")
    if today is None:
        today = utc_today()
    start = window_start_day(today, days)
    daily = build_daily(conn, code, today, days)
    total_clicks = 0
    for item in daily:
        total_clicks = total_clicks + item.clicks
    visitors = stats_repo.count_window_visitors_for_code(conn, code, start)
    return LinkAnalyticsResponse(
        code=code,
        days=days,
        daily=daily,
        total_clicks=total_clicks,
        total_unique_visitors=visitors,
    )


# Build the summary for the window.
def get_summary(
    conn: sqlite3.Connection, days: int, today: date | None = None
) -> SummaryResponse:
    if today is None:
        today = utc_today()
    start = window_start_day(today, days)
    top: list[TopLink] = []
    for row in stats_repo.top_links(conn, start, TOP_LINKS_LIMIT):
        top.append(
            TopLink(
                code=row["code"],
                original_url=row["original_url"],
                clicks=row["clicks"],
            )
        )
    return SummaryResponse(
        days=days,
        top_links=top,
        total_links=stats_repo.count_links_since(conn, start),
        total_clicks=stats_repo.count_clicks_since(conn, start),
        total_visitors=stats_repo.count_visitors_since(conn, start),
        total_api_clients=stats_repo.count_clients_since(conn, start),
    )
