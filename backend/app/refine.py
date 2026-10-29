"""Recruiter feedback loop: turn free-text feedback + candidate signals into strategy adjustments, then re-source."""
import re
import unicodedata
from collections import Counter

from . import heuristics, llm, sourcing

FIELDS = ["include_companies", "exclude_companies", "add_skills", "remove_skills", "add_titles", "remove_titles", "industries"]
POSITIVE_STAGES = ("Shortlisted", "Contacted", "Interviewing", "Offer", "Hired")

_KW = (r"exclude|excluding|avoid|no one from|nobody from|not from|skip|remove|drop|without|more (?:people |candidates |profiles )?from"
       r"|target|include|add companies?|also companies?|focus on|must have|must-have|need|needs|require|requires|with experience in"
       r"|nice to have|add titles?|titles? like|also (?:look for|search for|search)|look for|only in|based in|location|relocate to|more senior|more junior")
_END = rf"(?=[.;\n]|,?\s+(?:and\s+|but\s+)?(?:{_KW})\b|$)"
_SPLIT = re.compile(r",\s*|\s+(?:and|or|&)\s+(?=[A-Z0-9])|\s*/\s*")
RULES = [
    ("exclude", r"(?:exclude|excluding|avoid|no one from|nobody from|not from|skip|remove|drop)"),
    ("include", r"(?:more (?:people |candidates |profiles )?from|target|include|add companies?|also companies?)"),
    ("focus", r"focus on"),
    ("must", r"(?:must have|must-have|needs?|requires?|with experience in)"),
    ("nice", r"nice to have"),
    ("title", r"(?:add titles?|titles? like|also (?:look for|search for|search)|look for)"),
    ("location", r"(?:only in|based in|location:?|relocate to)"),
]


def empty() -> dict:
    return {f: [] for f in FIELDS} | {"add_nice": [], "location": "", "seniority": ""}


ALIASES = {
    "big 4": ["Deloitte", "PwC", "EY", "KPMG"], "big four": ["Deloitte", "PwC", "EY", "KPMG"],
    "mbb": ["McKinsey", "BCG", "Bain"], "faang": ["Meta", "Apple", "Amazon", "Netflix", "Google"],
}
_CG = ["Unilever", "Procter & Gamble", "Nestlé", "Reckitt", "Colgate-Palmolive", "Mondelez", "Kraft Heinz", "L'Oréal"]
ALIASES |= {k: _CG for k in ("cg", "fmcg", "cpg", "consumer goods")}
_PREFIX = re.compile(r"^(?:the|people|candidates|profiles|from|at|in)\s+", re.I)
_SUFFIX = re.compile(r"\s+(?:experience|backgrounds?|skills?|only|profiles?|candidates?|people)$", re.I)
_FILLER = re.compile(r"^(?:though|but|although|rather|ideally|which|that|as|so|if|while|unless|e\.?g\.?)\b", re.I)


def _items(s: str, protect: set[str] = frozenset()) -> list[str]:
    s = s.strip(" :-\"'")
    for k in sorted(protect, key=len, reverse=True):
        if re.search(r"\s(?:&|and)\s", k) and k.lower() in s.lower():
            s = re.sub(re.escape(k), k.replace(" ", "\u2063"), s, flags=re.I)
    out = []
    for p in _SPLIT.split(s):
        p = p.strip(" .:\"'").replace("\u2063", " ")
        p = _SUFFIX.sub("", _PREFIX.sub("", p)).strip()
        if p and len(p) <= 60 and len(p.split()) <= 5 and not _FILLER.match(p):
            out += ALIASES.get(p.lower(), [p])
    return out


def _canon(name: str, pool: list[str]) -> str:
    for p in pool:
        if p.lower() == name.lower():
            return p
    return name


def _is_company(x: str, job: dict, known: set[str]) -> bool:
    names = {c["name"].lower() for c in job.get("talent_map", {}).get("target_companies", [])} | {k.lower() for k in known}
    if x.lower() in names:
        return True
    if heuristics.find_skills(f" {x} ") or x.lower() in {s.lower() for s in _role_skills(job)}:
        return False
    return x[:1].isupper() and len(x.split()) <= 4


def _role_skills(job: dict) -> list[str]:
    r = job.get("role", {})
    return r.get("must_have_skills", []) + r.get("nice_to_have_skills", [])


