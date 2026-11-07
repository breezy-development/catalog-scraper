"""HTTP client that behaves like a good citizen: robots.txt, rate limiting, retries."""

from __future__ import annotations

import logging
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import __version__

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    f"catalog-scraper/{__version__} (+https://github.com/breezy-development/catalog-scraper)"
)


class DisallowedByRobots(Exception):
    pass


class PoliteFetcher:
    def __init__(
        self,
        delay: float = 1.0,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 20.0,
        retries: int = 3,
        session: requests.Session | None = None,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        self.delay = delay
        self.user_agent = user_agent
        self.timeout = timeout
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._robots: dict[str, RobotFileParser] = {}

        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        retry = Retry(
            total=retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url: str) -> str:
        if not self.allowed(url):
            raise DisallowedByRobots(url)
        self._throttle()
        log.debug("GET %s", url)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        if "charset" not in resp.headers.get("Content-Type", "").lower():
            resp.encoding = "utf-8"  # requests would otherwise assume ISO-8859-1 for text/html
        return resp.text

    def allowed(self, url: str) -> bool:
        parts = urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(origin)
        if parser is None:
            parser = RobotFileParser()
            robots_url = urljoin(origin, "/robots.txt")
            try:
                resp = self.session.get(robots_url, timeout=self.timeout)
                if resp.status_code >= 400:
                    parser.parse([])  # no robots.txt: everything allowed
                else:
                    parser.parse(resp.text.splitlines())
            except requests.RequestException as exc:
                log.warning("could not read %s (%s); assuming allowed", robots_url, exc)
                parser.parse([])
            self._robots[origin] = parser
            crawl_delay = parser.crawl_delay(self.user_agent)
            if crawl_delay and crawl_delay > self.delay:
                log.info("robots.txt crawl-delay %ss for %s", crawl_delay, origin)
                self.delay = float(crawl_delay)
        return parser.can_fetch(self.user_agent, url)

    def _throttle(self) -> None:
        now = self._clock()
        if self._last_request is not None:
            wait = self.delay - (now - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()
