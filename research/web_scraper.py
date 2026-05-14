"""
Web scraper for public prop firm pages, blogs, and support articles.
Generic: pass any {label: url} dict to scrape multiple sources.
"""
import logging
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from research.models import WebResult

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}


def _clean_text(text: str, max_chars: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _fetch_page(url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        return soup
    except Exception as exc:
        logger.warning("Fetch error (%s): %s", url, exc)
        return None


def _extract_article_links(soup: BeautifulSoup, base_url: str, limit: int = 8) -> list[str]:
    """Extract links from a blog/index page that look like article URLs."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Make absolute
        if href.startswith("/"):
            # Extract base domain
            parts = base_url.split("/")
            href = f"{parts[0]}//{parts[2]}{href}"
        elif not href.startswith("http"):
            continue
        # Must share domain with base_url and look like an article
        domain = base_url.split("/")[2]
        if domain in href and href != base_url:
            links.add(href)
        if len(links) >= limit:
            break
    return list(links)


def _scrape_single(source_label: str, url: str, keywords: list[str]) -> list[WebResult]:
    """Scrape one URL, returning results for any keyword hit."""
    soup = _fetch_page(url)
    if soup is None:
        return []

    title = soup.title.string.strip() if soup.title else url
    body_text = _clean_text(soup.get_text(separator=" "))

    # Check keyword relevance
    lower_body = body_text.lower()
    hits = [kw for kw in keywords if kw.lower() in lower_body]
    if not hits:
        return []

    # Extract a relevant snippet (first 500 chars around first hit)
    first_kw = hits[0].lower()
    idx = lower_body.find(first_kw)
    snippet = body_text[max(0, idx - 100): idx + 400].strip()

    return [WebResult(
        source=source_label,
        title=title,
        url=url,
        snippet=snippet,
        topic=", ".join(hits[:3]),
    )]


def scrape_web_sources(
    sources: dict[str, str],
    keywords: list[str],
    follow_article_links: bool = True,
    articles_per_source: int = 6,
    delay: float = 1.5,
) -> list[WebResult]:
    """
    Scrape all provided URLs for keyword matches.

    Args:
        sources: Dict mapping human label → URL.
        keywords: List of keywords to search for in page content.
        follow_article_links: If True, also follow article links found on index pages.
        articles_per_source: Max article sub-pages to follow per source.
        delay: Seconds between requests.

    Returns:
        List of WebResult objects, one per relevant page/article found.
    """
    results: list[WebResult] = []
    seen_urls: set[str] = set()

    for label, url in sources.items():
        time.sleep(delay)
        logger.info("Scraping: %s (%s)", label, url)

        # Scrape the index/main page
        main_results = _scrape_single(label, url, keywords)
        for r in main_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                results.append(r)

        # Follow article sub-links
        if follow_article_links:
            soup = _fetch_page(url)
            if soup:
                article_urls = _extract_article_links(soup, url, limit=articles_per_source)
                for art_url in article_urls:
                    if art_url in seen_urls:
                        continue
                    time.sleep(delay)
                    art_results = _scrape_single(label, art_url, keywords)
                    for r in art_results:
                        if r.url not in seen_urls:
                            seen_urls.add(r.url)
                            results.append(r)

    logger.info("Web scraper: collected %d relevant pages", len(results))
    return results