def parse_heuristic(text: str, job: dict, known: set[str]) -> dict:
    adj = empty()
    t = " " + (text or "").strip() + " "
    titles = job.get("talent_map", {}).get("peer_titles", [])
    skills = _role_skills(job)
    protect = set(known) | {c["name"] for c in job.get("talent_map", {}).get("target_companies", [])}
    for kind, pat in RULES:
        for m in re.finditer(rf"\b{pat}\s+(.+?){_END}", t, re.I):
            if kind == "location":
                adj["location"] = adj["location"] or heuristics.clean_location(m.group(1))
                continue
            for x in _items(m.group(1), protect):
                if kind == "exclude":
                    if x.lower() in {s.lower() for s in skills}:
                        adj["remove_skills"].append(_canon(x, skills))
                    elif any(x.lower() == ti.lower() for ti in titles):
                        adj["remove_titles"].append(_canon(x, titles))
                    else:
                        adj["exclude_companies"].append(x)
                elif kind == "include":
                    adj["include_companies"].append(x)
                elif kind == "focus":
                    (adj["include_companies"] if _is_company(x, job, known) and not heuristics.find_skills(f" {x} ") else adj["add_skills"]).append(x)
                elif kind == "must":
                    adj["add_skills"].append(x)
                elif kind == "nice":
                    adj["add_nice"].append(x)
                elif kind == "title":
                    adj["add_titles"].append(x)
    for m in re.finditer(r"\b(?:at|as)\s+(?:an?\s+)?((?:[A-Z][\w&/]*\s?){1,4}?)\s+level\b", t):
        adj["add_titles"].append(m.group(1).strip())
    for m in re.finditer(r"\b((?:[A-Z][\w&/]*\s?){1,3}?)\s*(?:experience|background)\s+(?:would be|is)\s+(?:an?\s+)?(?:\w+\s+)?(?:advantage|plus|bonus)", t):
        adj["add_nice"].append(m.group(1).strip())
    for m in re.finditer(r"\b(?:from|with)\s+(?:an?\s+|the\s+)?([a-zA-Z&,/\- ]{3,80}?)\s+(?:backgrounds?|industr(?:y|ies)|sectors?)\b", t, re.I):
        for x in re.split(r",\s*|\s+(?:and|or|&)\s+|\s*/\s*", m.group(1)):
            x = x.strip()
            if x and len(x.split()) <= 3 and not _FILLER.match(x):
                adj["industries"].append(x)
    if re.search(r"\bmore senior\b|\btoo junior\b", t, re.I):
        adj["seniority"] = "more senior"
    elif re.search(r"\bmore junior\b|\btoo senior\b", t, re.I):
        adj["seniority"] = "more junior"
    return _dedupe(adj)


def _dedupe(adj: dict) -> dict:
    for k in FIELDS + ["add_nice"]:
        seen, out = set(), []
        for x in adj.get(k) or []:
            x = str(x).strip()
            if x and x.lower() not in seen:
                seen.add(x.lower())
                out.append(x)
        adj[k] = out
    adj["location"] = str(adj.get("location") or "").strip()
    adj["seniority"] = str(adj.get("seniority") or "").strip()
    return adj


async def parse(text: str, job: dict, known: set[str], system: str) -> tuple[dict, str]:
    if not text.strip():
        return empty(), "none"
    if llm.provider():
        try:
            prompt = (
                f"A recruiter gave feedback on a sourcing search for '{job['role'].get('title')}' at {job['role'].get('company')}.\n"
                f"Current must-have skills: {job['role'].get('must_have_skills')}\nCurrent titles searched: {job['talent_map'].get('peer_titles')}\n"
                f"Current target companies: {[c['name'] for c in job['talent_map'].get('target_companies', [])]}\n"
                f"Location: {job['role'].get('location')}\n\nFeedback: \"\"\"{text}\"\"\"\n\n"
                "Translate it into adjustments. Return JSON with keys: include_companies, exclude_companies, add_skills, remove_skills, "
                "add_titles, remove_titles, add_nice, industries (arrays of strings; industries = sectors candidates should come from), location (string, empty if unchanged), seniority "
                "('more senior', 'more junior' or '')."
            )
            return _dedupe({**empty(), **(await llm.complete_json(system, prompt, 1500))}), "ai"
        except Exception:  # noqa: BLE001
            pass
    return parse_heuristic(text, job, known), "rules"


def is_positive(c: dict) -> bool:
    return (c.get("stage_manual") and c.get("stage") in POSITIVE_STAGES) or c.get("rating", 0) >= 4


def is_negative(c: dict) -> bool:
    return not c.get("excluded") and (c.get("stage") == "Rejected" or c.get("rating", 0) in (1, 2))


def _short_title(headline: str) -> str:
    h = re.split(r"\s*[|@·•,]\s*|\s+at\s+|\s[-–—]\s", headline or "")[0].strip()
    return h if 1 <= len(h.split()) <= 5 and not re.search(r"\b(i|my|hey|passionate)\b", h, re.I) else ""


