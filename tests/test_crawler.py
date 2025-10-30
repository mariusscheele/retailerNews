from __future__ import annotations

from types import SimpleNamespace

from bs4 import BeautifulSoup

from retailernews.config import SiteConfig
from retailernews.services.crawler import SiteCrawler


def test_extract_articles_skips_external_links(monkeypatch) -> None:
    crawler = SiteCrawler()

    html = """
    <html>
        <body>
            <a href="https://othersite.com/story">External</a>
            <a href="/news/internal">Internal Story</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")

    monkeypatch.setattr(crawler, "_build_summary", lambda *args, **kwargs: "summary")

    articles = list(crawler._extract_articles(soup, ["Story"], "https://example.com"))

    assert len(articles) == 1
    assert str(articles[0].url) == "https://example.com/news/internal"


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception("error")


def test_find_published_date_uses_text_regex() -> None:
    html = """
    <html>
        <body>
            <p>Updated 2023</p>
            <div>Published at October 5, 2024.</div>
            <footer>PUBLISHED ON 2024-09-30 should not match first.</footer>
        </body>
    </html>
    """

    assert SiteCrawler.find_published_date(html) == "October 5, 2024"


def test_fetch_extracts_new_articles(monkeypatch) -> None:
    site = SiteConfig(name="Example", url="https://example.com", topics=[])
    crawler = SiteCrawler()

    article_text = "lorem ipsum " * 20

    responses = {
        "https://example.com/": DummyResponse(
            "<html><a href=\"/story\">Story</a></html>"
        ),
        "https://example.com/story": DummyResponse("<html>content</html>"),
    }

    def fake_get(url, timeout):
        return responses[url]

    crawler._session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr(crawler, "extract_text", lambda html: ("Story", article_text))
    monkeypatch.setattr(crawler, "find_published_date", lambda html: "2024-10-05")
    monkeypatch.setattr(crawler, "article_path", lambda url: "path/to/article.json")

    stored_payloads = []
    monkeypatch.setattr(
        crawler,
        "store_json",
        lambda path, payload, blob_root=None: stored_payloads.append((path, payload)),
    )
    recorded_urls = []
    monkeypatch.setattr(
        crawler,
        "record_stored_url",
        lambda url, blob_root=None: recorded_urls.append(url),
    )
    monkeypatch.setattr(crawler, "has_been_extracted", lambda url, blob_root=None: False)

    result = crawler.fetch(site)

    assert len(result.articles) == 1
    assert result.articles[0].text == article_text
    assert stored_payloads
    payload = stored_payloads[0][1]
    assert payload["datestamp"] == "2024-10-05"
    assert recorded_urls == ["https://example.com/story"]


def test_fetch_skips_existing_articles(monkeypatch) -> None:
    site = SiteConfig(name="Example", url="https://example.com", topics=[])
    crawler = SiteCrawler()

    responses = {
        "https://example.com/": DummyResponse(
            "<html><a href=\"/story\">Story</a></html>"
        )
    }

    def fake_get(url, timeout):
        return responses[url]

    crawler._session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr(crawler, "has_been_extracted", lambda url, blob_root=None: True)

    fetch_called = False

    def fail_extract(html):
        nonlocal fetch_called
        fetch_called = True
        raise AssertionError("Should not be called")

    monkeypatch.setattr(crawler, "extract_text", fail_extract)

    def fail_store(*args, **kwargs):
        raise AssertionError("Should not store")

    monkeypatch.setattr(crawler, "store_json", fail_store)
    monkeypatch.setattr(crawler, "record_stored_url", fail_store)

    result = crawler.fetch(site)

    assert len(result.articles) == 1
    assert result.articles[0].text is None
    assert fetch_called is False


def test_fetch_filters_articles_by_root(monkeypatch) -> None:
    site = SiteConfig(
        name="Example",
        url="https://aggregator.example.com",
        root="https://example.com",
        topics=[],
        use_sitemap=True,
        sitemap_url="https://aggregator.example.com/sitemap.xml",
    )
    crawler = SiteCrawler()

    monkeypatch.setattr(
        crawler,
        "discover_links_from_sitemap",
        lambda sitemap_url, filter_path=None, use_playwright=False: [
            "https://example.com/story",
            "https://other.com/story",
        ],
    )

    article_text = "ipsum lorem " * 20

    def fake_get(url, timeout):
        if url == "https://example.com/story":
            return DummyResponse("<html>content</html>")
        raise AssertionError(f"Unexpected request for {url}")

    crawler._session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr(crawler, "extract_text", lambda html: ("Story", article_text))
    monkeypatch.setattr(crawler, "find_published_date", lambda html: None)
    monkeypatch.setattr(crawler, "article_path", lambda url: "path/to/article.json")
    monkeypatch.setattr(crawler, "has_been_extracted", lambda url, blob_root=None: False)

    recorded_urls: list[str] = []
    stored_payloads: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        crawler,
        "store_json",
        lambda path, payload, blob_root=None: stored_payloads.append((path, payload)),
    )
    monkeypatch.setattr(
        crawler,
        "record_stored_url",
        lambda url, blob_root=None: recorded_urls.append(url),
    )

    result = crawler.fetch(site)

    assert recorded_urls == ["https://example.com/story"]
    assert [str(article.url) for article in result.articles] == ["https://example.com/story"]
    assert stored_payloads


def test_fetch_accepts_sitemap_arguments(monkeypatch) -> None:
    site = SiteConfig(name="Example", url="https://example.com", topics=[])
    crawler = SiteCrawler()

    article_text = "lorem ipsum " * 20
    captured: dict[str, str | None] = {}

    def fake_discover(sitemap_url, filter_path=None, use_playwright=False):
        captured["sitemap_url"] = sitemap_url
        captured["filter_path"] = filter_path
        return ["https://example.com/story"]

    monkeypatch.setattr(crawler, "discover_links_from_sitemap", fake_discover)

    def fake_get(url, timeout):
        if url == "https://example.com/story":
            return DummyResponse("<html>content</html>")
        raise AssertionError(f"Unexpected request for {url}")

    crawler._session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr(crawler, "extract_text", lambda html: ("Story", article_text))
    monkeypatch.setattr(crawler, "find_published_date", lambda html: None)
    monkeypatch.setattr(crawler, "article_path", lambda url: "path/to/article.json")
    monkeypatch.setattr(crawler, "has_been_extracted", lambda url, blob_root=None: False)
    monkeypatch.setattr(crawler, "store_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(crawler, "record_stored_url", lambda *args, **kwargs: None)

    result = crawler.fetch(
        site,
        use_sitemap=True,
        sitemap_url="https://example.com/sitemap.xml",
        filter_path="retail",
    )

    assert [str(article.url) for article in result.articles] == ["https://example.com/story"]
    assert captured == {"sitemap_url": "https://example.com/sitemap.xml", "filter_path": "retail"}
