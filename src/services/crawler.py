import os
import json
import hashlib
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set

BLOB_ROOT = "./blobstore"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    )
}


def store_json(path: str, payload: dict) -> None:
    """Save payload as JSON into local blob-style folder."""
    full_path = os.path.join(BLOB_ROOT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def article_path(url: str) -> str:
    """Generate blob-style path based on URL and current date."""
    host = urlparse(url).netloc
    datestamp = datetime.datetime.utcnow().strftime("%Y%m%d")
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"site={host}/{datestamp}/{url_hash}.json"


def extract_text(html: str) -> tuple[str, str]:
    """Extract title and text content from HTML."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text("\n", strip=True)
    return title, text


def discover_links_from_page(root_url: str) -> List[str]:
    """Fetch a page and extract same-domain sublinks."""
    resp = requests.get(root_url, headers=HEADERS, timeout=(10, 60))
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    parsed_root = urlparse(root_url)
    root_netloc = parsed_root.netloc
    root_path = parsed_root.path.rstrip("/") + "/"

    found: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(root_url, href)
        parsed = urlparse(abs_url)

        if parsed.netloc != root_netloc:
            continue
        if not parsed.path.startswith(root_path):
            continue

        found.add(abs_url.split("#")[0])  # drop fragments
    return list(found)


def discover_links_from_sitemap(sitemap_url: str, filter_path: str = None) -> List[str]:
    """Parse sitemap.xml and return links (optionally filtered by path)."""
    resp = requests.get(sitemap_url, headers=HEADERS, timeout=(10, 120))
    print(resp)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "xml")
    urls = [loc.text for loc in soup.find_all("loc")]
    if filter_path:
        urls = [u for u in urls if filter_path in u]
    return urls


def crawl(root_url: str, use_sitemap: bool = False, sitemap_url: str = None, filter_path: str = None):
    """
    Crawl pages starting from a root URL.
    If use_sitemap=True, pull URLs from the sitemap instead of the root page.
    """
    if use_sitemap:
        if not sitemap_url:
            raise ValueError("Sitemap URL must be provided if use_sitemap=True")
        links = discover_links_from_sitemap(sitemap_url, filter_path)
    else:
        links = discover_links_from_page(root_url)

    print(f"Discovered {len(links)} links")

    for link in links:
        path = article_path(link)
        full_path = os.path.join(BLOB_ROOT, path)
        if os.path.exists(full_path):
            continue  # skip if already stored

        try:
            resp = requests.get(link, headers=HEADERS, timeout=(10, 60))
            resp.raise_for_status()
            title, text = extract_text(resp.text)

            if not text or len(text) < 200:
                print(f"Too little text, skip: {link}")
                continue

            payload = {
                "url": link,
                "title": title,
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": text,
            }
            store_json(path, payload)
            print(f"Stored {link}")
        except Exception as e:
            print(f"Failed {link}: {e}")


if __name__ == "__main__":
    # Example 1: Using sitemap for McKinsey retail
    crawl(
        root_url="https://www.retailgazette.co.uk/blog/2025/09/",
        use_sitemap=False,
        sitemap_url="",
        filter_path="/blog/"
    )

    # Example 2: Using plain page parsing (fallback)
    # crawl("https://www.example.com/section/", use_sitemap=False)
