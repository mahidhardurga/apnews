# AP News (apnews.mahidhardurga.in)

Andhra Pradesh news headline aggregator (all topics, filterable by topic and district). Fully static: a Python scraper runs in GitHub Actions, writes JSON into the repo, and a static site on GitHub Pages reads it. No server, no database.

Target domain: `apnews.mahidhardurga.in`

> **Mode: headlines only.** The scraper stores just the title, link, outlet, time, language, plus a keyword-derived topic and district. The site is one list; clicking a headline opens the original article on the outlet's site. Story grouping, tags, leader/district/trending/digest pages are kept as opt-in code (see "Advanced mode") but are not used or deployed by default.

## Layout

```
.github/workflows/scrape.yml   cron every 30 min + manual; commits data back, then starts deploy
.github/workflows/deploy.yml   builds /web and deploys to GitHub Pages
scraper/
  sources.yaml                 source registry (enable/disable, feed URLs)
  requirements.txt
  apnews/
    run.py                     entry point
    http.py                    robots.txt, per-host rate limit, retries
    store.py                   dedupe + latest.json / archive / state.json
    sources/                   one module per outlet
web/                           Astro + Tailwind static site (output: static)
  public/CNAME                 apnews.mahidhardurga.in (copied into the build)
  public/data/                 JSON written by the scraper (read by the site)
```

## Setup

1. Create a **public** GitHub repo and push this folder to `main`.
2. **Actions permissions:** Settings → Actions → General → Workflow permissions → *Read and write permissions*. (The workflow also declares `contents: write`.)
3. No secrets are needed.
4. Run it once: Actions → *scrape* → *Run workflow*. Afterwards `web/public/data/latest.json` appears in the repo.

### Enable GitHub Pages and the custom domain

1. Repo → Settings → **Pages** → *Build and deployment* → **Source: GitHub Actions**.
2. Push to `main` (or run Actions → *deploy* → *Run workflow*). The first deploy works even before any data exists.
3. In the same Pages settings, set **Custom domain** to `apnews.mahidhardurga.in`. (`web/public/CNAME` already contains it, so it survives every deploy.)
4. **DNS** at your domain provider for `mahidhardurga.in`, add:

   | Type | Name / Host | Value |
   |---|---|---|
   | `CNAME` | `apnews` | `<your-github-username>.github.io` |

   Do not include the repo name in the value. Wait for DNS, then tick **Enforce HTTPS** in Pages settings (the certificate can take up to an hour).
5. Verify the domain under your GitHub account → Settings → Pages (optional but prevents domain takeover).

### How data reaches the site

`scrape.yml` commits new JSON, then starts `deploy.yml` (commits made with `GITHUB_TOKEN` do not trigger push workflows, so it dispatches it explicitly). Each deploy bakes the RSS feed from the current data, and the home page fetches `/data/latest.json` in the browser at runtime. To show new data *between* deploys, build with `PUBLIC_DATA_BASE=https://raw.githubusercontent.com/<user>/<repo>/main/web/public/data` (CORS-enabled, cached ~5 min by GitHub).

## Frontend (`web/`)

```bash
cd web
npm install
npm run dev        # http://localhost:4321 (reads web/public/data)
npm run build      # -> web/dist
```

Pages: headline list with a topic dropdown and filters (district, outlet, language, time) plus Fuse.js search; district tile map (`/districts/`, optional topic filter; schematic, not real boundaries); about; `sitemap.xml`; `rss.xml` (items link to the original articles); Open Graph/Twitter tags (one shared 1200x630 `og.png`). English/Telugu toggle and dark mode are remembered in `localStorage`.

