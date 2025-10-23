"""Convenience script for running the Retailer News crawler locally."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import requests

# Ensure the src directory is on the Python path so the retailernews package can be imported
SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from retailernews.config import AppConfig  # noqa: E402  (import after path setup)
from retailernews.services.crawler import SiteCrawler  # noqa: E402


def main() -> None:
    """Load the site configuration and invoke the crawler for each entry."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        config = AppConfig.from_file()
    except FileNotFoundError as exc:
        logging.error("Could not load site configuration: %s", exc)
        sys.exit(1)

    crawler = SiteCrawler()

    results = []
    for site in config.sites:
        logging.info("Crawling %s (%s)", site.name, site.url)
        try:
            result = crawler.fetch(
                site,
                use_sitemap=site.use_sitemap,
                sitemap_url=str(site.sitemap_url) if site.sitemap_url is not None else None,
                filter_path=site.filter_path,
            )
        except requests.RequestException as exc:
            logging.error("Failed to crawl %s: %s", site.url, exc)
            continue
        results.append(result.model_dump())
        logging.info("Found %d candidate articles", len(result.articles))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
