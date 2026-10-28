"""The sourcing agent pipeline: JD -> recruiter brief -> talent map -> strategy -> candidates -> shortlist."""
import json
import re
import traceback
from datetime import datetime, timezone

from . import heuristics, llm, sourcing
from .store import load_job, save_job

STEPS = [
    ("ingest", "Reading job description"),
    ("analyze", "Executive recruiter intake & role analysis"),
    ("talent_map", "Talent mapping of hiring firm & market"),
    ("strategy", "Skills matrix & sourcing strategy"),
    ("sourcing", "Searching GitHub, LinkedIn & open web"),
    ("scoring", "Scoring & shortlisting candidates"),
]

RECRUITER_SYSTEM = (
    "You are a world-class executive search partner (ex-Heidrick & Struggles / Spencer Stuart) and talent-intelligence "
    "lead. You think like a retained-search recruiter: precise, commercial, evidence-based, and candid. You know which "
    "companies are talent feeders for which roles, how teams are typically structured, and what signals predict success. "
    "Always answer with valid JSON matching the requested schema exactly. Be specific: name real companies, real titles, "
    "real skills. Never invent candidate names."
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job(job_id: str, source: dict, options: dict) -> dict:
    return {
        "id": job_id, "created_at": now(), "updated_at": now(), "status": "running", "source": source, "options": options,
        "steps": [{"key": k, "label": l, "status": "pending"} for k, l in STEPS], "log": [], "mode": "",
        "jd_text": "", "role": {}, "recruiter_brief": {}, "talent_map": {}, "strategy": {}, "candidates": [], "error": "",
    }


class Run:
    def __init__(self, job: dict):
        self.job = job

    def save(self):
        self.job["updated_at"] = now()
        save_job(self.job)

    def log(self, msg: str):
        self.job["log"].append({"t": now(), "msg": msg})
        self.save()

    def step(self, key: str, status: str):
        for s in self.job["steps"]:
            if s["key"] == key:
                s["status"] = status
        self.save()


async def run_pipeline(job_id: str, raw: dict):
    job = load_job(job_id)
    r = Run(job)
    cur = "ingest"
    try:
        r.step("ingest", "running")
        text = raw.get("text", "")
        hints = {k: raw.get(k, "") for k in ("company", "location", "title", "page_title", "site_name", "host")}
        if len(text) < 80:
            raise ValueError("Couldn't extract enough text from the job description. Try uploading the file or pasting the text.")
        job["jd_text"] = text
        r.log(f"Extracted {len(text):,} characters from {job['source'].get('type')}")
        r.step("ingest", "done")

        use_llm = llm.provider() is not None
        job["mode"] = f"AI ({llm.provider()})" if use_llm else "Heuristic (no LLM key)"
        r.log(f"Agent mode: {job['mode']}")

        cur = "analyze"
        r.step("analyze", "running")
        base = heuristics.analyze(text, hints)
        if use_llm:
            try:
                a = await llm.complete_json(RECRUITER_SYSTEM, _analyze_prompt(text, hints))
                job["role"] = {**base["role"], **(a.get("role") or {})}
                job["recruiter_brief"] = {**base["recruiter_brief"], **(a.get("recruiter_brief") or {})}
            except Exception as e:  # noqa: BLE001
                r.log(f"LLM analysis failed, using heuristic analysis for this run: {e}")
                job["role"], job["recruiter_brief"] = base["role"], base["recruiter_brief"]
                use_llm = False
                job["mode"] = "Heuristic (LLM error)"
        else:
            job["role"], job["recruiter_brief"] = base["role"], base["recruiter_brief"]
        r.log(f"Role identified: {job['role'].get('title')} @ {job['role'].get('company')} ({job['role'].get('seniority')})")
        r.step("analyze", "done")

        cur = "talent_map"
        r.step("talent_map", "running")
        company = job["role"].get("company", "")
        footprint = None
        try:
            footprint = await sourcing.github_org_footprint(company)
            if footprint:
                r.log(f"Found hiring firm GitHub org: {footprint['org']} ({', '.join(l for l, _ in footprint['languages'][:4])})")
        except Exception as e:  # noqa: BLE001
            r.log(f"GitHub org lookup skipped: {e}")
        team_benchmark = []
        if sourcing.search_provider() and company:
            try:
                titles = (base["talent_map"].get("peer_titles") or [job["role"]["title"]])[:3]
                q = f'site:linkedin.com/in "{company}" ' + "(" + " OR ".join(f'"{t}"' for t in titles) + ")"
                res = await sourcing.web_search(q, 10)
                team_benchmark = [c for c in (sourcing.parse_linkedin_result(x) for x in res) if c]
                r.log(f"Benchmarked {len(team_benchmark)} current {company} profiles in similar roles")
            except Exception as e:  # noqa: BLE001
                r.log(f"Team benchmark search failed: {e}")
        tmap = base["talent_map"]
        if use_llm:
            try:
                t = await llm.complete_json(RECRUITER_SYSTEM, _talent_map_prompt(job, footprint, team_benchmark), 5000)
                tmap = {**tmap, **t}
            except Exception as e:  # noqa: BLE001
                r.log(f"LLM talent mapping failed, using heuristic map: {e}")
        tmap["github_footprint"] = footprint
        tmap["team_benchmark"] = [{"name": c["name"], "headline": c["headline"], "url": c["url"]} for c in team_benchmark]
        job["talent_map"] = tmap
        r.log(f"Mapped {len(tmap.get('target_companies', []))} target companies, {len(tmap.get('peer_titles', []))} peer titles")
        r.step("talent_map", "done")

        cur = "strategy"
        r.step("strategy", "running")
        strat = heuristics.build_strategy(job["role"], tmap)
        if use_llm:
            try:
                s = await llm.complete_json(RECRUITER_SYSTEM, _strategy_prompt(job), 4000)
                strat = {**strat, **{k: v for k, v in s.items() if v}}
            except Exception as e:  # noqa: BLE001
                r.log(f"LLM strategy failed, using heuristic strategy: {e}")
        strat["manual_search_links"] = [{"query": q, **sourcing.manual_links(q)} for q in strat.get("xray_queries", [])]
        li_kw = " ".join([(tmap.get("peer_titles") or [job["role"]["title"]])[0]] + job["role"].get("must_have_skills", [])[:2])
        strat["linkedin_search_link"] = sourcing.linkedin_search_link(li_kw)
        job["strategy"] = strat
        r.step("strategy", "done")

        cur = "sourcing"
        r.step("sourcing", "running")
        await source_candidates(r)
        r.step("sourcing", "done")

        cur = "scoring"
        r.step("scoring", "running")
        await score_candidates(r, use_llm)
        r.step("scoring", "done")
        job["status"] = "complete"
        r.log(f"Done — {len(job['candidates'])} candidates, {sum(1 for c in job['candidates'] if c['stage'] == 'Shortlisted')} shortlisted")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        r.step(cur, "error")
        job["status"] = "error"
        job["error"] = str(e)
        r.log(f"Error: {e}")
    r.save()


async def source_candidates(r: Run):
    job = r.job
    opts = job["options"]
    limit = int(opts.get("max_candidates", 25))
    role, strat = job["role"], job["strategy"]
    cands = []
    if opts.get("github", True):
        try:
            kws = [k for k in (strat.get("github_keywords") or role.get("must_have_skills", [])) if k][:2]
            gh = await sourcing.source_github(role.get("must_have_skills", []) + role.get("nice_to_have_skills", []),
                                              role.get("location", ""), kws, min(limit, 20), r.log)
            cands += gh
        except Exception as e:  # noqa: BLE001
            r.log(f"GitHub sourcing failed: {e}")
    if opts.get("linkedin", True) or opts.get("open_web", True):
        cands += await sourcing.source_web(strat.get("xray_queries", []), opts.get("linkedin", True), opts.get("open_web", True), limit, r.log)
    existing = {c["url"] for c in job["candidates"]}
    job["candidates"] += [c for c in cands if c["url"] not in existing]
    r.log(f"Sourced {len(cands)} raw profiles")
    r.save()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", " ", (s or "").lower())


def heuristic_score(c: dict, job: dict) -> dict:
    role, tmap = job["role"], job["talent_map"]
    text = _norm(" ".join([c.get("name", ""), c.get("headline", ""), c.get("company", ""), c.get("summary", ""), c.get("evidence", ""),
                            " ".join((c.get("github") or {}).get("top_languages", []))]))
    must, nice = role.get("must_have_skills", []), role.get("nice_to_have_skills", [])
    hit = lambda s: re.search(rf"(?<![a-z0-9]){re.escape(_norm(s).strip())}(?![a-z0-9])", text) is not None
    m_hit = [s for s in must if hit(s)]
    n_hit = [s for s in nice if hit(s)]
    skills = min(40, (len(m_hit) / max(1, len(must))) * 34 + min(6, len(n_hit) * 2))
    titles = tmap.get("peer_titles") or [role.get("title", "")]
    tw = {w for t in titles for w in _norm(t).split() if len(w) > 2 and w not in ("and", "the", "for", "head", "senior")}
    hl = set(_norm(c.get("headline", "")).split())
    title = min(20, len(tw & hl) * 6)
    comp_score, comp_match = 0, ""
    cc = _norm(c.get("company", "") + " " + c.get("headline", "") + " " + c.get("summary", ""))
    for t in tmap.get("target_companies", []):
        n = _norm(t.get("name", "")).strip()
        if n and re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", cc):
            val = {"Primary": 20, "Secondary": 14}.get(t.get("tier"), 8)
            if val > comp_score:
                comp_score, comp_match = val, t["name"]
    loc = (role.get("location") or "").split(",")[0].strip().lower()
    loc_score = 10 if loc and loc not in ("not specified", "remote") and loc in (c.get("location", "") + " " + c.get("summary", "")).lower() else (5 if not loc or loc in ("not specified", "remote") else 0)
    gh = c.get("github") or {}
    signals = min(10, (gh.get("followers", 0) ** 0.5) / 4 + (gh.get("stars", 0) ** 0.5) / 6 + (2 if gh.get("hireable") else 0)) if gh else (6 if c["source"] == "LinkedIn" else 3)
    total = round(skills + title + comp_score + loc_score + signals)
    strengths = []
    if m_hit:
        strengths.append(f"Matches must-haves: {', '.join(m_hit[:5])}")
    if comp_match:
        strengths.append(f"From target company {comp_match}")
    if gh.get("stars", 0) > 100:
        strengths.append(f"Strong open-source signal ({gh['stars']} stars)")
    concerns = []
    missing = [s for s in must if s not in m_hit][:4]
    if missing:
        concerns.append(f"No visible evidence of: {', '.join(missing)}")
    if loc_score == 0 and loc:
        concerns.append("Location may not match")
    return {"score": min(100, total), "breakdown": {"Skills": round(skills), "Title/Seniority": round(title), "Company": comp_score,
            "Location": loc_score, "Signals": round(signals)}, "skills": m_hit + n_hit, "strengths": strengths, "concerns": concerns}


async def score_candidates(r: Run, use_llm: bool):
    job = r.job
    for c in job["candidates"]:
        if c.get("manual_score"):
            continue
        h = heuristic_score(c, job)
        c.update({k: h[k] for k in ("score", "breakdown", "skills")})
        c["strengths"], c["concerns"] = h["strengths"], h["concerns"]
    job["candidates"].sort(key=lambda c: -c["score"])
    if use_llm and job["candidates"]:
        top = job["candidates"][:25]
        try:
            res = await llm.complete_json(RECRUITER_SYSTEM, _rank_prompt(job, top), 6000)
            by_id = {x.get("id"): x for x in res.get("candidates", [])}
            for c in top:
                x = by_id.get(c["id"])
                if not x:
                    continue
                c["score"] = int(round(0.6 * int(x.get("score", c["score"])) + 0.4 * c["score"]))
                c["rationale"] = x.get("rationale", "")
                c["strengths"] = x.get("strengths") or c["strengths"]
                c["concerns"] = x.get("concerns") or c["concerns"]
                c["outreach_hook"] = x.get("outreach_hook", "")
            r.log("AI re-ranked top candidates with recruiter rationale")
        except Exception as e:  # noqa: BLE001
            r.log(f"LLM re-ranking failed, keeping heuristic scores: {e}")
        job["candidates"].sort(key=lambda c: -c["score"])
    threshold = int(job["options"].get("shortlist_threshold", 55 if use_llm else 20))
    n_short = int(job["options"].get("shortlist_size", 10))
    for i, c in enumerate(job["candidates"]):
        if c["stage"] in ("Sourced", "Shortlisted"):
            c["stage"] = "Shortlisted" if (i < n_short and c["score"] >= threshold) else "Sourced"
        if not c.get("rationale"):
            c["rationale"] = "; ".join(c["strengths"]) or "Partial match — review manually."
    r.save()


def _analyze_prompt(text: str, hints: dict) -> str:
    return f"""Analyse this job description as an executive recruiter running a retained search intake.
Hints (may be empty): company={hints.get('company')!r}, location={hints.get('location')!r}, page_title={hints.get('page_title')!r}

JOB DESCRIPTION:
\"\"\"{text[:12000]}\"\"\"

Return JSON:
{{
 "role": {{"title": str, "company": str, "location": str, "seniority": one of ["C-Level","VP / Head","Director","Manager / Lead","Senior IC","Mid-level IC"],
   "function": str, "industry": str, "years_experience": str, "summary": str (2 sentences),
   "must_have_skills": [str] (6-10 concise skill keywords), "nice_to_have_skills": [str] (4-8),
   "responsibilities": [str] (4-6), "requirements": [str] (4-6), "education": str, "compensation_hint": str (market estimate with currency)}},
 "recruiter_brief": {{"executive_summary": str (3-4 sentences, recruiter's POV on the mandate and difficulty),
   "ideal_candidate_persona": str, "selling_points": [str] (4-5), "intake_questions": [str] (5-6 sharp questions for the hiring manager),
   "red_flags": [str] (3-5), "evaluation_criteria": [{{"criterion": str, "weight": int}}] (weights sum to 100)}}
}}"""


def _talent_map_prompt(job: dict, footprint, bench) -> str:
    role = job["role"]
    return f"""Build a talent map for this search. Start from the HIRING FIRM ({role.get('company')}): what kind of people it hires
for this role today, where they come from, then map the external market.

ROLE: {json.dumps({k: role.get(k) for k in ('title','company','location','seniority','industry','function','must_have_skills','nice_to_have_skills','years_experience')})}
HIRING FIRM PUBLIC GITHUB FOOTPRINT: {json.dumps(footprint) if footprint else 'unknown'}
CURRENT PROFILES AT HIRING FIRM IN SIMILAR ROLES (from web search): {json.dumps([{'name': b['name'], 'headline': b['headline'], 'snippet': b['summary'][:200]} for b in bench][:10]) if bench else 'not available'}

Return JSON:
{{
 "hiring_company_profile": {{"name": str, "description": str, "culture_signals": [str], "current_team_patterns": [str] (4-6 observations about background, prior employers, education, tenure of people in similar roles at this firm)}},
 "target_companies": [{{"name": str, "tier": "Primary"|"Secondary"|"Adjacent", "rationale": str, "est_talent_pool": str}}] (12-16 real companies, local to the location where relevant),
 "peer_titles": [str] (5-8 equivalent titles used across target companies),
 "talent_hubs": [{{"location": str, "rationale": str}}] (2-4),
 "market_trends": [{{"trend": str, "implication": str}}] (4-6, current hiring-market trends for this role),
 "common_attributes": [{{"attribute": str, "prevalence": int 0-100}}] (6-8 attributes shared by successful people in this role),
 "career_paths": [str] (3-4 typical paths into this role, as "A → B → C"),
 "talent_pool_estimate": str, "competition_level": "Low"|"Medium"|"High", "diversity_notes": str
}}"""


def _strategy_prompt(job: dict) -> str:
    role, tmap = job["role"], job["talent_map"]
    return f"""Design the sourcing strategy for this search.
ROLE: {json.dumps({k: role.get(k) for k in ('title','company','location','seniority','must_have_skills','nice_to_have_skills')})}
TARGET COMPANIES: {[c.get('name') for c in tmap.get('target_companies', [])]}
PEER TITLES: {tmap.get('peer_titles')}

Return JSON:
{{
 "skills_matrix": [{{"skill": str, "category": str, "importance": "Must-have"|"Nice-to-have", "signal": str (where/how to verify it)}}] (8-12),
 "channels": [{{"channel": str, "priority": "High"|"Medium"|"Low", "tactic": str}}] (4-6),
 "boolean_strings": {{"linkedin": str (LinkedIn Recruiter boolean), "google_xray": str, "github": str (GitHub user search syntax)}},
 "xray_queries": [str] (3-4 web search queries; at least 2 must start with "site:linkedin.com/in", one may target open web e.g. personal sites, conference speakers, publications),
 "github_keywords": [str] (2 short keyword phrases likely in GitHub bios of target candidates, empty if non-technical role),
 "outreach_template": str (personalised InMail with placeholders {{first_name}}, {{hook}}),
 "timeline": [{{"week": str, "focus": str}}]
}}"""


def _rank_prompt(job: dict, cands: list[dict]) -> str:
    role = job["role"]
    slim = [{"id": c["id"], "name": c["name"], "headline": c["headline"], "company": c["company"], "location": c["location"], "source": c["source"],
             "evidence": (c.get("evidence") or c.get("summary") or "")[:400], "github": {k: (c.get("github") or {}).get(k) for k in ("followers", "stars", "top_languages")} if c.get("github") else None,
             "heuristic_score": c["score"]} for c in cands]
    return f"""Assess these sourced candidates for the search below as an executive recruiter. Be candid; penalise weak evidence.
ROLE: {json.dumps({k: role.get(k) for k in ('title','company','location','seniority','must_have_skills','years_experience')})}
EVALUATION CRITERIA: {json.dumps(job['recruiter_brief'].get('evaluation_criteria'))}
CANDIDATES: {json.dumps(slim)}

Return JSON: {{"candidates": [{{"id": str, "score": int 0-100, "rationale": str (1-2 sentences), "strengths": [str], "concerns": [str], "outreach_hook": str (personalised opener)}}]}}"""
