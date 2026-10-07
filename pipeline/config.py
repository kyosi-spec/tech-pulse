"""Settings for the Tech Pulse pipeline. Edit these lists to change what the app covers."""

# News feeds: (display name, RSS url). Add or remove freely.
FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Wired", "https://www.wired.com/feed/category/business/latest/rss"),
    ("Engadget", "https://www.engadget.com/rss.xml"),
    ("Hacker News", "https://hnrss.org/frontpage?points=150"),
]

# Extra places where rumors tend to show up first. These count toward rumor
# scores but never appear in the Headlines list. Reddit sometimes blocks
# automated requests; the pipeline just skips a feed that fails.
RUMOR_FEEDS = [
    ("r/technology", "https://www.reddit.com/r/technology/top/.rss?t=day"),
    ("r/hardware", "https://www.reddit.com/r/hardware/top/.rss?t=day"),
    ("r/apple", "https://www.reddit.com/r/apple/top/.rss?t=day"),
    ("Hacker News (new)", "https://hnrss.org/newest?points=40"),
]

# Sources treated as "established outlets" in the rumor score.
CREDIBLE = {"TechCrunch", "The Verge", "Ars Technica", "Wired", "Engadget"}

# Words that mark a headline as a rumor rather than confirmed news.
RUMOR_WORDS = [
    "reportedly", "rumor", "rumour", "rumored", "rumoured", "leak", "leaked", "leaks",
    "in talks", "sources say", "people familiar", "said to be", "is said to",
    "could be", "may be planning", "plans to", "considering", "exploring a sale",
    "according to a report", "report says", "report:", "insider",
]

# Topic tags. The topic with the most keyword hits wins. Keywords match whole words,
# plus simple endings (launch -> launches, launched, launching).
TOPICS = {
    "AI": ["ai", "artificial intelligence", "openai", "anthropic", "llm", "chatgpt", "gemini",
           "model", "agent", "machine learning", "deepmind", "copilot"],
    "Chips": ["chip", "semiconductor", "gpu", "nvidia", "amd", "intel", "tsmc", "qualcomm", "arm holdings",
              "foundry", "processor", "wafer"],
    "Cloud": ["cloud", "aws", "azure", "data center", "datacenter", "server", "saas"],
    "Startups": ["startup", "raises", "funding", "series a", "series b", "series c", "seed round",
                 "valuation", "venture", "ipo", "acquire", "acquisition"],
    "Devices": ["iphone", "android", "pixel", "galaxy", "laptop", "headset", "glasses", "wearable",
                "watch", "tablet", "console", "macbook"],
    "Security": ["hack", "breach", "security", "ransomware", "vulnerability", "privacy", "malware"],
    "Policy": ["regulation", "regulators", "regulatory", "lawsuit", "antitrust", "ftc", "doj", "congress", "ban", "tariff", "export"],
}

# Story type tags.
KINDS = {
    "Launch": ["launch", "unveil", "announce", "release", "debut", "introduce", "introduces", "ship", "rolls out", "now available"],
    "Founder": ["founder", "raises", "funding", "series", "startup", "ceo", "co-founder", "seed"],
}

# Watchlist universe: ticker -> words that mean a headline is about this company.
WATCH_UNIVERSE = {
    "NVDA": ["nvidia"], "AMD": ["amd"], "INTC": ["intel"], "TSM": ["tsmc", "taiwan semiconductor"],
    "AVGO": ["broadcom"], "QCOM": ["qualcomm"], "ARM": ["arm holdings"], "MU": ["micron"],
    "ASML": ["asml"], "AAPL": ["apple", "iphone"], "MSFT": ["microsoft"], "GOOGL": ["google", "alphabet"],
    "AMZN": ["amazon", "aws"], "META": ["meta platforms", "facebook", "instagram", "zuckerberg"],
    "TSLA": ["tesla"], "ORCL": ["oracle"], "CRM": ["salesforce"], "ADBE": ["adobe"],
    "NFLX": ["netflix"], "PLTR": ["palantir"], "SNOW": ["snowflake"], "CRWD": ["crowdstrike"],
    "NET": ["cloudflare"], "SHOP": ["shopify"], "UBER": ["uber"], "COIN": ["coinbase"],
    "SMCI": ["supermicro", "super micro"], "DELL": ["dell"], "IBM": ["ibm"], "SPOT": ["spotify"],
}

# Display names for the watchlist.
NAMES = {
    "NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "TSM": "TSMC", "AVGO": "Broadcom", "QCOM": "Qualcomm",
    "ARM": "Arm Holdings", "MU": "Micron", "ASML": "ASML", "AAPL": "Apple", "MSFT": "Microsoft",
    "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "ORCL": "Oracle",
    "CRM": "Salesforce", "ADBE": "Adobe", "NFLX": "Netflix", "PLTR": "Palantir", "SNOW": "Snowflake",
    "CRWD": "CrowdStrike", "NET": "Cloudflare", "SHOP": "Shopify", "UBER": "Uber", "COIN": "Coinbase",
    "SMCI": "Supermicro", "DELL": "Dell", "IBM": "IBM", "SPOT": "Spotify",
}

# How many items each section keeps.
MAX_STORIES = 25
MAX_RUMORS = 8
WATCHLIST_SIZE = 5
STORY_MAX_AGE_HOURS = 72
RUMOR_MAX_AGE_DAYS = 10
