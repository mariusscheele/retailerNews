import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set

def get_subpages(root_url: str) -> List[str]:
    """
    Crawl a single web page and extract all subpage links
    that belong to the same domain and start with the given root_url.
    
    Args:
        root_url (str): The root page to crawl, e.g. "https://www.mckinsey.com/industries/retail/"
    
    Returns:
        List[str]: A list of unique subpage URLs under that root.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SubpageCrawler/1.0)"}
    try:
        resp = requests.get(root_url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {root_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # Normalize the root for comparison
    parsed_root = urlparse(root_url)
    root_netloc = parsed_root.netloc
    root_path = parsed_root.path.rstrip("/") + "/"

    found: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Resolve relative → absolute URL
        abs_url = urljoin(root_url, href)
        parsed = urlparse(abs_url)

        # Only keep same domain
        if parsed.netloc != root_netloc:
            continue

        # Only keep pages starting with the root path
        if not parsed.path.startswith(root_path):
            continue

        # Remove fragment part (#...) to normalize
        normalized = abs_url.split("#")[0]

        found.add(normalized)

    return sorted(found)


# Example usage:
if __name__ == "__main__":
    url = "https://www.mckinsey.com/industries/retail/"
    subpages = get_subpages(url)
    print(f"Found {len(subpages)} subpages under {url}:")
    for sp in subpages:
        print(" -", sp)