NOT_COMPANY = re.compile(r"\b(fp&a|finance|financial|manager|partner|analyst|director|controller|operations|transformation|strategy|strategic"
                         r"|sales|engineer|consultant|lead|head|mba|cpa|acca|cfa|freelance|self-employed|n/a)\b", re.I)


def _looks_like_company(name: str) -> bool:
    n = (name or "").strip()
    return (len(n) >= 3 and not NOT_COMPANY.search(n) and not heuristics.find_skills(f" {n} ")
            and not re.fullmatch(r"(?:[A-Z]\.)+[A-Z]?\.?", n))


def signals(job: dict) -> dict:
    """What the recruiter's shortlist/reject actions imply."""
    pos = [c for c in job["candidates"] if is_positive(c)]
    neg = [c for c in job["candidates"] if is_negative(c)]
    pc = Counter(c["company"] for c in pos if _looks_like_company(c.get("company", "")))
    nc = Counter(c["company"] for c in neg if _looks_like_company(c.get("company", "")))
    pt = Counter(t for t in (_short_title(c.get("headline", "")) for c in pos) if t)
    src_pos, src_neg = Counter(c["source"] for c in pos), Counter(c["source"] for c in neg)
    return {
        "liked": len(pos), "rejected": len(neg),
        "liked_companies": [k for k, _ in pc.most_common(4)],
        "liked_titles": [k for k, _ in pt.most_common(3)],
        "avoid_companies": [k for k, n in nc.most_common(4) if n >= 2 and k not in pc],
        "weak_sources": [s for s, n in src_neg.items() if n >= 3 and src_pos.get(s, 0) == 0],
    }


def apply(job: dict, adj: dict, sig: dict | None) -> list[str]:
    """Mutate role / talent map / refinement state; return a human-readable change list."""
    role, tmap = job["role"], job["talent_map"]
    st = job.setdefault("refinement", {"exclude_companies": [], "avoid_companies": [], "boost_companies": [], "rounds": []})
    changes = []
    low = lambda xs: {x.lower() for x in xs}

    if adj["add_skills"] or adj["remove_skills"]:
        must = [s for s in role.get("must_have_skills", []) if s.lower() not in low(adj["remove_skills"])]
        must = list(dict.fromkeys(adj["add_skills"] + must))
        role["must_have_skills"] = must
        role["nice_to_have_skills"] = [s for s in role.get("nice_to_have_skills", []) if s.lower() not in low(must + adj["remove_skills"])]
        if adj["add_skills"]:
            changes.append(f"Must-have skills added: {', '.join(adj['add_skills'])}")
        if adj["remove_skills"]:
            changes.append(f"Skills removed: {', '.join(adj['remove_skills'])}")
    if adj["add_nice"]:
        role["nice_to_have_skills"] = list(dict.fromkeys(role.get("nice_to_have_skills", []) + adj["add_nice"]))
        changes.append(f"Nice-to-have skills added: {', '.join(adj['add_nice'])}")

    role_title = role.get("title", "")
    if adj.get("industries"):
        role["target_industries"] = list(dict.fromkeys(role.get("target_industries", []) + adj["industries"]))
        changes.append(f"Target industries: {', '.join(adj['industries'])}")
    titles = [t for t in tmap.get("peer_titles", []) if t.lower() not in low(adj["remove_titles"])]
    new_titles = list(adj["add_titles"])
    if sig and sig.get("liked_titles"):
        new_titles += [t for t in sig["liked_titles"] if t.lower() not in low(titles + new_titles)]
    base = heuristics.search_title(role_title)
    if adj["seniority"] == "more senior":
        new_titles += [f"Senior {base}", f"Head of {base}" if " " not in base else f"Lead {base}"]
        changes.append("Shifted search towards more senior profiles")
    elif adj["seniority"] == "more junior":
        down = heuristics.step_down(role_title)
        if down:
            new_titles += [t for t in down if t.lower() not in low(adj["remove_titles"])]
            titles = [t for t in titles if not re.match(r"(chief|svp|evp|group)\b", t, re.I)]
        else:
            titles = [t for t in titles if not re.match(r"(senior|lead|head|principal|director|vp)\b", t, re.I)] or [base]
        changes.append("Shifted search towards less senior profiles")
    merged = list(dict.fromkeys(new_titles + titles))
    # never search titles from another job function (e.g. "Managing Director" for a CFO search) — they burn credits on off-target profiles
    off = [t for t in merged if t not in adj["add_titles"] and not heuristics.on_function(t, role_title)]
    merged = [t for t in merged if t not in off] or [t for t in heuristics.peer_titles(role_title, role.get("seniority", ""))
                                                     if t.lower() not in low(adj["remove_titles"])][:4] or [base]
    tmap["peer_titles"] = merged[:8]
    if new_titles:
        changes.append(f"Titles added to search: {', '.join(dict.fromkeys(new_titles))}")
    if adj["remove_titles"]:
        changes.append(f"Titles removed: {', '.join(adj['remove_titles'])}")
    if off:
        changes.append(f"Dropped titles outside the role's function: {', '.join(off)}")

    targets = tmap.get("target_companies", [])
    excl = low(adj["exclude_companies"])
    if excl:
        targets = [c for c in targets if c["name"].lower() not in excl]
        st["exclude_companies"] = list(dict.fromkeys(st["exclude_companies"] + adj["exclude_companies"]))
        st["boost_companies"] = [c for c in st["boost_companies"] if c.lower() not in excl]
        changes.append(f"Excluded companies: {', '.join(adj['exclude_companies'])}")
    adds = [(c, "Requested by recruiter feedback") for c in adj["include_companies"]]
    if sig:
        adds += [(c, "Calibrated from candidates you liked") for c in sig.get("liked_companies", []) if c.lower() not in excl]
        avoid = [c for c in sig.get("avoid_companies", []) if c.lower() not in low(st["avoid_companies"])]
        if avoid:
            st["avoid_companies"] += avoid
            changes.append(f"Down-weighted companies of rejected candidates: {', '.join(avoid)}")
    fresh = []
    for name, why in adds:
        targets = [c for c in targets if c["name"].lower() != name.lower()]
        fresh.append({"name": name, "tier": "Primary", "rationale": why, "est_talent_pool": ""})
        if name.lower() not in low(st["boost_companies"]):
            st["boost_companies"].append(name)
    if fresh:
        tmap["target_companies"] = fresh + targets
        changes.append(f"Prioritised companies: {', '.join(c['name'] for c in fresh)}")
    else:
        tmap["target_companies"] = targets

    loc = heuristics.clean_location(adj["location"]) if adj["location"] else ""
    if loc and loc.lower() != (role.get("location") or "").lower():
        role["location"] = loc
        changes.append(f"Location set to {loc}")
    if sig and sig.get("weak_sources"):
        changes.append(f"Note: you rejected all {', '.join(sig['weak_sources'])} candidates so far — consider turning that channel off")
    return changes


