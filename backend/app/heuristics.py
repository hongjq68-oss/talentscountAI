"""Rule-based JD analysis used when no LLM key is configured (and as a safety net)."""
import re
from collections import Counter

from .knowledge import ALL_SKILLS, COMPANY_COMPETITORS, INDUSTRY_COMPANIES, MARKET_SEGMENTS, INDUSTRY_KEYWORDS, LOCATIONS, SENIORITY

ROLE_WORDS = r"(engineer|developer|scientist|manager|director|head|lead|architect|analyst|designer|officer|" \
             r"president|vp|chief|consultant|specialist|recruiter|partner|executive|administrator|strategist)"


def _skill_regex(skill: str) -> re.Pattern:
    esc = re.escape(skill)
    return re.compile(rf"(?<![A-Za-z0-9]){esc}(?![A-Za-z0-9])", re.I if len(skill) > 2 else 0)


SKILL_PATTERNS = [(s, cat, _skill_regex(s)) for s, cat in ALL_SKILLS]


BOILERPLATE = re.compile(
    r"salary|compensation|pay range|base pay|on target earnings|\bOTE\b|commission|bonus|equity|benefits|"
    r"parental leave|vacation|equal opportunity|equal employment|visa sponsorship|reasonable accommodation|"
    r"privacy (?:notice|policy)|background check|e-verify", re.I)


def strip_boilerplate(text: str) -> str:
    """Drop pay/benefits/EEO lines so they don't leak into skills."""
    return "\n".join(l for l in text.splitlines() if not BOILERPLATE.search(l))


SKILL_ALIASES = [
    ("Enterprise Sales", "Business & Leadership", r"enterprise (?:customers|clients|accounts|deals|software deals)|selling [^.\n]{0,40}enterprise"),
    ("Technical Sales", "Business & Leadership", r"technical (?:sales|solutions|products)|selling (?:highly |deeply )?technical|sales engineer|solutions engineer|forward deployed"),
    ("Full-cycle Sales", "Business & Leadership", r"(?:entire|full|end-to-end) sales cycle|prospecting (?:through|to) close"),
    ("Pipeline Generation", "Business & Leadership", r"generat\w* pipeline|pipeline generation|outbound prospecting"),
    ("C-suite Engagement", "Business & Leadership", r"c-suite|c-level (?:executives|stakeholders)"),
    ("Complex Deal Closing", "Business & Leadership", r"clos\w* (?:large|complex|multi-?million)[^.\n]{0,30}deals|layered buying"),
]
ALIAS_PATTERNS = [(s, cat, re.compile(rx, re.I)) for s, cat, rx in SKILL_ALIASES]


def find_skills(text: str) -> list[tuple[str, str, int]]:
    out, seen = [], set()
    for s, cat, rx in SKILL_PATTERNS + ALIAS_PATTERNS:
        n = len(rx.findall(text))
        if n and s not in seen:
            seen.add(s)
            out.append((s, cat, n))
        elif n:
            out = [(a, c, k + n) if a == s else (a, c, k) for a, c, k in out]
    return out


GTM_SELLERS = ["GitHub", "GitLab", "Datadog", "Snowflake", "MongoDB", "Databricks", "HashiCorp", "Atlassian", "Palantir", "Scale AI"]
SALES_IC = re.compile(r"\b(account (?:director|executive|manager)|sales executive|client partner)\b", re.I)
GTM_ROLE = re.compile(r"\b(sales|account (?:director|executive|manager)|business development|go-to-market|gtm|partnerships|revenue)\b", re.I)
REGION_SUFFIX = re.compile(r"\s*[-–—,(|]\s*(?:apac|emea|amer|americas|anz|sea|asia(?: pacific)?|europe|latam|north america|japan|india|global|remote)\b.*$", re.I)


TECH_ROLE = re.compile(r"\b(engineer\w*|developer|software|data|machine learning|ml|ai|devops|sre|architect\w*|scientist|security"
                       r"|technical|solutions?|cloud|platform|infrastructure|programm\w*|full[- ]?stack|front[- ]?end|back[- ]?end"
                       r"|mobile|python|java\w*|golang|kubernetes|cto)\b", re.I)


