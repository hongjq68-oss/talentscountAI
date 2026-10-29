"""Candidate discovery: GitHub API and web/LinkedIn X-ray search via pluggable search APIs."""
import asyncio
import re
import time
import uuid
from urllib.parse import quote_plus

import httpx

from .knowledge import GITHUB_LANG
from .store import get_setting


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "talent-sourcing-agent"}
    tok = get_setting("GITHUB_TOKEN") or get_setting("GH_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def search_provider() -> str | None:
    for key, name in [("SERPER_API_KEY", "serper"), ("TAVILY_API_KEY", "tavily"), ("BRAVE_API_KEY", "brave"), ("SERPAPI_API_KEY", "serpapi")]:
        if get_setting(key):
            return name
    return None


def manual_links(query: str) -> dict:
    return {
        "google": f"https://www.google.com/search?q={quote_plus(query)}",
        "bing": f"https://www.bing.com/search?q={quote_plus(query)}",
    }


def linkedin_search_link(keywords: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(keywords)}"


async def web_search(query: str, num: int = 10) -> list[dict]:
    p = search_provider()
    if not p:
        return []
    async with httpx.AsyncClient(timeout=45) as c:
        if p == "serper":
            r = await c.post("https://google.serper.dev/search", headers={"X-API-KEY": get_setting("SERPER_API_KEY")}, json={"q": query, "num": num})
            r.raise_for_status()
            return [{"title": i.get("title", ""), "url": i.get("link", ""), "snippet": i.get("snippet", "")} for i in r.json().get("organic", [])]
        if p == "tavily":
            r = await c.post("https://api.tavily.com/search", json={"api_key": get_setting("TAVILY_API_KEY"), "query": query, "max_results": num})
            r.raise_for_status()
            return [{"title": i.get("title", ""), "url": i.get("url", ""), "snippet": i.get("content", "")} for i in r.json().get("results", [])]
        if p == "brave":
            r = await c.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": num},
                            headers={"X-Subscription-Token": get_setting("BRAVE_API_KEY"), "Accept": "application/json"})
            r.raise_for_status()
            return [{"title": i.get("title", ""), "url": i.get("url", ""), "snippet": re.sub("<.*?>", "", i.get("description", ""))}
                    for i in r.json().get("web", {}).get("results", [])]
        if p == "serpapi":
            r = await c.get("https://serpapi.com/search.json", params={"q": query, "api_key": get_setting("SERPAPI_API_KEY"),
                                                                       # SerpAPI's Google engine ignores site: filters
                                                                       **({"engine": "duckduckgo"} if "site:" in query else {"num": num})})
            r.raise_for_status()
            return [{"title": i.get("title", ""), "url": i.get("link", ""), "snippet": i.get("snippet", "")} for i in r.json().get("organic_results", [])]
    return []


def _new_candidate(**kw) -> dict:
    base = {"id": uuid.uuid4().hex[:10], "name": "", "headline": "", "company": "", "location": "", "source": "",
            "url": "", "avatar": "", "email": "", "summary": "", "skills": [], "stage": "Sourced", "notes": "",
            "rating": 0, "github": None, "score": 0, "breakdown": {}, "rationale": "", "strengths": [], "concerns": [],
            "outreach_hook": "", "evidence": ""}
    base.update(kw)
    return base