def relevant(c: dict, job: dict) -> bool:
    """Worth adding to the pool: same job function as the role and not from an excluded company."""
    if is_excluded(c, job):
        return False
    title = job["role"].get("title", "")
    if c.get("source") == "GitHub" and heuristics.role_family(title) in ("", "engineering", "data"):
        return True
    return heuristics.on_function(c.get("headline") or c.get("summary", "")[:160], title)


def warnings(job: dict, plan: list[dict]) -> list[str]:
    w = []
    if plan and all(p["cached"] for p in plan):
        w.append("Every planned search has already been run for this role, so it would find no one new. Change titles, companies or location.")
    loc = job["role"].get("location", "")
    if len(loc.split()) > 3:
        w.append(f"Location “{loc}” is too long for a search. Use a city or country.")
    if not sourcing.search_provider():
        w.append("No web-search key is set, so only GitHub and manual search links are available.")
    return w


def is_excluded(c: dict, job: dict) -> bool:
    excl = job.get("refinement", {}).get("exclude_companies", [])
    text = _fold(f" {c.get('company', '')} {c.get('headline', '')} ")
    return any(re.search(rf"(?<![a-z0-9]){re.escape(_fold(e))}(?![a-z0-9])", text) for e in excl)


def _fold(s: str) -> str:
    """Lower-case and strip accents so "L'Oréal" matches "L'Oreal"."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(ch)).lower()


def refine_strategy(job: dict, adj: dict) -> None:
    new = heuristics.build_strategy(job["role"], job["talent_map"])
    strat = job.get("strategy") or {}
    for k in ("skills_matrix", "boolean_strings", "xray_queries"):
        strat[k] = new[k]
    loc = job["role"].get("location", "")
    loc = "" if loc.lower() in ("not specified", "remote", "global") else loc
    title0 = heuristics.search_title((job["talent_map"].get("peer_titles") or [job["role"]["title"]])[0])
    extra = [f'site:linkedin.com/in "{title0}" "{s}" {loc}'.strip() for s in adj["add_skills"][:2]]
    strat["xray_queries"] = list(dict.fromkeys(strat["xray_queries"][:5] + extra[:1]))
    strat["manual_search_links"] = [{"query": q, **sourcing.manual_links(q)} for q in strat["xray_queries"]]
    job["strategy"] = strat
