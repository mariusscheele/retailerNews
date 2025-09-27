from __future__ import annotations

from bs4 import BeautifulSoup

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
