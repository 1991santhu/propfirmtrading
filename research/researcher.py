"""
Standalone research orchestrator.

Usage:
    python -m research.researcher
    python -m research.researcher --time year --posts 8 --output research/reports/
    python -m research.researcher --subreddits propfirms FuturesTrading
    python -m research.researcher --no-web          # Reddit only
    python -m research.researcher --no-reddit       # Web only

All defaults come from research/config.py — override per-run via CLI flags.
Designed to be reusable: import run_research() and pass custom topics/subreddits/sources.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from research.config import DEFAULT_SUBREDDITS, DEFAULT_TOPICS, DEFAULT_WEB_SOURCES
from research.reddit_client import search_reddit
from research.web_scraper import scrape_web_sources
from research.report import build_report, save_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_research(
    subreddits: list[str] = None,
    topics: dict[str, list[str]] = None,
    web_sources: dict[str, str] = None,
    time_filter: str = "year",
    posts_per_query: int = 5,
    skip_reddit: bool = False,
    skip_web: bool = False,
    output_dir: str = "research/reports",
    report_title: str = "Prop Firm Research Report",
) -> str:
    """
    Run full research pipeline: Reddit search + web scraping → markdown report.

    Returns the path to the saved report file.
    """
    subreddits  = subreddits  or DEFAULT_SUBREDDITS
    topics      = topics      or DEFAULT_TOPICS
    web_sources = web_sources or DEFAULT_WEB_SOURCES

    # Flatten all keywords for web scraper
    all_keywords = [kw for kws in topics.values() for kw in kws]

    reddit_posts = []
    web_results  = []

    if not skip_reddit:
        logger.info("=== Reddit search: %d subreddits × %d topics ===",
                    len(subreddits), len(topics))
        reddit_posts = search_reddit(
            subreddits=subreddits,
            topics=topics,
            posts_per_query=posts_per_query,
            time_filter=time_filter,
        )
        logger.info("Reddit done: %d posts collected", len(reddit_posts))

    if not skip_web:
        logger.info("=== Web scraping: %d sources ===", len(web_sources))
        web_results = scrape_web_sources(
            sources=web_sources,
            keywords=all_keywords,
        )
        logger.info("Web done: %d pages collected", len(web_results))

    ts = datetime.now(tz=timezone.utc)
    report_text = build_report(
        reddit_posts=reddit_posts,
        web_results=web_results,
        topics=topics,
        run_timestamp=ts,
        custom_title=report_title,
    )

    path = save_report(report_text, output_dir=output_dir)
    logger.info("Report saved: %s", path)

    # Print short terminal summary
    _print_summary(reddit_posts, web_results, topics)

    return path


def _print_summary(reddit_posts, web_results, topics):
    print("\n" + "=" * 70)
    print("  RESEARCH SUMMARY")
    print("=" * 70)
    print(f"  Reddit posts: {len(reddit_posts)}")
    print(f"  Web pages:    {len(web_results)}")
    print()

    for topic_label in topics:
        posts = [p for p in reddit_posts if p.topic == topic_label]
        if not posts:
            continue
        print(f"  [{topic_label}]  {len(posts)} posts")
        top = sorted(posts, key=lambda p: p.score, reverse=True)[:2]
        for p in top:
            age = p.created_utc.strftime("%b %Y")
            title = p.title[:70] + "…" if len(p.title) > 70 else p.title
            print(f"    • [{p.score:>5}] {title}  ({age})")
        print()

    if web_results:
        print("  Web findings:")
        for r in web_results[:5]:
            print(f"    • {r.source}: {r.title[:60]}")

    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Research scraper — Reddit + prop firm forums"
    )
    parser.add_argument(
        "--subreddits", nargs="+", default=None,
        help="Override subreddit list (e.g. --subreddits propfirms FuturesTrading)"
    )
    parser.add_argument(
        "--time", default="year",
        choices=["day", "week", "month", "year", "all"],
        help="Reddit time filter (default: year)"
    )
    parser.add_argument(
        "--posts", type=int, default=5,
        help="Max posts per subreddit/keyword pair (default: 5)"
    )
    parser.add_argument(
        "--output", default="research/reports",
        help="Output directory for markdown report (default: research/reports)"
    )
    parser.add_argument(
        "--no-reddit", action="store_true",
        help="Skip Reddit search, run web scraping only"
    )
    parser.add_argument(
        "--no-web", action="store_true",
        help="Skip web scraping, run Reddit search only"
    )
    parser.add_argument(
        "--title", default="Prop Firm Research Report",
        help="Report title"
    )
    args = parser.parse_args()

    report_path = run_research(
        subreddits=args.subreddits,
        time_filter=args.time,
        posts_per_query=args.posts,
        skip_reddit=args.no_reddit,
        skip_web=args.no_web,
        output_dir=args.output,
        report_title=args.title,
    )
    print(f"\nFull report: {report_path}")