def parse_linkedin_result(res: dict) -> dict | None:
    url = res["url"].split("?")[0]
    if "linkedin.com/in/" not in url:
        return None
    url = re.sub(r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com", "https://www.linkedin.com", url)
    title = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", res["title"])
    title = re.sub(r"\s*\|\s*LinkedIn.*$", "", title).strip()
    parts = [p.strip() for p in re.split(r"\s[-–—|]\s", title) if p.strip()]
    name = parts[0] if parts else title
    headline = parts[1] if len(parts) > 1 else ""
    company = parts[2] if len(parts) > 2 else ""
    snippet = res.get("snippet", "")
    if not company:
        m = re.search(r"(?:Experience|at)\s*[:\-]?\s*([A-Z][\w&.\- ]{1,40}?)(?:[·|.,]|\s{2}|$)", snippet)
        company = m.group(1).strip() if m else ""
    company = "" if company.lower() == "linkedin" else company
    loc = ""
    m = re.search(r"(?:Location|Based in)\s*[:\-]?\s*([A-Z][\w ,]{2,40}?)(?:[·|.]|$)", snippet)
    if m:
        loc = m.group(1).strip()
    return _new_candidate(name=name, headline=headline, company=company, location=loc, source="LinkedIn",
                          url=url, summary=snippet, evidence=snippet)


JOB_PAGE = re.compile(r"/jobs?[/-]|/careers?/|linkedin\.com/jobs|indeed\.|glassdoor\.|jobstreet|jobsdb|jobleads|expertini|trabajo|mycareersfuture|monster\.|/vacanc", re.I)
JOB_TITLE = re.compile(r"\b(jobs?|hiring|vacanc\w*|careers?|apply|salar\w+|recruit\w*)\b", re.I)
ROLE_WORD = re.compile(r"\b(sales|director|manager|executive|finance|partner|engineer|lead|head|account|enterprise|senior|apac|business|developer|consultant|analyst|officer|vp|chief|president|strategic|regional|global|team|company|group|podcast|episode|webinar|summit|conference|report|news|the|how|why|what)\b", re.I)


def parse_web_result(res: dict) -> dict | None:
    url = res["url"]
    title = res["title"]
    if JOB_PAGE.search(url) or JOB_TITLE.search(title):
        return None
    name = re.split(r"\s[-–—|:,]\s?", title)[0].strip()
    words = name.split()
    if not 2 <= len(words) <= 4 or not all(w[:1].isupper() for w in words) or ROLE_WORD.search(name):
        return None
    return _new_candidate(name=name, headline=title[:120], source="Open Web", url=url, summary=res.get("snippet", ""), evidence=res.get("snippet", ""))


def plan_queries(job: dict) -> list[dict]:
    """Searches the next sourcing run would make, LinkedIn X-ray first; `cached` ones were already run for this role and are skipped."""
    done, opts = job.get("search_log") or {}, job.get("options", {})
    plan = []
    for q in dict.fromkeys(job.get("strategy", {}).get("xray_queries", [])):
        li = "linkedin.com/in" in q
        if not (opts.get("open_web", True) or (li and opts.get("linkedin"))):
            continue
        prev = done.get(q)
        plan.append({"q": q, "kind": "linkedin" if li else "web", "cached": bool(prev), "kept": (prev or {}).get("kept")})
    return sorted(plan, key=lambda p: p["kind"] != "linkedin")


async def source_web(plan: list[dict], limit: int, log, keep=None, seen: set | None = None, done: dict | None = None) -> list[dict]:
    """Run planned searches until `limit` relevant new profiles are found. Skips searches already run and drops off-target results."""
    if not search_provider():
        log("No web-search API key configured — skipping open-web search (manual X-ray links provided in Strategy tab).")
        return []
    done = {} if done is None else done
    seen = set() if seen is None else seen
    cached = [p for p in plan if p["q"] in done]
    if cached:
        log(f"Skipped {len(cached)} searches already run for this role (no credits used)")
    todo = [p["q"] for p in plan if p["q"] not in done]
    if not todo:
        log("No new searches to run — change titles, companies or location in Refine to look somewhere new")
    out = []
    for i, q in enumerate(todo):
        if len(out) >= limit:
            log(f"Found {len(out)} relevant new profiles — stopped early, saved {len(todo) - i} searches")
            break
        is_li = "linkedin.com/in" in q
        try:
            try:
                results = await web_search(q, 10)
            except httpx.TimeoutException:
                results = await web_search(q, 10)
        except Exception as e:  # noqa: BLE001
            log(f"Search failed for query: {type(e).__name__} {e}")
            continue
        kept = dup = off = 0
        for r in results:
            c = parse_linkedin_result(r) if "linkedin.com/in/" in r.get("url", "") else parse_web_result(r)
            if not c:
                off += 1
                continue
            if c["url"] in seen or c["name"].lower() in seen:
                dup += 1
                continue
            if keep and not keep(c):
                off += 1
                continue
            seen.update((c["url"], c["name"].lower()))
            out.append(c)
            kept += 1
        done[q] = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": len(results), "kept": kept}
        log(f"{search_provider()}: {len(results)} results for {'public LinkedIn profile' if is_li else 'open web'} query — "
            f"{kept} relevant new" + (f", {dup} already found" if dup else "") + (f", {off} off-target dropped" if off else ""))
    return out[:limit]


async def github_org_footprint(company: str) -> dict | None:
    """Tech footprint of the hiring firm from its public GitHub org (languages, top repos)."""
    if not company or company.lower() in ("hiring company",):
        return None
    async with httpx.AsyncClient(timeout=20, headers=_gh_headers()) as c:
        r = await c.get("https://api.github.com/search/users", params={"q": f"{company} type:org", "per_page": 3})
        if r.status_code != 200 or not r.json().get("items"):
            return None
        org = r.json()["items"][0]["login"]
        repos = await c.get(f"https://api.github.com/orgs/{org}/repos", params={"sort": "pushed", "per_page": 60})
        if repos.status_code != 200:
            return None
        langs, top = {}, []
        for rp in repos.json():
            if rp.get("fork"):
                continue
            if rp.get("language"):
                langs[rp["language"]] = langs.get(rp["language"], 0) + 1
            top.append({"name": rp["name"], "stars": rp.get("stargazers_count", 0), "language": rp.get("language"), "url": rp["html_url"], "description": rp.get("description") or ""})
        top.sort(key=lambda x: -x["stars"])
        return {"org": org, "url": f"https://github.com/{org}", "languages": sorted(langs.items(), key=lambda x: -x[1])[:8], "top_repos": top[:6]}


async def _gh_user_detail(c: httpx.AsyncClient, login: str) -> dict | None:
    u, repos = await asyncio.gather(c.get(f"https://api.github.com/users/{login}"),
                                    c.get(f"https://api.github.com/users/{login}/repos", params={"sort": "pushed", "per_page": 30}))
    if u.status_code != 200:
        return None
    u = u.json()
    if u.get("type") != "User":
        return None
    rl = repos.json() if repos.status_code == 200 else []
    langs, stars, topics, top = {}, 0, set(), []
    for rp in rl:
        if rp.get("fork"):
            continue
        stars += rp.get("stargazers_count", 0)
        if rp.get("language"):
            langs[rp["language"]] = langs.get(rp["language"], 0) + 1
        topics.update(rp.get("topics") or [])
        top.append({"name": rp["name"], "stars": rp.get("stargazers_count", 0), "language": rp.get("language"), "url": rp["html_url"], "description": rp.get("description") or ""})
    top.sort(key=lambda x: -x["stars"])
    top_langs = [l for l, _ in sorted(langs.items(), key=lambda x: -x[1])[:6]]
    text = " ".join(filter(None, [u.get("bio"), u.get("company"), " ".join(top_langs), " ".join(topics), " ".join(t["description"] for t in top[:8])]))
    return _new_candidate(
        name=u.get("name") or u["login"], headline=(u.get("bio") or "").strip()[:160], company=(u.get("company") or "").lstrip("@").strip(),
        location=u.get("location") or "", source="GitHub", url=u["html_url"], avatar=u.get("avatar_url", ""),
        email=u.get("email") or "", summary=text[:600], evidence=text,
        github={"login": u["login"], "followers": u.get("followers", 0), "public_repos": u.get("public_repos", 0), "stars": stars,
                "top_languages": top_langs, "top_repos": top[:4], "hireable": bool(u.get("hireable")), "blog": u.get("blog") or "",
                "twitter": u.get("twitter_username") or ""},
    )


async def source_github(skills: list[str], location: str, keywords: list[str], limit: int, log) -> list[dict]:
    langs = []
    for s in skills:
        l = GITHUB_LANG.get(s)
        if l and l not in langs:
            langs.append(l)
    loc = "" if not location or location.lower() in ("not specified", "remote", "global") else location.split(",")[0].strip()
    queries = []
    for l in langs[:2]:
        q = " ".join(filter(None, [f"language:{l}" if l else None, f'location:"{loc}"' if loc else None, "followers:>15", "type:user"]))
        if l or loc:
            queries.append(q)
    for kw in keywords[:2]:
        queries.append(" ".join(filter(None, [f'"{kw}"', f'location:"{loc}"' if loc else None, "type:user"])))
    if not queries:
        log("GitHub: not enough technical signals in the JD to search GitHub.")
        return []
    logins, basic = [], {}
    async with httpx.AsyncClient(timeout=20, headers=_gh_headers()) as c:
        for q in queries:
            r = await c.get("https://api.github.com/search/users", params={"q": q, "sort": "followers", "per_page": 15})
            if r.status_code != 200:
                log(f"GitHub search error {r.status_code}: {r.text[:120]}")
                continue
            items = r.json().get("items", [])
            log(f"GitHub: {len(items)} users for `{q}`")
            for i in items:
                if i["login"] not in logins:
                    logins.append(i["login"])
                    basic[i["login"]] = i
        logins = logins[: limit + 5]
        details = await asyncio.gather(*[_gh_user_detail(c, l) for l in logins], return_exceptions=True)
    out = []
    for login, d in zip(logins, details):
        if isinstance(d, dict):
            out.append(d)
        elif d is None and login in basic:
            b = basic[login]
            out.append(_new_candidate(name=login, source="GitHub", url=b["html_url"], avatar=b.get("avatar_url", ""), location=loc,
                                      summary=f"{' '.join(langs[:2])} developer", evidence=" ".join(langs[:2]),
                                      github={"login": login, "followers": 0, "public_repos": 0, "stars": 0, "top_languages": [l.capitalize() for l in langs[:1]],
                                              "top_repos": [], "hireable": False, "blog": "", "twitter": ""}))
    if any(d is None for d in details):
        log("GitHub profile enrichment rate-limited for some users — add a GitHub token in Integrations for full profiles.")
    return out[:limit]
