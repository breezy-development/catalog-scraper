import pytest
import responses

from catalog_scraper.fetch import DisallowedByRobots, PoliteFetcher


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@responses.activate
def test_respects_robots_disallow():
    responses.get("https://example.test/robots.txt", body="User-agent: *\nDisallow: /private/\n")
    responses.get("https://example.test/public", body="ok")
    f = PoliteFetcher(delay=0)
    assert f.get("https://example.test/public") == "ok"
    with pytest.raises(DisallowedByRobots):
        f.get("https://example.test/private/page")


@responses.activate
def test_missing_robots_means_allowed():
    responses.get("https://example.test/robots.txt", status=404)
    responses.get("https://example.test/a", body="ok")
    assert PoliteFetcher(delay=0).get("https://example.test/a") == "ok"


@responses.activate
def test_crawl_delay_raises_configured_delay():
    responses.get("https://example.test/robots.txt", body="User-agent: *\nCrawl-delay: 5\n")
    responses.get("https://example.test/a", body="ok")
    f = PoliteFetcher(delay=1)
    f.get("https://example.test/a")
    assert f.delay == 5


@responses.activate
def test_throttles_between_requests():
    responses.get("https://example.test/robots.txt", status=404)
    responses.get("https://example.test/a", body="ok")
    clock = FakeClock()
    f = PoliteFetcher(delay=2, sleep=clock.sleep, clock=clock)
    f.get("https://example.test/a")
    clock.now += 0.5
    f.get("https://example.test/a")
    assert clock.sleeps == [pytest.approx(1.5)]


@responses.activate
def test_decodes_utf8_when_charset_missing():
    responses.get("https://example.test/robots.txt", status=404)
    responses.get(
        "https://example.test/p", body="£45.17".encode(), content_type="text/html"
    )
    assert PoliteFetcher(delay=0).get("https://example.test/p") == "£45.17"


@responses.activate
def test_sends_identifying_user_agent():
    responses.get("https://example.test/robots.txt", status=404)
    responses.get("https://example.test/a", body="ok")
    PoliteFetcher(delay=0).get("https://example.test/a")
    assert responses.calls[-1].request.headers["User-Agent"].startswith("catalog-scraper/")
