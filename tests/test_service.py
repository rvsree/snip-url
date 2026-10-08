import pytest

from snip_url.common.config import Settings
from snip_url.common.errors import AppError
from snip_url.repo import link_repo
from snip_url.repo.db import get_connection, init_db
from snip_url.services import link_service


# Return a list that is used as a queue of codes for a fake generator.
def install_fake_generator(monkeypatch: pytest.MonkeyPatch, codes: list[str]) -> None:
    state = {"index": 0}

    # Return the next code, repeating the last one when the list runs out.
    def fake_generate_code() -> str:
        position = state["index"]
        if position >= len(codes):
            position = len(codes) - 1
        state["index"] = state["index"] + 1
        return codes[position]

    monkeypatch.setattr(link_service, "generate_code", fake_generate_code)


# AC13: a taken code is skipped and a new unused code is used.
def test_AC13_collision_retries_to_new_code(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(settings.db_path)
    conn = get_connection(settings.db_path)
    try:
        link_repo.insert_link(conn, "TakenCd", "https://example.com/old", "2026-01-01T00:00:00+00:00")
        install_fake_generator(monkeypatch, ["TakenCd", "FreshCd"])
        result = link_service.create_link(conn, settings.base_url, "https://example.com/new")
        assert result.code == "FreshCd"
        old = link_repo.get_link(conn, "TakenCd")
        assert old is not None
        assert old["original_url"] == "https://example.com/old"
    finally:
        conn.close()


# AC13: when every attempt collides, a 500 code_generation_failed error is raised.
def test_AC13_code_exhaustion_raises_500(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(settings.db_path)
    conn = get_connection(settings.db_path)
    try:
        link_repo.insert_link(conn, "TakenCd", "https://example.com/old", "2026-01-01T00:00:00+00:00")
        install_fake_generator(monkeypatch, ["TakenCd"])
        with pytest.raises(AppError) as info:
            link_service.create_link(conn, settings.base_url, "https://example.com/new")
        assert info.value.status_code == 500
        assert info.value.code == "code_generation_failed"
        assert info.value.message != ""
        assert link_repo.count_clicks(conn, "TakenCd") == 0
    finally:
        conn.close()
