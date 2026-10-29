import clsx from "clsx";
import { AlertCircle, FileSpreadsheet, FileText, Globe, Link2, Loader2, Sparkles, Type, UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { GithubIcon } from "../components/ui";
import type { Status } from "../types";

const SAMPLE = `Head of Data Platform
Grab — Singapore

About Grab
Grab is Southeast Asia's leading superapp, providing deliveries, mobility and financial services.

What you'll do
- Lead a team of 25+ data and platform engineers building our real-time data platform
- Own the strategy and roadmap for streaming, lakehouse and ML infrastructure
- Partner with product, analytics and machine learning teams across the region
- Drive reliability, cost efficiency and governance of petabyte-scale data systems

What you'll need
- 12+ years of experience in data engineering, with 5+ years leading engineering teams
- Deep expertise in Spark, Kafka, Airflow and cloud data platforms (AWS)
- Strong programming skills in Python, Scala or Java
- Experience with Kubernetes, Terraform and modern Data Engineering practices
- Track record of stakeholder management and cross-functional leadership

Nice to have
- Experience in fintech or payments; exposure to Databricks, Snowflake or dbt`;

type Mode = "link" | "file" | "text";

export default function NewSearch({ status }: { status: Status | null }) {
  const [mode, setMode] = useState<Mode>("link");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [sources, setSources] = useState({ github: true, linkedin: false, open_web: true });
  const [max, setMax] = useState(25);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const ready = (mode === "link" && url.trim()) || (mode === "file" && file) || (mode === "text" && text.trim().length > 50);

  async function submit() {
    setBusy(true); setErr("");
    const fd = new FormData();
    if (mode === "link") fd.append("url", url.trim());
    if (mode === "file" && file) fd.append("file", file);
    if (mode === "text") fd.append("text", text);
    fd.append("company", company); fd.append("location", location);
    Object.entries(sources).forEach(([k, v]) => fd.append(k, String(v)));
    fd.append("max_candidates", String(max));
    try {
      const { id } = await api.createJob(fd);
      navigate(`/jobs/${id}`);
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  }

  const modes: { key: Mode; label: string; icon: React.ReactNode; hint: string }[] = [
    { key: "link", label: "Job link", icon: <Link2 className="h-4 w-4" />, hint: "Careers page, Greenhouse, Lever, Workday…" },
    { key: "file", label: "Upload file", icon: <UploadCloud className="h-4 w-4" />, hint: "Word, PDF, Excel or CSV" },
    { key: "text", label: "Paste text", icon: <Type className="h-4 w-4" />, hint: "Copy & paste the JD" },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">New sourcing search</h1>
        <p className="text-sm text-slate-500 mt-1">Your AI executive recruiter will analyse the role, map the talent market around the hiring firm, design a sourcing strategy and build a scored shortlist.</p>
      </div>

      <div className="card">
        <div className="p-6 space-y-6">
          <div>
            <div className="label">1. Job description</div>
            <div className="grid grid-cols-3 gap-3">
              {modes.map((m) => (
                <button key={m.key} onClick={() => setMode(m.key)}
                  className={clsx("text-left rounded-xl border p-3.5 transition", mode === m.key ? "border-brand-500 ring-2 ring-brand-100 bg-brand-50/40" : "border-slate-200 hover:border-slate-300")}>
                  <div className={clsx("flex items-center gap-2 text-sm font-medium", mode === m.key ? "text-brand-700" : "text-slate-800")}>{m.icon}{m.label}</div>
                  <div className="text-xs text-slate-500 mt-1 hidden sm:block">{m.hint}</div>
                </button>
              ))}
            </div>
            <div className="mt-4">
              {mode === "link" && (
                <div className="relative">
                  <Globe className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input className="input pl-9 py-2.5" placeholder="https://careers.company.com/jobs/head-of-data" value={url} onChange={(e) => setUrl(e.target.value)} />
                </div>
              )}
              {mode === "file" && (
                <div onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
                  onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
                  className={clsx("cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition", drag ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-brand-400 hover:bg-slate-50")}>
                  <input ref={fileRef} type="file" hidden accept=".docx,.pdf,.xlsx,.xlsm,.csv,.txt,.md" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                  {file ? (
                    <div className="inline-flex items-center gap-3 rounded-lg bg-white border border-slate-200 px-4 py-2.5">
                      {/\.(xlsx|xlsm|csv)$/i.test(file.name) ? <FileSpreadsheet className="h-5 w-5 text-emerald-600" /> : <FileText className="h-5 w-5 text-brand-600" />}
                      <span className="text-sm font-medium">{file.name}</span>
                      <span className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB</span>
                      <button onClick={(e) => { e.stopPropagation(); setFile(null); }}><X className="h-4 w-4 text-slate-400 hover:text-slate-700" /></button>
                    </div>
                  ) : (
                    <>
                      <UploadCloud className="h-8 w-8 mx-auto text-slate-400" />
                      <div className="mt-2 text-sm font-medium text-slate-700">Drop your JD here or <span className="text-brand-600">browse</span></div>
                      <div className="text-xs text-slate-500 mt-1">.docx · .pdf · .xlsx · .csv · .txt</div>
                    </>
                  )}
                </div>
              )}
              {mode === "text" && (
                <div>
                  <textarea className="input min-h-[220px] font-mono text-[13px]" placeholder="Paste the full job description…" value={text} onChange={(e) => setText(e.target.value)} />
                  <button className="text-xs text-brand-600 hover:underline mt-1.5" onClick={() => setText(SAMPLE)}>Use a sample JD</button>
                </div>
              )}
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="label">2. Hiring company <span className="text-slate-400 font-normal">(optional)</span></div>
              <input className="input" placeholder="Auto-detected from JD" value={company} onChange={(e) => setCompany(e.target.value)} />
            </div>
            <div>
              <div className="label">Location <span className="text-slate-400 font-normal">(optional)</span></div>
              <input className="input" placeholder="Auto-detected from JD" value={location} onChange={(e) => setLocation(e.target.value)} />
            </div>
          </div>

          <div>
            <div className="label">3. Sourcing channels</div>
            <div className="grid sm:grid-cols-2 gap-3">
              <Toggle on={sources.github} onClick={() => setSources((s) => ({ ...s, github: !s.github }))} icon={<GithubIcon />} label="GitHub" sub="Public profiles & repos" />
              <Toggle on={sources.open_web} onClick={() => setSources((s) => ({ ...s, open_web: !s.open_web }))} icon={<Globe className="h-4 w-4 text-emerald-600" />} label="Open web" sub={status?.search ? "Public LinkedIn profiles, sites, talks" : "Needs a web-search key (Integrations)"} />
            </div>
            <div className="mt-4 flex items-center gap-4">
              <span className="text-sm text-slate-600 w-40">Max candidates: <b>{max}</b></span>
              <input type="range" min={5} max={60} step={5} value={max} onChange={(e) => setMax(+e.target.value)} className="flex-1 accent-brand-600" />
            </div>
          </div>

          {(!status?.llm || !status?.search) && (
            <div className="flex gap-3 rounded-lg bg-amber-50 border border-amber-200 p-3.5 text-sm text-amber-800">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <div>
                {!status?.llm && <div>Running in <b>heuristic mode</b> — add an OpenAI or Anthropic key for full AI talent mapping and candidate reasoning.</div>}
                {!status?.search && <div>No web-search key — LinkedIn/open-web results will be provided as ready-to-run X-ray search links.</div>}
                <Link to="/settings" className="font-medium underline">Configure integrations</Link>
              </div>
            </div>
          )}
          {err && <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">{err}</div>}
        </div>
        <div className="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4 bg-slate-50/60 rounded-b-xl">
          <button className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
          <button className="btn-primary px-5" disabled={!ready || busy} onClick={submit}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}Run sourcing agent
          </button>
        </div>
      </div>
    </div>
  );
}

function Toggle({ on, onClick, icon, label, sub }: { on: boolean; onClick: () => void; icon: React.ReactNode; label: string; sub: string }) {
  return (
    <button onClick={onClick} className={clsx("flex items-center gap-3 rounded-xl border p-3 text-left transition", on ? "border-brand-500 bg-brand-50/40" : "border-slate-200 opacity-70")}>
      <div className="h-8 w-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center">{icon}</div>
      <div className="flex-1"><div className="text-sm font-medium">{label}</div><div className="text-xs text-slate-500">{sub}</div></div>
      <div className={clsx("h-5 w-9 rounded-full p-0.5 transition", on ? "bg-brand-600" : "bg-slate-300")}><div className={clsx("h-4 w-4 rounded-full bg-white transition", on && "translate-x-4")} /></div>
    </button>
  );
}
