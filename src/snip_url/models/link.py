from pydantic import BaseModel


class CreateLinkRequest(BaseModel):
    url: str | None = None
    alias: str | None = None


class CreateLinkResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    created_at: str


class LinkStatsResponse(BaseModel):
    code: str
    original_url: str
    created_at: str
    click_count: int


class HealthResponse(BaseModel):
    status: str
