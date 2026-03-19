# Company Career Scout

AI-powered company reputation analysis tool built exclusively for Sri Lankan companies.

Uses LangGraph and LangChain to orchestrate parallel web crawlers that aggregate public company data from 8 sources, then analyzes and presents structured insights via a Streamlit dashboard.

---

## Architecture

```
Input Validator → Parallel Crawlers (8 sources) → SL Validation Filter → LLM Analysis → Report Builder
```

**LangGraph StateGraph** with 5 nodes:
1. **Input Validator** — normalizes company name, resolves aliases, enriches queries
2. **Parallel Crawlers** — async fan-out to Reddit, Google Maps, Glassdoor, SL Job Boards, LinkedIn, Facebook, SL News, General Web
3. **SL Validation Filter** — enforces Sri Lanka geo-scoping + deduplication
4. **Analysis Agent** — LLM-based sentiment, theme, severity classification per result
5. **Report Builder** — assembles source-sorted structured report

---

## Data Sources

| Source | Method | Max Results |
|--------|--------|-------------|
| Reddit (r/srilanka, r/colombo, r/askSriLanka) | PRAW API | 30 posts + comments |
| Google Maps | Playwright headless | 20 reviews |
| Glassdoor / Indeed | Playwright + scraping | 40 reviews |
| TopJobs / Ikman / JobsNet | httpx + BS4 | 30 listings |
| LinkedIn | Google search proxy | 10 results |
| Facebook | Google search proxy | 15 results |
| SL News (dailymirror.lk, etc.) | httpx + BS4 | 20 articles |
| General Web | Brave/SerpAPI/Google | 10 results |

---

## Multi-Model LLM Support

| Provider | Model | Cost |
|----------|-------|------|
| Groq (default) | Llama 3.3 70B | Free |
| Google Gemini | gemini-2.0-flash | Free |
| Anthropic Claude | claude-haiku-4-5 | Free credits |
| OpenAI | gpt-4o-mini | Paid |

Switch models via the sidebar dropdown. API keys stored in session only.

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd company-career-scout
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env with your API keys (at minimum, add GROQ_API_KEY)
```

Or enter keys directly in the Streamlit sidebar at runtime.

### 3. Run

```bash
streamlit run frontend/app.py
```

---

## Project Structure

```
agents/
  orchestrator.py          # LangGraph StateGraph pipeline
  analysis_agent.py        # LLM sentiment/theme classification
  report_builder.py        # Source-sorted report assembly
  crawlers/
    base_crawler.py        # BaseCrawler + RawResult
    reddit_crawler.py
    google_maps_crawler.py
    glassdoor_crawler.py
    topjobs_crawler.py     # topjobs.lk, ikman.lk, jobsnet.lk
    linkedin_crawler.py
    facebook_crawler.py
    news_crawler.py        # SL news sites
    web_crawler.py         # Brave/SerpAPI fallback
core/
  model_router.py          # Multi-provider LLM switcher
  sl_validator.py          # Sri Lanka validation + crisis detection
  cache.py                 # SQLite cache (48h TTL)
  deduplicator.py          # Sentence-transformer dedup
frontend/
  app.py                   # Streamlit main
  sidebar.py               # Model selector UI
  components/
    source_tab.py          # Per-source result cards
    score_gauge.py         # Plotly gauge + pie chart
    export.py              # JSON/CSV/PDF export
data/
  company_aliases.json     # SL company alias mappings
  demo_companies.json      # Pre-loaded demo companies
```

---

## Features

- **Sri Lanka-only scoping**: every query, scrape, and result is validated for SL relevance
- **48-hour intelligent caching**: SQLite-backed, re-scrape only when stale
- **Sinhala/Tamil support**: language detection and translation
- **Crisis detection**: flags mass layoffs, legal proceedings, financial distress, regulatory actions
- **12 theme categories**: salary, WLB, management, product quality, and more
- **Export**: JSON, CSV, PDF report download
- **Token tracking**: per-run LLM usage logged to SQLite

---

## License

MIT