Note: `data/` is published with the site, including `archive/`, so the 1 GB Pages limit applies to it (headline archives are small).

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r scraper/requirements.txt   # light: no ML
cd scraper
python -m apnews.run                 # all enabled sources
python -m apnews.run --only sakshi   # one source
python -m apnews.run --dry-run       # fetch and report, write nothing
python -m apnews.run --stories      # advanced: grouping + tags (pip install -r scraper/requirements-stories.txt)
```

## Pipeline (each run)

1. Fetch each enabled source (RSS), keep title + URL + outlet + time + language.
2. Dedupe by canonical URL and by near-identical title (same language).
3. Write `web/public/data/latest.json` (newest 2000 headlines, i.e. the last 7 days), `articles.json` (7-day pool), `archive/YYYY-MM.json` and `state.json`.

No ML, no LLM, no secrets. A run takes seconds. Only what outlets still list in their feeds can be collected, so the 7 days fill up gradually after launch (history is not back-filled).

## Data files (`web/public/data/`)

| File | Contents |
|---|---|
| `latest.json` | newest 2000 headlines (last 7 days): `id, title, url, source, source_name, language, published, topic, district` |
| `articles.json` | rolling 7-day pool (internal) |
| `archive/YYYY-MM.json` | every headline seen, by month |
| `state.json` | seen IDs (14 days) and the last run's per-source report |

## Advanced mode (optional, not deployed)

`python -m apnews.run --stories` additionally groups articles into stories with multilingual embeddings (`intfloat/multilingual-e5-small`, chosen over the MiniLM model from the brief because that one was not trained on Telugu and scored unrelated Telugu headlines 0.90+ similar), tags them from `scraper/lexicon.yaml`, and writes story/leader/district/trending/digest JSON (an LLM backend is available with `ENRICH_BACKEND=llm`). It needs `scraper/requirements-stories.txt` and set excerpts on in `sources.yaml` (`excerpt_chars: 280`). It overwrites `latest.json` with a different shape, so the frontend pages for it live in `web/src/_advanced/pages/` (move them back into `web/src/pages/` to use them).

## Adding a source

1. Check the outlet's `robots.txt` and terms. Prefer an RSS feed.
2. Add an entry to `scraper/sources.yaml` with `module: my_outlet`, `enabled: true`, and its `feeds`.
3. Create `scraper/apnews/sources/my_outlet.py`:
   ```python
   from .base import Source

   class Impl(Source):
       pass   # generic RSS works as-is
   ```
   Override `keep(url, entry)` to filter items, `excerpt_from(entry)` to change the excerpt, or `fetch()` to scrape HTML with `self.http.get(url)` (this keeps robots.txt and rate limiting). `fetch()` must return a list of dicts built with `self.to_article(...)`-style fields.
4. Test: `python -m apnews.run --only my_outlet --dry-run`.

A failing source is logged and skipped; the run only fails if every source fails.

## Source status

| Source | State |
|---|---|
| The Hindu (AP) | working, RSS |
| TV9 Telugu (AP) | working, RSS |
| NTV Telugu (AP) | working, RSS |
| 10TV (AP) | working, RSS (extra, not in the original list) |
| Eenadu | working via its news sitemap (robots.txt explicitly allows `/sitemap-news.xml`), AP section only |
| Andhra Jyothy | working via the news sitemap listed in its robots.txt, AP section only |
| The Indian Express | working, but the AP-filtered result is small (national feed + keyword filter) |
| Sakshi | working, but its only feed is site-wide, so ~1 AP item per run |
| Deccan Chronicle | blocked: every feed URL returns HTTP 403 to our bot; not bypassed |
| Times of India | not added: AP city feed URLs not found (the Hyderabad feed is not AP) |
| ABN | not added: site unreachable from the build machine |
| CEO Andhra Pradesh | **not scrapable**: its robots.txt is `Disallow: /` for all bots |
| AP Govt press releases | not added: the IPR site is a JavaScript app with no static pages or feed |

Reasons are also recorded as `notes:` in `scraper/sources.yaml`. To add a news-sitemap source, subclass `NewsSitemapSource` (see `sources/eenadu.py`).
