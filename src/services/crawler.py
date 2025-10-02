import os
import json
import hashlib
import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set

BLOB_ROOT = "./blobstore"
EXTRACTED_URLS_INDEX = "extracted_urls.json"
STORED_URLS_INDEX = "stored_urls.json"

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


def record_stored_url(url: str, index_filename: str = STORED_URLS_INDEX) -> None:
    """Record a stored article URL inside the blob root index file."""

    blob_root = Path(BLOB_ROOT)
    blob_root.mkdir(parents=True, exist_ok=True)

    index_path = blob_root / index_filename

    urls: List[str] = []
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = None

        if isinstance(data, dict):
            maybe_urls = data.get("urls")
            if isinstance(maybe_urls, list):
                urls = [str(u) for u in maybe_urls]
        elif isinstance(data, list):
            urls = [str(u) for u in data]

    if url in urls:
        return

    urls.append(url)

    with index_path.open("w", encoding="utf-8") as f:
        json.dump({"urls": urls}, f, ensure_ascii=False, indent=2)


def has_been_extracted(url: str, index_filename: str = EXTRACTED_URLS_INDEX) -> bool:
    """Return True if the given URL has already been extracted."""

    blob_root = Path(BLOB_ROOT)
    index_path = blob_root / "stored_urls.json"


    # Prefer checking a dedicated index file if present.
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = None

        if isinstance(data, dict):
            urls = data.get("urls")
        else:
            urls = data

        if isinstance(urls, list) and url in urls:
            print("The text in the url has already been extracted")
            return True

    if not blob_root.exists():
        return False

    # Fallback: scan all stored JSON payloads for the URL.
    for json_path in blob_root.rglob("*.json"):
        if json_path == index_path:
            continue

        try:
            with json_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(payload, dict) and payload.get("url") == url:
            return True

    return False


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
        ' os.path.exists(full_path) or '
        if has_been_extracted(link):
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
            record_stored_url(link)
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
