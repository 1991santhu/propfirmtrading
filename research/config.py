"""
Default search configuration.
Import and override any of these in your own scripts to reuse for other topics.
"""

# Subreddits to search (in priority order)
DEFAULT_SUBREDDITS = [
    "propfirms",
    "FuturesTrading",
    "Daytrading",
    "algotrading",
    "Tradovate",
    "StockMarket",
]

# Topic buckets: each key becomes a section in the report.
# Values are keyword lists — a post is assigned to the FIRST bucket that matches.
DEFAULT_TOPICS = {
    "Payout Scaling ($1M/month strategies)": [
        "million payout",
        "1 million",
        "scale funded",
        "multiple accounts",
        "trade copier",
        "horizontal scaling",
        "vertical scaling",
        "100 accounts",
        "50 accounts",
        "copy trade",
        "mass scale",
    ],
    "LucidTrading / LucidFlex": [
        "LucidTrading",
        "LucidFlex",
        "lucid trading",
        "lucid flex",
    ],
    "Tradeify": [
        "Tradeify",
        "tradeify",
    ],
    "The Trading Pit (TPT)": [
        "Trading Pit",
        "TPT prop",
        "thetradingpit",
    ],
    "Prop Firm Payouts & Rules": [
        "payout prop",
        "funded payout",
        "withdrawal funded",
        "consistency rule",
        "trailing drawdown",
        "eval pass",
        "evaluation rules",
        "funded account rules",
        "prop firm fees",
        "eval cost",
    ],
    "MNQ / Micro Nasdaq Futures": [
        "/MNQ",
        "MNQ futures",
        "Micro Nasdaq",
        "mnq",
        "micro NQ",
    ],
    "ORB / Key Level Strategies": [
        "opening range breakout",
        "ORB strategy",
        "PDH PDL",
        "previous day high",
        "key levels futures",
        "breakout retest",
        "orb futures",
    ],
    "EMA Cloud / Ripster": [
        "EMA cloud",
        "Ripster",
        "ema clouds",
        "ripster clouds",
    ],
    "Prop Firm Automation / Bots": [
        "TradingView webhook",
        "prop firm bot",
        "automated prop",
        "algo funded",
        "tradovate bot",
        "tradovate automation",
        "webhook bot",
    ],
}

# Public web pages to scrape (source label → URL)
DEFAULT_WEB_SOURCES = {
    "LucidTrading - Funded Rules": (
        "https://support.lucidtrading.com/en/articles/12945795-lucidflex-funded-account"
    ),
    "LucidTrading - Eval Rules": (
        "https://support.lucidtrading.com/en/collections/16914631-lucidflex"
    ),
    "Tradeify Blog": "https://www.tradeify.com/blog",
    "The Trading Pit Blog": "https://www.thetradingpit.com/blog",
    "Apex Trader Funding Blog": "https://apextraderfunding.com/blog",
    "MyFundedFutures Blog": "https://www.myfundedfutures.com/blog",
}