def is_technical_role(role: dict) -> bool:
    """GitHub is only a useful channel for engineering, technical and go-to-market roles."""
    title = role.get("title", "")
    skills = " ".join(role.get("must_have_skills", []))
    return bool(TECH_ROLE.search(f"{title} {skills}") or GTM_ROLE.search(title))


def seniority_of(title: str) -> str:
    t = f" {title.lower()} "
    if SALES_IC.search(t) and not re.search(r"\b(head|vp|vice president|chief)\b", t):
        return "Senior IC"
    for level, keys in SENIORITY:
        if any(re.search(rf"(?<![a-z]){re.escape(k.strip())}(?![a-z])", t) for k in keys):
            return level
    return "Mid-level IC"


def guess_title(text: str, page_title: str = "") -> str:
    candidates = []
    if page_title:
        candidates.extend(re.split(r"\s[|\-–—]\s|:", page_title))
    candidates.extend(l.strip() for l in text.splitlines()[:40])
    for c in candidates:
        c = c.strip(" -|•*")
        if 3 < len(c) < 90 and re.search(ROLE_WORDS, c, re.I) and not c.lower().startswith(("we ", "you ", "the ", "our ")):
            c = re.sub(r"^(job title|position|role)\s*[:\-]\s*", "", c, flags=re.I)
            return c[:80]
    return "Open Role"


ATS_HOSTS = ("linkedin", "indeed", "glassdoor", "greenhouse", "lever", "workday", "myworkdayjobs", "smartrecruiters",
             "ashbyhq", "workable", "jobvite", "icims", "bamboohr", "recruitee", "teamtailor", "jobstreet", "mycareersfuture")


