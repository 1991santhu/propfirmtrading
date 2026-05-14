"""
Reddit search client.
Uses PRAW (authenticated) if REDDIT_CLIENT_ID is set in env.
Falls back to Reddit's public JSON search API if not.
"""
import os
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from research.models import RedditPost

logger = logging.getLogger(__name__)

_PUBLIC_HEADERS = {
    "User-Agent": os.environ.get(
        "REDDIT_USER_AGENT", "PropResearchBot/1.0 (research tool)"
    )
}
_PUBLIC_SEARCH_URL = "https://www.reddit.com/r/{sub}/search.json"


def _praw_available() -> bool:
    return bool(
        os.environ.get("REDDIT_CLIENT_ID")
        and os.environ.get("REDDIT_CLIENT_SECRET")
    )


def _make_praw():
    import praw
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "PropResearchBot/1.0"),
    )


def _public_search(
    subreddit: str,
    query: str,
    limit: int = 10,
    time_filter: str = "year",
) -> list[RedditPost]:
    """Search using the public (unauthenticated) Reddit JSON API."""
    params = {
        "q": query,
        "sort": "relevance",
        "t": time_filter,
        "limit": limit,
        "restrict_sr": "true",
    }
    try:
        r = requests.get(
            _PUBLIC_SEARCH_URL.format(sub=subreddit),
            params=params,
            headers=_PUBLIC_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("Reddit public API error (%s/%s): %s", subreddit, query, exc)
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        posts.append(RedditPost(
            subreddit=subreddit,
            title=d.get("title", ""),
            url="https://reddit.com" + d.get("permalink", ""),
            score=d.get("score", 0),
            created_utc=datetime.fromtimestamp(
                d.get("created_utc", 0), tz=timezone.utc
            ),
            author=d.get("author", "[deleted]"),
            selftext=d.get("selftext", "")[:2000],
        ))
    return posts


def _praw_search(
    reddit,
    subreddit: str,
    query: str,
    limit: int = 10,
    time_filter: str = "year",
) -> list[RedditPost]:
    """Search using authenticated PRAW."""
    try:
        sub = reddit.subreddit(subreddit)
        results = []
        for submission in sub.search(query, sort="relevance", time_filter=time_filter, limit=limit):
            # Grab top 3 comments
            submission.comments.replace_more(limit=0)
            top_comments = [
                c.body[:500]
                for c in submission.comments.list()[:3]
                if hasattr(c, "body")
            ]
            results.append(RedditPost(
                subreddit=subreddit,
                title=submission.title,
                url=f"https://reddit.com{submission.permalink}",
                score=submission.score,
                created_utc=datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                ),
                author=str(submission.author),
                selftext=submission.selftext[:2000],
                comments=top_comments,
            ))
        return results
    except Exception as exc:
        logger.warning("PRAW error (%s/%s): %s", subreddit, query, exc)
        return []


def _build_or_query(keywords: list[str], max_terms: int = 4) -> str:
    """
    Combine keywords into a Reddit OR query to reduce API calls.
    Picks the most distinctive terms (shorter = more specific in Reddit search).
    e.g. ["LucidTrading", "LucidFlex"] -> 'LucidTrading OR LucidFlex'
    """
    chosen = keywords[:max_terms]
    return " OR ".join(f'"{kw}"' if " " in kw else kw for kw in chosen)


def search_reddit(
    subreddits: list[str],
    topics: dict[str, list[str]],
    posts_per_query: int = 8,
    time_filter: str = "year",
    delay_between_requests: float = 5.0,
) -> list[RedditPost]:
    """
    Search Reddit for all topics across subreddits.

    Each topic fires ONE batched OR-query per subreddit (not one per keyword),
    which keeps the total request count to len(topics) × len(subreddits).

    Returns deduplicated list of RedditPost objects with topic assigned.
    Prefers PRAW if credentials available, falls back to public API.

    Args:
        subreddits: List of subreddit names (no r/ prefix).
        topics: Dict mapping topic label → list of search keywords.
        posts_per_query: Max posts per (subreddit, topic) query.
        time_filter: Reddit time filter: "day","week","month","year","all".
        delay_between_requests: Seconds to sleep between API calls.
    """
    use_praw = _praw_available()
    reddit = _make_praw() if use_praw else None
    mode = "PRAW (authenticated)" if use_praw else "public JSON API"
    logger.info("Reddit client mode: %s", mode)

    seen_urls: set[str] = set()
    all_posts: list[RedditPost] = []

    total_queries = len(topics) * len(subreddits)
    done = 0

    for topic_label, keywords in topics.items():
        query = _build_or_query(keywords)
        for subreddit in subreddits:
            time.sleep(delay_between_requests)
            done += 1
            logger.info("[%d/%d] r/%s | %s", done, total_queries, subreddit, topic_label[:40])

            if use_praw:
                posts = _praw_search(reddit, subreddit, query, posts_per_query, time_filter)
            else:
                posts = _public_search(subreddit, query, posts_per_query, time_filter)

            for post in posts:
                if post.url not in seen_urls:
                    post.topic = topic_label
                    seen_urls.add(post.url)
                    all_posts.append(post)

    logger.info("Reddit: collected %d unique posts", len(all_posts))
    return all_posts
