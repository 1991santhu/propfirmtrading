# Research Scraper Module

Standalone, reusable Reddit + web scraper for market research.  
Designed to be independent of the trading bot — can be used for any research topic.

---

## Quick Start

```bash
# Run with all defaults (Reddit public API + prop firm web pages)
python -m research.researcher

# Output saved to: research/reports/YYYY-MM-DD_HHMM_research_report.md
```

---

## Setup

### Optional: Reddit API credentials (recommended for richer data)

Without credentials the scraper uses Reddit's public JSON API (rate-limited to ~10 req/min).  
With credentials it uses PRAW (higher limits, includes post comments).

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"Create App"** → type: **script**
3. Name it anything, redirect URI: `http://localhost:8080`
4. Copy the **client ID** (under the app name) and **client secret**
5. Add to `.env`:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=PropResearchBot/1.0
```

---

## CLI Usage

```bash
# Full run (Reddit + web scraping)
python -m research.researcher

# Custom time window
python -m research.researcher --time month     # last month only
python -m research.researcher --time year      # last year (default)
python -m research.researcher --time all       # all time

# More posts per query
python -m research.researcher --posts 10

# Specific subreddits only
python -m research.researcher --subreddits propfirms FuturesTrading algotrading

# Reddit only (skip web scraping)
python -m research.researcher --no-web

# Web only (skip Reddit)
python -m research.researcher --no-reddit

# Custom output directory
python -m research.researcher --output ~/research_reports/

# Custom report title
python -m research.researcher --title "LucidFlex Payout Research"
```

---

## Default Topics Searched

| Topic | Keywords Used |
|-------|--------------|
| Payout Scaling ($1M/month) | "multiple accounts", "trade copier", "horizontal scaling", "copy trade" |
| LucidTrading / LucidFlex | "LucidTrading", "LucidFlex", "lucid trading" |
| Tradeify | "Tradeify" |
| The Trading Pit (TPT) | "Trading Pit", "TPT prop", "thetradingpit" |
| Prop Firm Payouts & Rules | "payout prop", "consistency rule", "trailing drawdown", "eval pass" |
| MNQ / Micro Nasdaq | "/MNQ", "MNQ futures", "Micro Nasdaq" |
| ORB / Key Level Strategies | "opening range breakout", "ORB strategy", "breakout retest" |
| EMA Cloud / Ripster | "EMA cloud", "Ripster", "ema clouds" |
| Prop Firm Automation | "TradingView webhook", "prop firm bot", "tradovate automation" |

Default subreddits: `propfirms`, `FuturesTrading`, `Daytrading`, `algotrading`, `Tradovate`, `StockMarket`

---

## Customizing for Other Use Cases

```python
from research.researcher import run_research

# Custom topics (any subject)
my_topics = {
    "Topic A": ["keyword1", "keyword two", "keyword3"],
    "Topic B": ["other terms", "related phrase"],
}

# Custom web pages to scrape
my_sources = {
    "My Source": "https://example.com/blog",
    "Another Site": "https://other.com/articles",
}

path = run_research(
    subreddits=["investing", "personalfinance"],
    topics=my_topics,
    web_sources=my_sources,
    time_filter="month",
    posts_per_query=10,
    report_title="My Custom Research",
    output_dir="my_reports/",
)
print(f"Report saved: {path}")
```

---

## Module Structure

| File | Purpose |
|------|---------|
| `config.py` | Default subreddits, topics, and web URLs |
| `models.py` | `RedditPost` and `WebResult` dataclasses |
| `reddit_client.py` | PRAW + public JSON API Reddit search |
| `web_scraper.py` | `requests` + `BeautifulSoup` page scraper |
| `researcher.py` | CLI orchestrator and `run_research()` function |
| `report.py` | Markdown report formatter + file writer |
| `reports/` | Generated reports (timestamped markdown files) |

---

## Key Research Findings (May 2026 Run)

From the initial run across 6 subreddits × 9 topics (147 posts, 14 web pages):

**Scaling to $1M+/month:**
- Top traders run 3-20 funded accounts via Tradovate's built-in Group Trade (copy trade) feature
- [TradeSyncer](https://www.reddit.com/r/Daytrading/comments/1qyl3cj/tradesyncer_multiple_accounts/) is a popular copy-trade platform for grouping Apex + Tradeify accounts
- At $2k payout cap per cycle, need 500+ accounts for $1M/month — cost: ~$200k+/month in eval fees

**What actually works for MNQ prop trading:**
- ["3 Months, 0 Red Days, $20k in payouts"](https://reddit.com/r/Daytrading/comments/1qsydiq) — used fixed small risk + copy traded 3 accounts
- Strategy: keep it boring, single setup, walk away after entry, let trade run
- ["After 5 years of trading mistakes"](https://reddit.com/r/Daytrading/comments/1rullr6) — the key insight: stick to ONE strategy, no deviation

**Consistency rule reality:**
- ["I hate myself rn"](https://reddit.com/r/Daytrading/comments/1kti3ng) — trader made too much profit in one trade, violated consistency rule, couldn't count it toward target
- The solution: cap single-trade size, spread P&L across days
- Tradeify: 25% rule (no day > 25% of total) — stricter than LucidFlex's 50%

**Prop firm reliability:**
- [OFP refused payout despite full compliance](https://reddit.com/r/PropFirms/comments/1o7o3a8) — 10 months of trading, documentation, still denied. Stick to established firms.
- The Trading Pit: [trader reports being stopped out far from price](https://reddit.com/r/Daytrading/comments/1pkzkv5) — platform reliability concern