def guess_company(text: str, site_name: str = "", host: str = "") -> str:
    m = re.search(r"(?:company|organisation|organization|employer)[ \t]*[:\-][ \t]*([A-Z][\w&.\- ]{1,40})", text, re.I)
    if m:
        return m.group(1).strip()
    if site_name and not any(a in site_name.lower() for a in ATS_HOSTS):
        return site_name
    if host and not any(a in host for a in ATS_HOSTS):
        parts = [p for p in host.split(".") if p not in ("www", "jobs", "careers", "career", "apply", "com", "co", "io", "net", "org", "sg", "uk", "ai")]
        if parts:
            return parts[-1].capitalize()
    m = re.search(r"\bAbout[ \t]+([A-Z][\w&.\-]+(?:[ \t]+[A-Z][\w&.\-]+){0,3})", text)
    if m and m.group(1).lower() not in ("the role", "you", "us", "the team", "the job"):
        return m.group(1).strip()
    m = re.search(r"^[ \t]*([A-Z][\w&.]+(?:[ \t]+[A-Z][\w&.]+){0,2})[ \t]+(?:is|was)[ \t]+(?:a|an|the|born|founded|building)\b", text, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bat[ \t]+([A-Z][\w&.\-]+(?:[ \t]+[A-Z][\w&.\-]+){0,2})", text)
    if m:
        return m.group(1).strip()
    return ""


def guess_location(text: str) -> str:
    counts = Counter()
    for loc in LOCATIONS:
        n = len(re.findall(rf"\b{re.escape(loc)}\b", text, re.I))
        if n:
            counts[loc] = n
    return counts.most_common(1)[0][0] if counts else ""


def guess_industry(text: str, company: str = "") -> str:
    co = company.strip().lower()
    if co:
        for ind, companies in INDUSTRY_COMPANIES.items():
            if any(c.lower() == co for c in companies):
                return ind
    about = _section(text, [rf"about {re.escape(company)}" if company else "about us", "about us", "who we are", "about the company"])
    t = f" {text.lower()} {about.lower() * 3} "
    scores = {ind: sum(t.count(k) for k in keys) for ind, keys in INDUSTRY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "General business"


def _section(text: str, heads: list[str]) -> str:
    rx = re.compile(rf"^\s*(?:{'|'.join(heads)})\b.*$", re.I | re.M)
    m = rx.search(text)
    if not m:
        return ""
    head_line = m.group(0)
    rest = text[m.end():]
    if ":" in head_line:
        rest = head_line.split(":", 1)[1] + rest
    stop = re.search(r"^\s*(?:about|benefits|what we offer|why join|perks|how to apply|nice to have|preferred|bonus|requirements|qualifications|what you(?:'|’)ll need|what we(?:'|’)re looking for|who you are|responsibilities|what you(?:'|’)ll do)\b.*$", rest, re.I | re.M)
    return rest[: stop.start()] if stop else rest[:3000]


def _bullets(block: str, limit: int = 8) -> list[str]:
    items = []
    for line in block.splitlines():
        line = line.strip(" •*-–·\t")
        if 15 < len(line) < 240:
            items.append(line)
    return items[:limit]


def search_title(title: str) -> str:
    """Short, searchable form of a job title (drops region, team and 'to the X unit' qualifiers)."""
    t = REGION_SUFFIX.sub("", title).strip() or title
    t = re.split(r"\s+(?:to|for|within|at)\s+(?:the\s+)?|\s[-–—|]\s|\s*[(,]", t)[0].strip()
    return t or title


FUNCTION_FAMILIES = {
    "finance": r"cfo|financ\w*|finanz\w*|fp&a|controller|treasur\w*|tesorer\w*|accounting|accountant|comptroller|daf|contable|contabilidad",
    "sales": r"sales|pre-?sales|account (?:executive|director|manager)|business development|revenue|cro|commercial|go-to-market|gtm|comercial|ventas|vertrieb\w*",
    "engineering": r"engineer\w*|developer|cto|architect|devops|sre|software|programmer",
    "people": r"hr|human resources|recursos humanos|rrhh|people|talent|recruit\w*|chro",
    "marketing": r"marketing|cmo|brand",
    "operations": r"operations|operaciones|coo|supply chain|logistics|procurement",
    "data": r"data|analytics|machine learning|ml|ai|scientist",
    "product": r"product",
    "legal": r"legal|counsel|compliance",
}
CXO = {"financial": ("CFO", "Finance"), "finance": ("CFO", "Finance"), "technology": ("CTO", "Engineering"), "operating": ("COO", "Operations"),
       "marketing": ("CMO", "Marketing"), "people": ("CPO", "People"), "human resources": ("CHRO", "HR"), "revenue": ("CRO", "Sales"),
       "commercial": ("CCO", "Commercial"), "information": ("CIO", "IT"), "data": ("CDO", "Data"), "product": ("CPO", "Product")}


LOCALE = {"Barcelona": "es", "Madrid": "es", "Valencia": "es", "Bilbao": "es", "Seville": "es", "Mexico City": "es", "Munich": "de",
          "Frankfurt": "de", "Berlin": "de", "Hamburg": "de", "Vienna": "de", "Zurich": "de", "Basel": "de", "Paris": "fr", "Lyon": "fr",
          "Brussels": "fr", "Geneva": "fr", "Milan": "it", "Rome": "it", "Lisbon": "pt", "Porto": "pt", "São Paulo": "pt"}
# Titles senior people actually use on local-language LinkedIn profiles
LOCAL_TITLES = {
    "es": {"finance": ["Director Financiero", "Directora Financiera", "Controller Financiero"], "sales": ["Director Comercial"],
           "operations": ["Director de Operaciones"], "people": ["Director de Recursos Humanos"], "marketing": ["Director de Marketing"]},
    "de": {"finance": ["Leiter Finanzen", "Kaufmännischer Leiter"], "sales": ["Vertriebsleiter"], "operations": ["Leiter Operations"]},
    "fr": {"finance": ["Directeur Financier", "DAF"], "sales": ["Directeur Commercial"], "operations": ["Directeur des Opérations"]},
    "it": {"finance": ["Direttore Finanziario"], "sales": ["Direttore Commerciale"]},
    "pt": {"finance": ["Diretor Financeiro"], "sales": ["Diretor Comercial"]},
}
INDUSTRY_TERMS = {
    "performance materials": {"en": "materials", "es": "materiales", "de": "Werkstoffe", "fr": "matériaux", "it": "materiali", "alt": ["specialty", "especialidades", "additives", "aditivos", "coatings"]},
    "chemical": {"en": "chemicals", "es": "química", "de": "Chemie", "fr": "chimie", "it": "chimica", "pt": "química", "alt": ["chemical", "quimica", "químico", "químicos"]},
    "industrial": {"en": "industrial", "es": "industrial", "de": "Industrie", "fr": "industriel", "it": "industriale", "alt": ["industria", "manufacturing", "fabricación"]},
    "pharma": {"en": "pharmaceutical", "es": "farmacéutica", "de": "Pharma", "fr": "pharmaceutique", "alt": ["pharma", "farma"]},
    "distribution": {"en": "distribution", "es": "distribución", "de": "Distribution", "fr": "distribution", "alt": ["distributor", "distribuidor"]},
    "automotive": {"en": "automotive", "es": "automoción", "de": "Automobil", "fr": "automobile", "alt": ["automotriz"]},
    "energy": {"en": "energy", "es": "energía", "de": "Energie", "fr": "énergie", "alt": ["oil", "gas", "utilities"]},
    "consumer goods": {"en": "FMCG", "es": "gran consumo", "alt": ["consumer goods", "cpg"]},
    "private equity": {"en": "private equity", "es": "private equity", "alt": ["portfolio company", "pe-backed"]},
}


def _industry_key(name: str) -> str:
    n = name.lower()
    return next((k for k in INDUSTRY_TERMS if k in n or n in k or n.rstrip("s") in k), "")


def industry_query_term(name: str, lang: str) -> str:
    k = _industry_key(name)
    return INDUSTRY_TERMS[k].get(lang) or INDUSTRY_TERMS[k]["en"] if k else name


def industry_terms(names: list[str]) -> list[str]:
    """Every word (any language) that signals a candidate comes from one of these industries."""
    out = []
    for n in names:
        k = _industry_key(n)
        out += [n] + ([v for key, v in INDUSTRY_TERMS[k].items() if key != "alt"] + INDUSTRY_TERMS[k]["alt"] if k else [])
    return list(dict.fromkeys(t for t in out if t))


def xray_queries(role: dict, tmap: dict, titles: list[str], companies: list[str], loc: str, budget: int = 6) -> list[str]:
    """Executive-researcher style X-ray: local-language titles x target industries in the target city.
    Title + quoted company + city combinations are avoided: search APIs return almost nothing for them."""
    lang = LOCALE.get(loc, "")
    local = LOCAL_TITLES.get(lang, {}).get(role_family(role.get("title", "")), []) if role.get("seniority") in ("C-Level", "VP / Head", "Director") else []
    pool = list(dict.fromkeys(local[:2] + titles[:3]))
    terms = list(dict.fromkeys(industry_query_term(i, lang) for i in role.get("target_industries", [])))[:3]
    li = lambda *parts: " ".join(["site:linkedin.com/in", *[p for p in parts if p]])
    if terms:
        pairs = sorted(((i, j) for i in range(min(3, len(pool))) for j in range(len(terms))), key=lambda p: (p[0] + p[1], p[0]))
        base = [li(f'"{pool[i]}"', terms[j], loc) for i, j in pairs]
    else:
        base = [li(f'"{t}"', loc) for t in pool[:4]]
    requested = [re.sub(r"\s*\(.*\)", "", c["name"]) for c in tmap.get("target_companies", []) if c.get("rationale") == "Requested by recruiter feedback"]
    req = [li(f'"{pool[0]}"', c, loc) for c in requested[:2]] if pool else []
    qs = base[:4] + req + base[4:]
    if is_technical_role(role) and companies and pool:
        qs.append(f"{_or(pool, 2)} {_or(companies[:4], 4)}{' ' + chr(34) + loc + chr(34) if loc else ''} (speaker OR panelist OR podcast OR interview) -jobs -hiring")
    return list(dict.fromkeys(qs))[:budget]


def role_family(title: str) -> str:
    t = search_title(title or "")
    for name, pat in FUNCTION_FAMILIES.items():
        if re.search(rf"\b(?:{pat})\b", t, re.I):
            return name
    return ""


def on_function(text: str, role_title: str) -> bool:
    """True when a title/headline is in the same job function as the role being searched (e.g. finance for a CFO search)."""
    fam = role_family(role_title)
    return not fam or bool(re.search(rf"\b(?:{FUNCTION_FAMILIES[fam]})\b", text or "", re.I))


def cxo(title: str) -> tuple[str, str] | None:
    m = re.search(r"\bchief\s+(\w+(?:\s+resources)?)\s+officer\b", title or "", re.I)
    return CXO.get(m.group(1).lower()) if m else None


def step_down(title: str) -> list[str]:
    """Titles one level below a C-level role, e.g. CFO -> Regional CFO / Finance Director."""
    x = cxo(title)
    if not x:
        return []
    abbr, area = x
    return [f"Regional {abbr}", f"{area} Director", f"VP {area}", f"Head of {area}"]


def clean_location(s: str) -> str:
    """Turn free text like 'based in barcelona or open to relocate' into a searchable place."""
    s = (s or "").strip()
    known = guess_location(s)
    if known:
        return known
    s = re.sub(r"^[-:\s]*(?:(?:based in|located in|only in|in|location)\b\s*[:\-]?\s*)?", "", s, flags=re.I)
    s = re.split(r"\s+(?:or|and|but|with|/)\s+|[,;(]", s)[0].strip(" .")
    return " ".join(w[:1].upper() + w[1:] for w in s.split()[:3] if re.search(r"\w", w))


def peer_titles(title: str, seniority: str) -> list[str]:
    region = REGION_SUFFIX.search(title)
    title = search_title(title)
    if seniority == "C-Level" and (x := cxo(title)):
        abbr, area = x
        return [title, f"Regional {abbr}", f"VP {area}", f"Head of {area}", f"{area} Director"]
    if GTM_ROLE.search(title) and seniority in ("Senior IC", "Manager / Lead", "Mid-level IC"):
        sfx = f" ({region.group(0).strip(' -–—,(|')})" if region else ""
        return [title + sfx, "Enterprise Account Executive", "Strategic Account Director", "Enterprise Account Manager",
                "Regional Sales Director", "Senior Sales Engineer"]
    core = re.sub(r"(?i)\b(senior|sr\.?|junior|jr\.?|lead|principal|staff|head of|director of|vp of|vice president of|chief)\b", "", title).strip(" ,-")
    core = core or title
    ladders = {
        "C-Level": [title, f"VP {core}", f"SVP {core}", f"Head of {core}"],
        "VP / Head": [title, f"Head of {core}", f"VP {core}", f"Director of {core}", f"Senior Director {core}"],
        "Director": [title, f"Director of {core}", f"Head of {core}", f"Senior Manager {core}", f"Lead {core}"],
        "Manager / Lead": [title, f"Lead {core}", f"Staff {core}", f"Principal {core}", f"{core} Manager"],
        "Senior IC": [title, f"Senior {core}", f"Lead {core}", f"Staff {core}", core],
        "Mid-level IC": [title, core, f"Senior {core}", f"{core} II"],
    }
    seen, out = set(), []
    for t in ladders.get(seniority, [title]):
        t = re.sub(r"\s+", " ", t).strip()
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def _same_co(a: str, b: str) -> bool:
    a, b = re.sub(r"\s*\(.*\)", "", a).lower().strip(), b.lower().strip()
    return bool(a and b) and (a == b or a.startswith(b + " ") or b.startswith(a + " "))


def market_segment(text: str, company: str = "") -> tuple[str, list[str]]:
    """Classify what the hiring firm sells from its own description; weights the intro/about-us text."""
    about = _section(text, [rf"about {re.escape(company)}" if company else "about us", "about us", "who we are"])
    t = f" {(text[:1200] + ' ' + about[:1500]).lower()} "
    scored = [(sum(t.count(k) for k in keys), name, players) for name, keys, players in MARKET_SEGMENTS]
    n, name, players = max(scored, key=lambda x: x[0])
    return (name, players) if n >= 2 else ("", [])


def direct_competitors(text: str, company: str, industry: str) -> tuple[list[str], str, str]:
    """Returns (competitors, market segment, basis)."""
    segment, players = market_segment(text, company)
    key = re.sub(r"\b(inc|ltd|labs|technologies|holdings|group|pte|ag|sa|plc|corp|corporation|limited)\b\.?", "", company.lower()).strip(" ,.")
    if key in COMPANY_COMPETITORS:
        known = COMPANY_COMPETITORS[key]
        overlap, seg = max((len(set(known) & set(ps)), name) for name, _, ps in MARKET_SEGMENTS)
        return known, seg if overlap >= 2 else segment, f"Known competitor set for {company}"
    if players:
        return [c for c in players if not _same_co(c, company)], segment, f"Detected from {company or 'the company'}'s product description"
    return [c for c in INDUSTRY_COMPANIES.get(industry, []) if not _same_co(c, company)], "", (f"{industry} industry leaders (no specific product segment detected)" if industry in INDUSTRY_COMPANIES
           else "Not detected from the JD — add a web-search or AI key to look up competitors")


def _a(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def analyze(text: str, hints: dict) -> dict:
    title = hints.get("title") or guess_title(text, hints.get("page_title", ""))
    company = hints.get("company") or guess_company(text, hints.get("site_name", ""), hints.get("host", ""))
    location = hints.get("location") or guess_location(text)
    industry = guess_industry(text, company)
    seniority = seniority_of(title)
    core = strip_boilerplate(text)
    skills = find_skills(core)
    req_block = _section(core, ["requirements", "qualifications", "what you(?:'|’)ll need", "what we(?:'|’)re looking for", "must have", "you have", "who you are", "skills"])
    req_skills = {s for s, _, _ in find_skills(req_block)} if req_block else set()
    ranked = sorted(skills, key=lambda x: (x[0] not in req_skills, -x[2]))
    must = [s for s, _, n in ranked if s in req_skills or n >= 2][:10] or [s for s, _, _ in ranked[:6]]
    nice = [s for s, _, _ in ranked if s not in must][:10]
    yrs = re.search(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?years", text, re.I)
    resp = _bullets(_section(text, ["responsibilities", "what you(?:'|’)ll do", "the role", "your role", "key responsibilities", "duties"]))
    reqs = _bullets(req_block)
    cats = Counter(cat for s, cat, _ in skills)
    function = cats.most_common(1)[0][0] if cats else "General"
    comps, segment, comp_basis = direct_competitors(core, company, industry)
    peers = [c for c in INDUSTRY_COMPANIES.get(industry, []) if not _same_co(c, company) and c not in comps]
    targets = comps[:6] + peers
    adjacent = [c for i in ("Consumer Internet", "Enterprise SaaS") if i != industry for c in INDUSTRY_COMPANIES[i][:4]]
    gtm = bool(GTM_ROLE.search(f"{title}\n{text[:400]}"))
    if gtm:
        sellers = [c for c in GTM_SELLERS if c.lower() != company.lower() and c not in targets[:6]]
        targets = targets[:6] + sellers[:4]
        adjacent = [c for c in INDUSTRY_COMPANIES.get("Enterprise SaaS", []) if c not in targets and c.lower() != company.lower()][:4]
    exec_level = seniority in ("C-Level", "VP / Head", "Director")

    role = {
        "title": title, "company": company or "Hiring company", "location": location or "Not specified",
        "seniority": seniority, "function": function, "industry": industry,
        "years_experience": f"{yrs.group(1)}+ years" if yrs else ("12+ years" if exec_level else "Not specified"),
        "summary": f"{title} ({seniority}) role in {industry} focused on {', '.join(must[:4]) or 'core domain expertise'}.",
        "must_have_skills": must, "nice_to_have_skills": nice,
        "responsibilities": resp or reqs[:5], "requirements": reqs,
        "education": "Bachelor's or higher" if re.search(r"bachelor|degree|master|phd|mba", text, re.I) else "Not specified",
        "compensation_hint": "",
    }
    brief = {
        "executive_summary": f"{company or 'The client'} is hiring {_a(title)} {title}{' in ' + location if location else ''}. "
                             f"Prioritise candidates with proven depth in {', '.join(must[:3]) or 'the core skills'} from "
                             f"{industry} peers" + (f", with {role['years_experience']} of relevant experience." if yrs or exec_level else "."),
        "ideal_candidate_persona": f"{_a(seniority).capitalize()} {seniority} operator currently at {_a(industry)} {industry} leader such as "
                                   f"{', '.join(targets[:3]) or 'a market peer'}, who has shipped outcomes using "
                                   f"{', '.join(must[:4]) or 'the required stack'} and wants a broader remit.",
        "selling_points": ["Scope and ownership of a high-impact mandate", f"Exposure to {industry.lower()} growth",
                           "Opportunity to shape team, culture and roadmap"],
        "intake_questions": ["What are the 2-3 outcomes this hire must deliver in the first 12 months?",
                             "Which companies or teams would you most like to hire from (and avoid)?",
                             "What is the approved compensation band and flexibility on location?",
                             "Who are the key stakeholders and what does the interview loop look like?",
                             "Why is the role open now and what happened with previous hires?"],
        "red_flags": ["Title inflation without matching scope", "Short tenures (<1.5 yrs) across recent roles",
                      "Skill keywords without evidence of shipped outcomes"],
        "evaluation_criteria": [{"criterion": "Core skills match", "weight": 35}, {"criterion": "Relevant company / domain", "weight": 25},
                                {"criterion": "Seniority & scope", "weight": 20}, {"criterion": "Location fit", "weight": 10},
                                {"criterion": "Public signals (OSS, talks, writing)", "weight": 10}],
    }
    talent_map = {
        "hiring_company_profile": {
            "name": company or "Hiring company",
            "description": f"{industry} organisation{' in ' + segment if segment else ''} hiring for {title}.",
            "market_segment": segment,
            "direct_competitors": comps[:6],
            "competitor_basis": comp_basis,
            "culture_signals": [s for s in ["Fast-paced" if re.search(r"fast[- ]paced|startup", text, re.I) else "",
                                            "Remote-friendly" if re.search(r"remote|hybrid", text, re.I) else "",
                                            "Data-driven" if re.search(r"data[- ]driven|metrics", text, re.I) else "",
                                            "Customer-obsessed" if re.search(r"customer", text, re.I) else ""] if s],
            "current_team_patterns": [f"Team likely built around {', '.join(must[:3])}" if must else "Add an LLM key for team pattern analysis"],
        },
        "target_companies": [{"name": c, "tier": "Primary", "rationale": f"Direct competitor of {company or 'the hiring firm'}" + (f" in {segment.lower()}" if segment else "")} for c in targets[:6]]
        + [{"name": c, "tier": "Secondary", "rationale": "Enterprise tech sales org selling to engineering buyers" if gtm else f"{industry} peer with comparable talent"} for c in targets[6:10]]
        + [{"name": c, "tier": "Adjacent", "rationale": "Adjacent industry with strong talent density in required skills"} for c in adjacent[:4]],
        "peer_titles": peer_titles(title, seniority),
        "talent_hubs": [{"location": location or "Global", "rationale": "Primary hiring location"}],
        "market_trends": [
            {"trend": f"High competition for {must[0] if must else 'specialist'} talent", "implication": "Lead with mission and scope; move fast on process"},
            {"trend": "AI adoption reshaping role expectations", "implication": "Screen for hands-on AI/automation literacy"},
            {"trend": "Hybrid work is the default expectation", "implication": "Be explicit about flexibility in outreach"},
        ],
        "common_attributes": [{"attribute": f"Hands-on with {s}", "prevalence": max(40, 90 - i * 8)} for i, s in enumerate(must[:6])],
        "career_paths": [f"{peer_titles(title, seniority)[-1]} → {title}", f"{title} at {targets[0] if targets else 'peer company'} → {title} at {company or 'client'}"],
        "talent_pool_estimate": "Medium" if exec_level else "Large",
        "competition_level": "High" if exec_level or industry in ("AI & Machine Learning", "Fintech & Payments") else "Medium",
        "diversity_notes": "Broaden to adjacent industries and non-traditional backgrounds to widen the slate.",
    }
    strategy = build_strategy(role, talent_map)
    return {"role": role, "recruiter_brief": brief, "talent_map": talent_map, "strategy": strategy}


def _or(items: list[str], n: int) -> str:
    items = [i for i in items if i][:n]
    return "(" + " OR ".join(f'"{i}"' for i in items) + ")" if items else ""


def build_strategy(role: dict, tmap: dict) -> dict:
    must, nice = role.get("must_have_skills", []), role.get("nice_to_have_skills", [])
    titles = list(dict.fromkeys(search_title(t) for t in (tmap.get("peer_titles") or [role["title"]])))
    tiers = tmap.get("target_companies", [])
    ranked = [c for c in tiers if c.get("tier") == "Primary"][:3] + [c for c in tiers if c.get("tier") != "Primary"]
    companies = list(dict.fromkeys(re.sub(r"\s*\(.*\)", "", c["name"]).replace(" Copilot", "") for c in ranked or tiers))
    loc = role.get("location", "")
    loc = "" if loc.lower() in ("not specified", "remote", "global") else loc
    loc_q = f' "{loc}"' if loc else ""
    li = " AND ".join(x for x in [_or(titles, 4), _or(must, 4), _or(companies, 6)] if x)
    xray = f"site:linkedin.com/in {_or(titles, 2)} {_or(must, 2)}{loc_q} -jobs"
    return {
        "skills_matrix": [{"skill": s, "category": "Core", "importance": "Must-have", "signal": "Recent role responsibilities, projects, GitHub repos"} for s in must]
        + [{"skill": s, "category": "Supporting", "importance": "Nice-to-have", "signal": "Profile keywords, certifications, side projects"} for s in nice[:6]],
        "channels": [
            {"channel": "Open web X-ray (public LinkedIn profiles)", "priority": "High", "tactic": "Google X-ray of public LinkedIn profiles for peer titles at primary companies; reach out by email or a role-specific note"},
            {"channel": "GitHub", "priority": "High" if role.get("function") in ("Languages", "Backend", "Frontend", "Data & AI", "Cloud & Infra") else "Low", "tactic": "Find active contributors by language/location; reference their repos in outreach"},
            {"channel": "Referrals & alumni networks", "priority": "Medium", "tactic": "Mine alumni of target companies and the hiring team's networks"},
            {"channel": "Communities, events & content", "priority": "Medium", "tactic": "Speakers, meetup organisers, authors of relevant posts/papers"},
        ],
        "boolean_strings": {
            "linkedin": li,
            "google_xray": xray,
            "github": f"{'language:' + must[0].lower() if must else ''}{' location:' + chr(34) + loc + chr(34) if loc else ''} followers:>20".strip(),
        },
        # one title per query, no OR/minus operators: search APIs (e.g. DuckDuckGo via SerpAPI) drop complex site: queries
        "xray_queries": xray_queries(role, tmap, titles, companies, loc),
        "outreach_template": (
            f"Hi {{first_name}},\n\nI'm working with {role.get('company')} on a {role['title']} mandate{(' in ' + loc) if loc else ''}. "
            f"Your work on {{hook}} stood out — particularly your experience with {', '.join(must[:2]) or 'this space'}.\n\n"
            "The role offers real scope: {selling_point}. Open to a 15-minute confidential chat this week?\n\nBest,\n{recruiter}"
        ),
        "timeline": [{"week": "Week 1", "focus": "Intake, calibration profiles, first 30 outreach"},
                     {"week": "Week 2", "focus": "Expand to secondary/adjacent companies; screen calls"},
                     {"week": "Week 3", "focus": "Present shortlist of 5-8; hiring manager feedback"},
                     {"week": "Week 4+", "focus": "Interviews, references, offer management"}],
    }
