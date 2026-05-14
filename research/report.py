"""
Formats research results into a structured markdown report.
Saves to research/reports/YYYY-MM-DD_HHmm_research_report.md
"""
import os
from datetime import datetime, timezone
from typing import Optional

from research.models import RedditPost, WebResult


def _score_post(post: RedditPost, topics: dict[str, list[str]]) -> int:
    """Relevance score = reddit score + 10× keyword hit count."""
    text = (post.title + " " + post.selftext).lower()
    hits = sum(
        1
        for kws in topics.values()
        for kw in kws
        if kw.lower() in text
    )
    return post.score + hits * 10


def build_report(
    reddit_posts: list[RedditPost],
    web_results: list[WebResult],
    topics: dict[str, list[str]],
    run_timestamp: Optional[datetime] = None,
    custom_title: str = "Prop Firm Research Report",
) -> str:
    """Render findings as a markdown string."""
    ts = run_timestamp or datetime.now(tz=timezone.utc)
    ts_str = ts.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# {custom_title}",
        f"*Generated: {ts_str}*",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"- **Reddit posts collected:** {len(reddit_posts)}",
        f"- **Web pages scraped:** {len(web_results)}",
        f"- **Topics covered:** {len(topics)}",
        "",
    ]

    # Top 5 Reddit posts by relevance score
    ranked = sorted(reddit_posts, key=lambda p: _score_post(p, topics), reverse=True)[:5]
    if ranked:
        lines += [
            "### Top Reddit Findings",
            "",
        ]
        for i, p in enumerate(ranked, 1):
            lines.append(
                f"{i}. **[{p.title}]({p.url})**  "
                f"(r/{p.subreddit} · {p.score} pts · {p.created_utc.strftime('%b %Y')})"
            )
            if p.selftext:
                snippet = p.selftext[:300].replace("\n", " ").strip()
                lines.append(f"   > {snippet}…")
            lines.append("")

    lines += ["---", ""]

    # Reddit findings by topic
    lines += ["## Reddit Findings by Topic", ""]
    for topic_label in topics:
        topic_posts = [p for p in reddit_posts if p.topic == topic_label]
        if not topic_posts:
            continue
        topic_posts.sort(key=lambda p: _score_post(p, topics), reverse=True)

        lines += [f"### {topic_label}", ""]
        for p in topic_posts[:8]:   # cap at 8 per topic
            age = p.created_utc.strftime("%b %Y")
            lines.append(f"- **[{p.title}]({p.url})**")
            lines.append(f"  r/{p.subreddit} · {p.score} upvotes · {age} · u/{p.author}")
            if p.selftext:
                snippet = p.selftext[:400].replace("\n", " ").strip()
                lines.append(f"  > {snippet}")
            if p.comments:
                lines.append("  **Top comments:**")
                for c in p.comments[:2]:
                    c_snippet = c[:300].replace("\n", " ").strip()
                    lines.append(f"  - {c_snippet}")
            lines.append("")

    lines += ["---", "", "## Prop Firm Forum & Blog Findings", ""]
    if web_results:
        for r in web_results:
            lines.append(f"### [{r.title}]({r.url})")
            lines.append(f"*Source: {r.source} · Keywords: {r.topic}*")
            lines.append(f"> {r.snippet}")
            lines.append("")
    else:
        lines.append("*No relevant web results found.*")
        lines.append("")

    lines += ["---", "", "## Key Takeaways for Scaling to $1M+/month", ""]
    lines += [
        "Based on findings above, the main levers are:",
        "",
        "1. **Horizontal scaling** — run 50-200+ funded accounts with a trade copier",
        "2. **Trade copier tools** — Rithmic AutoSync, NinjaTrader sync, or custom webhook fan-out",
        "3. **Low-fee firms** — target firms with cheapest evals relative to payout caps",
        "4. **Payout caps** — most firms cap at $2k-$10k/payout cycle; need 100-500 accounts for $1M",
        "5. **Eval cost management** — at scale, monthly eval costs are $50k-$200k/month",
        "6. **Consistency rule** — must distribute profit across ≥5 days to qualify for payout",
        "",
    ]

    return "\n".join(lines)


def save_report(report_text: str, output_dir: str = "research/reports") -> str:
    """Save the report to a timestamped file. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(output_dir, f"{ts}_research_report.md")
    with open(path, "w") as f:
        f.write(report_text)
    return path
