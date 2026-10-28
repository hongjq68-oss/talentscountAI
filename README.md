# TalentScout AI — Talent Sourcing Agent

An AI executive-recruiter agent with a modern ATS-style UI. Give it a job description (link, Word, PDF, Excel/CSV or pasted text) and it:

1. **Reads the JD** and runs an executive-search style **intake**: role profile, must-have / nice-to-have skills, ideal-candidate persona, selling points, red flags, intake questions and a weighted evaluation scorecard.
2. **Maps talent around the hiring firm**: hiring-company profile and current team patterns (incl. its public GitHub engineering footprint and, with a search key, benchmark profiles of people in similar roles there), tiered target companies (primary / secondary / adjacent), peer titles, talent hubs, market trends, common attributes and career paths.
3. **Builds the sourcing strategy**: skills matrix, channel plan, LinkedIn Recruiter Boolean, Google X-ray and GitHub search strings, one-click X-ray search links, outreach template and search timeline.
4. **Sources candidates** from GitHub (API), LinkedIn (X-ray via a search API) and the open web, then **scores and shortlists** them (skills, title/seniority, target-company, location and public-signal scoring; AI re-ranking with rationale, strengths, gaps and a personalised outreach hook when an LLM key is set).
5. Manage candidates in an ATS workflow: filterable candidate table, candidate profile drawer, drag-and-drop **pipeline** (Sourced → Shortlisted → Contacted → Interviewing → Offer → Hired / Rejected), notes, ratings, manual add, talent pool across searches and CSV export.

## Run

Requirements: Python 3.10+, Node 18+.

```bash
./start.sh            # builds the UI, serves UI + API on http://localhost:8000
```

Dev mode (hot reload): `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000` and `cd frontend && npm run dev` (http://localhost:5173, proxies `/api`).

## Integrations

Add keys in the app under **Integrations** (stored server-side in `backend/data/settings.json`) or as environment variables:

| Purpose | Variables (any one per group) |
| --- | --- |
| AI recruiter reasoning | `OPENAI_API_KEY` (+ `OPENAI_MODEL`, default `gpt-4o`) or `ANTHROPIC_API_KEY` (+ `ANTHROPIC_MODEL`) |
| LinkedIn / open-web X-ray search | `SERPER_API_KEY`, `TAVILY_API_KEY`, `BRAVE_API_KEY` or `SERPAPI_API_KEY` |
| GitHub rate limits | `GITHUB_TOKEN` (no scopes needed) |

Without keys the agent still works in **heuristic mode** (rule-based JD analysis, built-in industry/company knowledge, GitHub sourcing, and ready-to-run X-ray links for LinkedIn). LinkedIn is never scraped directly — profiles are found through search-engine X-ray queries.

Sample JDs are in `samples/` (`.txt`, `.docx`, `.xlsx`).
