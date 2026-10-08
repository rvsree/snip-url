import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from snip_url.models.link import (
    CreateLinkRequest,
    CreateLinkResponse,
    HealthResponse,
    LinkStatsResponse,
)
from snip_url.repo.db import get_connection
from snip_url.services import link_service

router = APIRouter()


# Return a new connection using the app settings.
def open_conn(request: Request) -> sqlite3.Connection:
    return get_connection(request.app.state.settings.db_path)


# Health check.
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# Create a short link.
@router.post("/api/links", status_code=201, response_model=CreateLinkResponse)
def create_link(body: CreateLinkRequest, request: Request) -> CreateLinkResponse:
    conn = open_conn(request)
    try:
        base_url = request.app.state.settings.base_url
        return link_service.create_link(conn, base_url, body.url)
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
        url = link_service.resolve_and_record_click(conn, code)
        return RedirectResponse(url, status_code=301)
    finally:
        conn.close()
