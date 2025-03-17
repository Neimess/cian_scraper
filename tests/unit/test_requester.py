from urllib.parse import urlencode

import pytest
import requests

from src.web_scraper.requester import USER_AGENTS, Requester


class FakeResponse:
    def __init__(self, text, status_code, headers):
        self.text = text
        self.status_code = status_code
        self.headers = headers


def fake_get_success(url, headers, timeout, allow_redirects):
    return FakeResponse("Success", 200, {"Content-Type": "text/html"})


def fake_get_exception(url, headers, timeout, allow_redirects):
    raise requests.exceptions.RequestException("Test exception")


@pytest.mark.asyncio
async def test_fetch_exception(monkeypatch):
    monkeypatch.setattr(requests, "get", fake_get_exception)
    req = Requester("http://exception.com", freeze_time=0)
    text, status, headers = await req.fetch()
    assert text == ""
    assert status == 500
    assert headers == {}


def test_url_construction_with_params():
    params = {"a": "1", "b": "2"}
    req = Requester("http://example.com/", params=params)
    expected_query = urlencode(params)
    assert "cat.php" in req.url
    assert expected_query in req.url


def test_headers_contains_user_agent():
    req = Requester("http://example.com")
    user_agent = req.headers.get("User-Agent")
    assert user_agent in USER_AGENTS
