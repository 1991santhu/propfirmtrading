"""Shared data models for research results."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RedditPost:
    subreddit: str
    title: str
    url: str
    score: int
    created_utc: datetime
    author: str
    selftext: str
    comments: list[str] = field(default_factory=list)
    relevance: int = 0      # keyword hit count (filled by researcher)
    topic: str = ""         # which topic bucket triggered this result


@dataclass
class WebResult:
    source: str             # human label, e.g. "LucidTrading Support"
    title: str
    url: str
    snippet: str
    topic: str = ""
