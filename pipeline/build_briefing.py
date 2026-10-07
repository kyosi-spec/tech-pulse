#!/usr/bin/env python3
"""Build data/briefing.json for the Tech Pulse app.

Run:  python pipeline/build_briefing.py
Optional: set ANTHROPIC_API_KEY to get an AI-written weekly summary.

Steps:
  1. Pull headlines from the RSS feeds in config.py
  2. Split them into confirmed news (Headlines) and rumors (Word on the Street)
  3. Group rumors about the same thing and count the evidence behind each
  4. Score tech tickers on this week's catalysts and keep the top 5
  5. Write everything to data/briefing.json, which the app reads
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "briefing.json"
HEADERS = {"User-Agent": "TechPulse/1.0 (personal news digest; +https://github.com)"}
NOW = datetime.now(timezone.utc)

STOPWORDS = set("""a an the and or but of to in on for with from by at as is are was were be been it its this that
these those new says say said will would can could may might than then into over after before about more most
their there they them his her our your you we he she not no yes how why what when who which while up down out
report reports reportedly rumor rumored leak leaked plans plan talks sources people familiar according
""".split())


# ---------------------------------------------------------------- helpers
def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def clean_text(raw: str, limit: int = 280) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def kw_pattern(words: list[str]) -> re.Pattern:
    """Whole-word match with simple endings: launch -> launches/launched/launching."""
    parts = [re.escape(w.strip()) + r"(?:s|es|d|ed|ing)?" for w in words]
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b", re.I)


TOPIC_RX = {name: kw_pattern(words) for name, words in config.TOPICS.items()}
KIND_RX = {name: kw_pattern(words) for name, words in config.KINDS.items()}
RUMOR_RX = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in config.RUMOR_WORDS) + ")", re.I)
COMPANY_RX = {t: kw_pattern(names) for t, names in config.WATCH_UNIVERSE.items()}


def tag_topic(text: str) -> str:
    hits = {name: len(rx.findall(text)) for name, rx in TOPIC_RX.items()}
    best = max(hits, key=hits.get)
    return best if hits[best] else "Tech"


def tag_kind(text: str) -> str:
    for name, rx in KIND_RX.items():
        if rx.search(text):
            return name
    return "Company"


def is_rumor(text: str) -> bool:
    return bool(RUMOR_RX.search(text))


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-\.]+", text.lower())
    return {w.strip(".-") for w in words if len(w) > 2 and w not in STOPWORDS}


def similar(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def companies_in(text: str) -> list[str]:
    return [t for t, rx in COMPANY_RX.items() if rx.search(text)]


def short_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


# ---------------------------------------------------------------- 1. fetch
def fetch_feed(name: str, url: str) -> list[dict]:
    import feedparser
    import requests

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:  # one bad feed shouldn't stop the run
        log(f"  ! skipped {name}: {exc}")
        return []
    feed = feedparser.parse(resp.content)
    items = []
    for e in feed.entries:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        published = datetime.fromtimestamp(time.mktime(stamp), timezone.utc) if stamp else NOW
        title = clean_text(e.get("title", ""), 200)
        if not title:
            continue
        items.append({
            "source": name,
            "title": title,
            "summary": clean_text(e.get("summary", "")),
            "url": e.get("link", ""),
            "published": published,
        })
    log(f"  {name}: {len(items)} items")
    return items


def fetch_all() -> tuple[list[dict], list[dict]]:
    log("Fetching news feeds…")
    news = [i for name, url in config.FEEDS for i in fetch_feed(name, url)]
    log("Fetching rumor feeds…")
    chatter = [i for name, url in config.RUMOR_FEEDS for i in fetch_feed(name, url)]
    return news, chatter


# ---------------------------------------------------------------- 2. stories
def same_story(a: set[str], b: set[str]) -> bool:
    return similar(a, b) >= 0.5 or (len(a & b) >= 3 and similar(a, b) >= 0.3)


def dedupe(items: list[dict]) -> list[dict]:
    """Drop near-identical headlines (the same story from several outlets), keeping the newest."""
    kept: list[dict] = []
    for item in sorted(items, key=lambda i: i["published"], reverse=True):
        kw = keywords(item["title"])
        if any(same_story(kw, keywords(k["title"])) for k in kept):
            continue
        kept.append(item)
    return kept


def build_stories(news: list[dict]) -> list[dict]:
    cutoff = NOW - timedelta(hours=config.STORY_MAX_AGE_HOURS)
    fresh = [i for i in news if i["published"] >= cutoff and not is_rumor(i["title"])]
    stories = []
    for item in dedupe(fresh)[: config.MAX_STORIES]:
        text = f'{item["title"]} {item["summary"]}'
        stories.append({
            "id": short_id(item["url"], item["title"]),
            "topic": tag_topic(text),
            "kind": tag_kind(text),
            "source": item["source"],
            "published": item["published"].isoformat(),
            "title": item["title"],
            "summary": item["summary"] or "No summary in the feed. Tap through to read the story.",
            "url": item["url"],
        })
    return stories


# ---------------------------------------------------------------- 3. rumors
def rumor_score(sources: int, credible: int, mentions: int) -> int:
    """Same formula as the app: sources 40%, established outlets 35%, chatter 25%."""
    src = min(sources, 10) / 10 * 40
    cred = min(credible, 5) / 5 * 35
    buzz = min(math.log10(mentions + 1) / math.log10(51), 1) * 25
    return round(src + cred + buzz)


def build_rumors(news: list[dict], chatter: list[dict]) -> list[dict]:
    everything = news + chatter
    cutoff = NOW - timedelta(days=config.RUMOR_MAX_AGE_DAYS)
    candidates = [i for i in everything if i["published"] >= cutoff and is_rumor(f'{i["title"]} {i["summary"][:120]}')]

    # Group rumor items that talk about the same thing.
    # An item joins a group when it closely matches any item already in it.
    clusters: list[dict] = []
    for item in sorted(candidates, key=lambda i: i["published"]):
        kw = keywords(item["title"])
        for c in clusters:
            if any(similar(kw, k) >= 0.3 or len(kw & k) >= 3 for k in c["kws"]):
                c["items"].append(item)
                c["kws"].append(kw)
                break
        else:
            clusters.append({"items": [item], "kws": [kw]})

    rumors = []
    for c in clusters:
        items = c["items"]
        core = keywords(items[0]["title"])
        # Chatter: every item anywhere (rumor-worded or not) that shares 3+ key words.
        mentions = sum(1 for i in everything if len(keywords(i["title"]) & core) >= 3)
        sources = {i["source"] for i in items}
        credible = len(sources & config.CREDIBLE)
        first = min(i["published"] for i in items)
        days = max((NOW - first).days, 0)
        lead = sorted(items, key=lambda i: (i["source"] not in config.CREDIBLE, -len(i["summary"])))[0]
        if credible >= 3 or len(sources) >= 5:
            status = "Gaining traction"
        elif days <= 1 and len(sources) <= 2:
            status = "Just surfaced"
        else:
            status = "Unconfirmed"
        text = " ".join(i["title"] for i in items)
        rumors.append({
            "id": short_id(lead["url"], lead["title"]),
            "topic": tag_topic(text),
            "status": status,
            "title": lead["title"],
            "detail": lead["summary"] or "Seen in: " + ", ".join(sorted(sources)),
            "url": lead["url"],
            "sources": len(sources),
            "mentions": max(mentions, len(items)),
            "credible": credible,
            "days": days,
            "tickers": companies_in(text),
            "score": rumor_score(len(sources), credible, max(mentions, len(items))),
        })
    rumors.sort(key=lambda r: r["score"], reverse=True)
    return rumors[: config.MAX_RUMORS]


# ---------------------------------------------------------------- 4. watchlist
def fetch_market(tickers: list[str]) -> dict:
    """Return {ticker: {closes, volumes, earnings}} using yfinance. Empty dict on failure."""
    try:
        import yfinance as yf
    except ImportError:
        log("  ! yfinance not installed; skipping watchlist")
        return {}
    log("Fetching market data…")
    try:
        data = yf.download(tickers, period="2mo", interval="1d", group_by="ticker",
                           auto_adjust=True, progress=False, threads=True)
    except Exception as exc:
        log(f"  ! market download failed: {exc}")
        return {}
    market = {}
    for t in tickers:
        try:
            frame = data[t].dropna()
            if len(frame) < 6:
                continue
            market[t] = {"closes": [float(x) for x in frame["Close"]],
                         "volumes": [float(x) for x in frame["Volume"]], "earnings": None}
        except Exception:
            continue
        try:
            cal = yf.Ticker(t).calendar
            dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
            if dates:
                d = dates[0]
                if isinstance(d, datetime):
                    d = d.date()
                market[t]["earnings"] = d if hasattr(d, "weekday") else None
        except Exception:
            pass
    log(f"  prices for {len(market)} of {len(tickers)} tickers")
    return market


def build_watchlist(market: dict, news: list[dict]) -> list[dict]:
    today = NOW.date()
    rows = []
    for ticker, m in market.items():
        closes, vols = m["closes"], m["volumes"]
        price, week_ago = closes[-1], closes[-6]
        change = (price - week_ago) / week_ago * 100
        avg_vol = sum(vols[-21:-1]) / max(len(vols[-21:-1]), 1)
        vol_ratio = vols[-1] / avg_vol if avg_vol else 1.0
        rx = COMPANY_RX[ticker]
        hits = [n for n in news if rx.search(n["title"])]
        earnings = m.get("earnings")
        days_to_earn = (earnings - today).days if earnings else None
        earn_soon = days_to_earn is not None and 0 <= days_to_earn <= 7

        score = (40 if earn_soon else 0) + min(len(hits), 6) * 5 \
            + min(abs(change) / 10, 1) * 20 + min(max(vol_ratio - 1, 0) / 2, 1) * 10

        signals = []
        if earn_soon:
            signals.append("Earnings")
        if len(hits) >= 2:
            signals.append(f"{len(hits)} headlines")
        if abs(change) >= 5:
            signals.append("Big price move")
        if vol_ratio >= 1.5:
            signals.append("Volume up")

        if earn_soon:
            catalyst, when = "Earnings report", earnings.strftime("%a")
        elif hits:
            latest = max(hits, key=lambda n: n["published"])
            catalyst, when = latest["title"], "In the news"
        elif abs(change) >= 5:
            catalyst, when = f"{'Up' if change > 0 else 'Down'} {abs(change):.0f}% this week", "Price"
        elif vol_ratio >= 1.5:
            catalyst, when = "Unusual trading volume", "Volume"
        else:
            catalyst, when = "No major catalyst yet", "Quiet"

        rows.append({
            "ticker": ticker,
            "name": config.NAMES.get(ticker, ticker),
            "price": round(price, 2),
            "changePct": round(change, 1),
            "catalyst": catalyst,
            "when": when,
            "signals": signals or ["Steady"],
            "spark": [round(c, 2) for c in closes[-7:]],
            "score": round(score, 1),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[: config.WATCHLIST_SIZE]


# ---------------------------------------------------------------- 5. summary
def summarize(stories: list[dict], rumors: list[dict], watch: list[dict]) -> list[str]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and stories:
        try:
            return ai_summary(key, stories, rumors, watch)
        except Exception as exc:
            log(f"  ! AI summary failed, using basic summary: {exc}")
    return basic_summary(stories, rumors, watch)


def basic_summary(stories, rumors, watch) -> list[str]:
    lines = []
    if stories:
        counts: dict[str, int] = {}
        for s in stories:
            counts[s["topic"]] = counts.get(s["topic"], 0) + 1
        top = max(counts, key=counts.get)
        lines.append(f"{top} leads the news with {counts[top]} of {len(stories)} stories. Top headline: {stories[0]['title']}")
    earners = [w["ticker"] for w in watch if "Earnings" in w["signals"]]
    if earners:
        lines.append(f"Earnings this week from {', '.join(earners)}.")
    elif watch:
        lines.append(f"Biggest catalyst on the watchlist: {watch[0]['ticker']}, {watch[0]['catalyst'].lower()}.")
    if rumors:
        lines.append(f"Strongest rumor: {rumors[0]['title']}")
    return lines or ["No new stories yet. Check back after the next update."]


def ai_summary(key, stories, rumors, watch) -> list[str]:
    import requests

    digest = "\n".join(f"- [{s['topic']}] {s['title']}" for s in stories[:20])
    digest += "\nRumors:\n" + "\n".join(f"- {r['title']} (strength {r['score']})" for r in rumors[:5])
    digest += "\nWatchlist:\n" + "\n".join(f"- {w['ticker']}: {w['catalyst']} ({w['changePct']:+}%)" for w in watch)
    prompt = ("You write a weekly tech briefing for one reader on their phone. From the items below, "
              "write exactly 3 short bullet points (max 25 words each) on what matters this week. "
              "Plain language, no hype, no investment advice. Return only the 3 lines, no bullets symbols.\n\n" + digest)
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.environ.get("TECH_PULSE_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 300,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    resp.raise_for_status()
    text = "".join(b.get("text", "") for b in resp.json()["content"])
    lines = [re.sub(r"^[\-\*•\d\.\)\s]+", "", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        raise ValueError("empty summary")
    return lines[:3]


# ---------------------------------------------------------------- main
def build(news: list[dict], chatter: list[dict], market: dict) -> dict:
    stories = build_stories(news)
    rumors = build_rumors(news, chatter)
    watch = build_watchlist(market, news + chatter)
    monday = (NOW - timedelta(days=NOW.weekday())).date()
    return {
        "weekOf": monday.isoformat(),
        "updated": NOW.isoformat(timespec="seconds"),
        "summary": summarize(stories, rumors, watch),
        "stories": stories,
        "rumors": rumors,
        "watchlist": watch,
    }


def main() -> None:
    news, chatter = fetch_all()
    if not news:
        log("No news fetched at all; keeping the previous briefing.json.")
        sys.exit(1)
    market = fetch_market(list(config.WATCH_UNIVERSE))
    briefing = build(news, chatter, market)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(briefing, indent=2, ensure_ascii=False))
    log(f"Wrote {OUT.relative_to(ROOT)}: {len(briefing['stories'])} stories, "
        f"{len(briefing['rumors'])} rumors, {len(briefing['watchlist'])} watchlist")


if __name__ == "__main__":
    main()
