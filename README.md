# Tech Pulse

A phone-first app for tech headlines, rumors ("Word on the street") and a weekly watchlist of 5 tickers.
A Python script collects the data twice a day on GitHub, and the app on your iPhone reads it.

```
RSS feeds + Reddit + Hacker News ─┐
                                  ├─► pipeline/build_briefing.py ─► data/briefing.json ─► app (index.html)
Stock prices + earnings (yfinance)┘          (runs on GitHub Actions)        (hosted free on GitHub Pages)
```

## What's in here

| File | What it does |
|---|---|
| `index.html` | The app: Today, Watchlist, Street, Topics, Saved |
| `pipeline/build_briefing.py` | Fetches news, groups rumors, scores tickers, writes `data/briefing.json` |
| `pipeline/config.py` | **The file to edit**: feeds, rumor words, topics, ticker list |
| `pipeline/test_build.py` | Offline test with made-up data (no internet needed) |
| `.github/workflows/update-briefing.yml` | Runs the pipeline automatically at ~6 AM and ~5 PM Central |
| `sw.js`, `manifest.webmanifest`, `icons/` | Make it installable on your home screen and work offline |

Until the pipeline has run once, the app shows **sample data** (marked with a "Sample data" badge).

---

## Step 1: Run it on your computer

Open a terminal in this folder.

```bash
# Create a virtual environment (keeps packages for this project separate)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r pipeline/requirements.txt

python pipeline/test_build.py      # should end with "All checks passed."
python pipeline/build_briefing.py  # fetches real data, writes data/briefing.json

python -m http.server 8000         # then open http://localhost:8000 in your browser
```

## Step 2: Put it on GitHub

1. On github.com, create a new **public** repository named `tech-pulse` (no README, so it's empty).
2. In this folder, run (replace `YOUR-USERNAME`):

```bash
git init
git add .
git commit -m "First version of Tech Pulse"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/tech-pulse.git
git push -u origin main
```

3. **Turn on hosting:** repo **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder `/ (root)` → Save.
4. **Let the bot save data:** repo **Settings → Actions → General** → Workflow permissions → *Read and write permissions* → Save.
5. **Run it now:** **Actions** tab → *Update briefing* → **Run workflow**. After about 1–2 minutes, `data/briefing.json` appears in the repo.

## Step 3: Install it on your iPhone

1. Open **Safari** and go to `https://YOUR-USERNAME.github.io/tech-pulse/`
2. Tap **Share** → **Add to Home Screen** → **Add**.

It now opens full-screen from its own icon, and refreshes its data each time you open it.

## Optional: AI-written summary

By default the "This week in 30 seconds" box is written by simple rules. For a smarter summary written by Claude:

1. Get an API key at console.anthropic.com (usage is billed, but this costs pennies per month).
2. Repo **Settings → Secrets and variables → Actions → New repository secret**
   Name: `ANTHROPIC_API_KEY`, value: your key.

Never put the key in a file in the repo, since the repo is public.

---

## How the scores work

**Rumor strength (0–100)**
- Independent sources reporting it: 40 points (maxes out at 10 sources)
- Established outlets among them: 35 points (maxes out at 5)
- Total chatter, log-scaled so hype alone can't win: 25 points (maxes out at 50 mentions)

**Watchlist (top 5 of ~30 tech tickers)**
- Earnings report in the next 7 days: 40 points
- Headlines mentioning the company: 5 points each, up to 30
- Size of this week's price move: up to 20 points
- Trading volume above its 20-day average: up to 10 points

The watchlist shows what has something happening this week. It is not a prediction or investment advice.

## Ideas for next steps

- Add or remove feeds and tickers in `pipeline/config.py`
- Push notifications when a rumor crosses 75
- A "Details" screen per ticker with a bigger chart
- Track how rumors changed over the week (save past briefings)

## Troubleshooting

- **App still says "Sample data"**: the workflow hasn't run yet, or Pages is still deploying. Check the Actions tab.
- **A feed shows "skipped" in the log**: that site blocked or timed out. The rest still work. Reddit often blocks automated requests.
- **Changed `index.html` but your phone shows the old app**: bump `VERSION` in `sw.js` (e.g. `tech-pulse-v2`), push, then close and reopen the app.
