"""Offline test: runs the pipeline on made-up feed items and prices (no internet needed).

Run:  python pipeline/test_build.py
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_briefing as bb  # noqa: E402

H = timedelta(hours=1)


def item(source, title, hours_ago, summary="Example summary text for testing."):
    return {"source": source, "title": title, "summary": summary,
            "url": f"https://example.com/{abs(hash(title))}", "published": bb.NOW - hours_ago * H}


news = [
    item("TechCrunch", "Nvidia unveils new AI accelerator with double the memory bandwidth", 2),
    item("The Verge", "Nvidia unveils its new AI accelerator with more memory bandwidth", 3),  # same story, other outlet
    item("Ars Technica", "Robotics startup raises $120M Series B to scale warehouse arms", 5),
    item("Wired", "Amazon cuts AWS GPU instance prices ahead of earnings", 8),
    item("Engadget", "New AR glasses ship with an on-device assistant", 20),
    item("TechCrunch", "Apple reportedly testing a foldable iPhone for next year", 30),
    item("The Verge", "Apple is said to be testing foldable iPhone prototypes", 40),
    item("Wired", "Foldable iPhone leak points to a 2027 launch for Apple", 60),
    item("Hacker News", "OpenAI reportedly in talks to acquire a chip startup", 6),
    item("Engadget", "Old story that is too old to show up", 200),
]
chatter = [
    item("r/apple", "Foldable iPhone prototype leaked photos from Apple supply chain", 10),
    item("r/technology", "Apple foldable iPhone testing rumor gains steam", 12),
    item("r/hardware", "Rumor: gaming GPU shortage coming next month", 4),
]

closes_up = [100, 101, 102, 101, 103, 104, 105, 106, 108, 110, 112]
closes_flat = [50.0] * 11
market = {
    "NVDA": {"closes": closes_up, "volumes": [1e6] * 10 + [3e6], "earnings": None},
    "AMZN": {"closes": closes_flat, "volumes": [1e6] * 11, "earnings": bb.NOW.date() + timedelta(days=2)},
    "AAPL": {"closes": closes_flat, "volumes": [1e6] * 11, "earnings": None},
    "IBM": {"closes": closes_flat, "volumes": [1e6] * 11, "earnings": date(2020, 1, 1)},
}

out = bb.build(news, chatter, market)
print(json.dumps(out, indent=2)[:3000])

titles = [s["title"] for s in out["stories"]]
assert sum("Nvidia" in t for t in titles) == 1, "duplicate story was not removed"
assert not any("reportedly" in t for t in titles), "rumor leaked into headlines"
assert not any("too old" in t for t in titles), "old story not filtered"
assert "foldable" in out["rumors"][0]["title"].lower(), "foldable rumor should rank first"
assert out["rumors"][0]["sources"] >= 4 and out["rumors"][0]["credible"] == 3
assert "AAPL" in out["rumors"][0]["tickers"]
tickers = [w["ticker"] for w in out["watchlist"]]
assert tickers[0] in ("AMZN", "NVDA") and "AMZN" in tickers[:2], tickers
assert out["watchlist"][tickers.index("AMZN")]["signals"][0] == "Earnings"
assert len(out["summary"]) >= 2
print("\nAll checks passed.")
