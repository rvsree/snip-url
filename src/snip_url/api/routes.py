import sqlite3

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from snip_url.models.analytics import LinkAnalyticsResponse, SummaryResponse
from snip_url.models.link import (
    CreateLinkRequest,
    CreateLinkResponse,
    HealthResponse,
    LinkStatsResponse,
)
from snip_url.repo.db import get_connection
from snip_url.services import analytics_service, link_service, tracking_service

router = APIRouter()


# Return a new connection using the app settings.
def open_conn(request: Request) -> sqlite3.Connection:
    return get_connection(request.app.state.settings.db_path)


# Health check.
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# Return the direct client IP (ignores X-Forwarded-For) or "unknown".
def client_ip_of(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"


# Dependency: count this create request against the direct client IP and record rate-limit hits.
def limit_create(request: Request) -> None:
    settings = request.app.state.settings
    conn = open_conn(request)
    try:
        tracking_service.enforce_create_limit(
            conn,
            request.app.state.rate_limiter,
            client_ip_of(request),
            settings.ip_hash_salt,
        )
    finally:
        conn.close()


# Create a short link.
@router.post(
    "/api/links",
    status_code=201,
    response_model=CreateLinkResponse,
    dependencies=[Depends(limit_create)],
)
def create_link(body: CreateLinkRequest, request: Request) -> CreateLinkResponse:
    conn = open_conn(request)
    try:
        settings = request.app.state.settings
        return link_service.create_link(
            conn,
            settings.base_url,
            body.url,
            body.alias,
            client_ip=client_ip_of(request),
            salt=settings.ip_hash_salt,
        )
    finally:
        conn.close()


# Return per-day analytics for one code.
@router.get("/api/analytics/links/{code}", response_model=LinkAnalyticsResponse)
def link_analytics(
    code: str, request: Request, days: int = Query(7, ge=1, le=90)
) -> LinkAnalyticsResponse:
    conn = open_conn(request)
    try:
        return analytics_service.get_link_analytics(conn, code, days)
    finally:
        conn.close()


# Return the analytics summary.
@router.get("/api/analytics/summary", response_model=SummaryResponse)
def analytics_summary(
    request: Request, days: int = Query(7, ge=1, le=90)
) -> SummaryResponse:
    conn = open_conn(request)
    try:
        return analytics_service.get_summary(conn, days)
    finally:
        conn.close()


# Return click stats for a code.
@router.get("/api/links/{code}/stats", response_model=LinkStatsResponse)
def link_stats(code: str, request: Request) -> LinkStatsResponse:
    conn = open_conn(request)
    try:
        return link_service.get_stats(conn, code)
    finally:
        conn.close()


# Redirect a short code to its original url.
@router.get("/{code}")
def redirect(code: str, request: Request) -> RedirectResponse:
    conn = open_conn(request)
    try:
        url = link_service.resolve_and_record_click(
            conn,
            code,
            client_ip=client_ip_of(request),
            salt=request.app.state.settings.ip_hash_salt,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
        )
        return RedirectResponse(url, status_code=302)
    finally:
        conn.close()
