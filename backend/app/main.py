import asyncio
import csv
import io
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, ingest, llm, sourcing, store

app = FastAPI(title="Talent Sourcing Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STAGES = ["Sourced", "Shortlisted", "Contacted", "Interviewing", "Offer", "Hired", "Rejected"]


def _summary(j: dict) -> dict:
    counts = {s: 0 for s in STAGES}
    for c in j.get("candidates", []):
        counts[c.get("stage", "Sourced")] = counts.get(c.get("stage", "Sourced"), 0) + 1
    return {"id": j["id"], "created_at": j["created_at"], "status": j["status"], "mode": j.get("mode"),
            "title": j.get("role", {}).get("title") or j["source"].get("label") or "Analysing…",
            "company": j.get("role", {}).get("company", ""), "location": j.get("role", {}).get("location", ""),
            "seniority": j.get("role", {}).get("seniority", ""), "source": j["source"], "stage_counts": counts,
            "total": len(j.get("candidates", [])), "top_score": max([c["score"] for c in j.get("candidates", [])], default=0),
            "steps": j["steps"]}


@app.get("/api/status")
def status():
    return {"llm": llm.provider(), "search": sourcing.search_provider(),
            "github_token": bool(store.get_setting("GITHUB_TOKEN") or store.get_setting("GH_TOKEN")), "stages": STAGES}


class SettingsIn(BaseModel):
    values: dict[str, str]


@app.get("/api/settings")
def get_settings():
    return {k: bool(store.get_setting(k)) if "KEY" in k or "TOKEN" in k else store.get_setting(k) for k in store.SETTING_KEYS}


@app.post("/api/settings")
def set_settings(body: SettingsIn):
    store.update_settings(body.values)
    return status()


@app.get("/api/jobs")
def jobs():
    return [_summary(j) for j in store.list_jobs()]


@app.post("/api/jobs")
async def create_job(
    background: BackgroundTasks,
    url: str = Form(""), text: str = Form(""), company: str = Form(""), location: str = Form(""),
    github: bool = Form(True), linkedin: bool = Form(True), open_web: bool = Form(True),
    max_candidates: int = Form(25), file: UploadFile | None = File(None),
):
    raw = {"company": company.strip(), "location": location.strip()}
    if file is not None and file.filename:
        data = await file.read()
        try:
            raw["text"] = ingest.parse_file(file.filename, data)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"Could not read file: {e}")
        source = {"type": "file", "label": file.filename}
    elif url.strip():
        try:
            page = await ingest.fetch_url(url.strip())
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"Could not fetch URL ({e}). Some job boards block bots — paste the JD text instead.")
        raw.update(page)
        source = {"type": "link", "label": url.strip()}
    elif text.strip():
        raw["text"] = text.strip()
        source = {"type": "text", "label": "Pasted job description"}
    else:
        raise HTTPException(400, "Provide a JD link, file, or text")
    job_id = uuid.uuid4().hex[:12]
    opts = {"github": github, "linkedin": linkedin, "open_web": open_web, "max_candidates": max(5, min(60, max_candidates))}
    store.save_job(agent.new_job(job_id, source, opts))
    background.add_task(agent.run_pipeline, job_id, raw)
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    j = store.load_job(job_id)
    if not j:
        raise HTTPException(404)
    return j


@app.delete("/api/jobs/{job_id}")
def del_job(job_id: str):
    store.delete_job(job_id)
    return {"ok": True}


class CandidatePatch(BaseModel):
    stage: str | None = None
    notes: str | None = None
    rating: int | None = None


@app.patch("/api/jobs/{job_id}/candidates/{cid}")
def patch_candidate(job_id: str, cid: str, body: CandidatePatch):
    j = store.load_job(job_id)
    if not j:
        raise HTTPException(404)
    for c in j["candidates"]:
        if c["id"] == cid:
            for k, v in body.model_dump(exclude_none=True).items():
                if k == "stage" and v not in STAGES:
                    raise HTTPException(400, "bad stage")
                c[k] = v
            store.save_job(j)
            return c
    raise HTTPException(404)


class CandidateIn(BaseModel):
    name: str
    url: str = ""
    headline: str = ""
    company: str = ""
    location: str = ""
    notes: str = ""


@app.post("/api/jobs/{job_id}/candidates")
def add_candidate(job_id: str, body: CandidateIn):
    j = store.load_job(job_id)
    if not j:
        raise HTTPException(404)
    src = "LinkedIn" if "linkedin.com" in body.url else ("GitHub" if "github.com" in body.url else "Manual")
    c = sourcing._new_candidate(**body.model_dump(), source=src, summary=body.headline, evidence=f"{body.headline} {body.company} {body.notes}")
    h = agent.heuristic_score(c, j)
    c.update({k: h[k] for k in ("score", "breakdown", "skills", "strengths", "concerns")})
    c["rationale"] = "; ".join(c["strengths"]) or "Manually added"
    j["candidates"].append(c)
    j["candidates"].sort(key=lambda x: -x["score"])
    store.save_job(j)
    return c


@app.post("/api/jobs/{job_id}/resource")
async def resource(job_id: str, background: BackgroundTasks):
    j = store.load_job(job_id)
    if not j or j["status"] == "running":
        raise HTTPException(400, "Job not found or still running")

    async def go():
        r = agent.Run(store.load_job(job_id))
        r.job["status"] = "running"
        r.step("sourcing", "running")
        await agent.source_candidates(r)
        r.step("sourcing", "done")
        await agent.score_candidates(r, llm.provider() is not None)
        r.job["status"] = "complete"
        r.log("Re-sourcing complete")

    background.add_task(go)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/export.csv")
def export(job_id: str):
    j = store.load_job(job_id)
    if not j:
        raise HTTPException(404)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Score", "Stage", "Headline", "Company", "Location", "Source", "URL", "Email", "Matched skills", "Rationale", "Notes"])
    for c in j["candidates"]:
        w.writerow([c["name"], c["score"], c["stage"], c["headline"], c["company"], c["location"], c["source"], c["url"], c["email"],
                    ", ".join(c.get("skills", [])), c.get("rationale", ""), c.get("notes", "")])
    buf.seek(0)
    name = (j.get("role", {}).get("title") or "candidates").replace(" ", "_")
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}_shortlist.csv"'})


DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
