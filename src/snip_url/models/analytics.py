from pydantic import BaseModel


class DailyStat(BaseModel):
    day: str
    clicks: int
    unique_visitors: int


class LinkAnalyticsResponse(BaseModel):
    code: str
    days: int
    daily: list[DailyStat]
    total_clicks: int
    total_unique_visitors: int


class TopLink(BaseModel):
    code: str
    original_url: str
    clicks: int


class SummaryResponse(BaseModel):
    days: int
    top_links: list[TopLink]
    total_links: int
    total_clicks: int
    total_visitors: int
    total_api_clients: int
