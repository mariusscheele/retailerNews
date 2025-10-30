import asyncio
import re
from typing import Optional, List

import pytest
from bs4 import BeautifulSoup

playwright_async = pytest.importorskip(
    "playwright.async_api",
    reason="Playwright is required to crawl McKinsey pages",
)
async_playwright = playwright_async.async_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) "
        "Gecko/20100101 Firefox/129.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def fetch_with_firefox(url: str, wait_ms: int = 3000) -> str:
    """Fetch raw page content using Playwright Firefox (handles Akamai)."""
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page(extra_http_headers=HEADERS)
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(wait_ms)
        html = await page.content()
        await browser.close()
        return html


async def get_sitemap_links(base_url: str, filter_path: Optional[str] = None) -> List[str]:
    """Fetch sitemap.xml and return list of <loc> URLs, optionally filtered."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    print(f"🔎 Fetching sitemap: {sitemap_url}")
    xml = await fetch_with_firefox(sitemap_url)

    # Parse sitemap XML
    soup = BeautifulSoup(xml, "xml")
    urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
    if filter_path:
        urls = [u for u in urls if filter_path in u]

    print(f"✅ Found {len(urls)} URLs (filtered by: {filter_path})")
    return urls


async def extract_article(url: str) -> Optional[dict]:
    """Extract title, date, author, and text from a McKinsey article URL."""
    print(f"📰 Extracting article: {url}")
    html = await fetch_with_firefox(url)
    soup = BeautifulSoup(html, "lxml")

    # ---- Title ----
    title_tag = soup.find("meta", property="og:title") or soup.find("title")
    title = (
        title_tag.get("content")
        if title_tag and title_tag.has_attr("content")
        else (title_tag.get_text(strip=True) if title_tag else None)
    )

    # ---- Date ----
    date_tag = soup.find("meta", attrs={"name": "publish-date"}) or soup.find("time")
    publish_date = (
        date_tag.get("content")
        if date_tag and date_tag.has_attr("content")
        else (date_tag.get_text(strip=True) if date_tag else None)
    )

    # ---- Author ----
    author_tag = soup.find("meta", attrs={"name": "author"})
    author = author_tag.get("content") if author_tag and author_tag.has_attr("content") else None

    # ---- Body ----
    article_node = (
        soup.find("article")
        or soup.find("div", class_=re.compile(r"Article-body"))
        or soup.find("main")
    )
    paragraphs = [p.get_text(" ", strip=True) for p in article_node.find_all("p")] if article_node else []
    text = clean_text(" ".join(paragraphs))

    if not text:
        print(f"⚠️ No text found for: {url}")
        return None

    return {
        "url": url,
        "title": title,
        "summary": clean_text(title or url or ""),
        "author": author,
        "publish_date": publish_date,
        "text": text,
        "length": len(text),
    }


async def crawl_mckinsey_section(base_url: str, section_path: str):
    """Fetch sitemap, filter by section, and extract all article contents."""
    urls = await get_sitemap_links(base_url, filter_path=section_path)
    urls = urls[:4]
    results = []
    for idx, url in enumerate(urls, 1):
        article = await extract_article(url)
        if article:
            results.append(article)
            print(f"✅ [{idx}/{len(urls)}] Extracted: {article['title']}")
        await asyncio.sleep(2)  # polite delay

    print(f"🟢 Completed extraction of {len(results)} articles.")
    return results


# ---- Example usage ----
if __name__ == "__main__":
    async def main():
        base_url = "https://www.mckinsey.com"
        section_path = "/industries/retail/our-insights/"
        articles = await crawl_mckinsey_section(base_url, section_path)

        # Print a preview of first article
        if articles:
            a = articles[0]
            print("\n📰 Example article:")
            print(f"Title: {a['title']}")
            print(f"Date: {a['publish_date']}")
            print(f"Author: {a['author']}")
            print(f"Text sample: {a['text'][:500]}...")

    asyncio.run(main())
