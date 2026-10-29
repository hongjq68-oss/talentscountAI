import clsx from "clsx";
import {
  Activity, AlertTriangle, ArrowRight, Building2, CheckCircle2, ChevronLeft, CircleDashed, ClipboardList, Compass, Download, ExternalLink,
  Flame, KanbanSquare, LayoutList, Lightbulb, Loader2, MapPin, MessageSquareQuote, Plus, RefreshCw, Search, Target, TrendingUp, Users, Wand2, XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, STAGES } from "../api";
import CandidateDrawer, { ProfileLink, SourceIcon } from "../components/CandidateDrawer";
import RefinePanel from "../components/RefinePanel";
import { Avatar, Badge, Card, CopyButton, Empty, GithubIcon, LinkedinIcon, List, ScoreRing, Tabs, tierTone } from "../components/ui";
import type { Candidate, Job } from "../types";

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState("overview");
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(() => api.job(id!).then(setJob).catch((e) => setErr(e.message)), [id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (job?.status !== "running") return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [job?.status, load]);

  const patch = async (cid: string, p: Partial<Candidate>) => {
    setJob((j) => j && { ...j, candidates: j.candidates.map((c) => (c.id === cid ? { ...c, ...p } : c)) });
    await api.patchCandidate(id!, cid, p);
  };

  if (err) return <div className="p-8 text-rose-600">{err}</div>;
  if (!job) return <div className="p-10 flex justify-center"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>;

  const role = job.role || ({} as Job["role"]);
  const ready = (k: string) => job.steps.find((s) => s.key === k)?.status === "done";
  const shortlisted = job.candidates.filter((c) => c.stage === "Shortlisted").length;
  const openC = job.candidates.find((c) => c.id === open);

  return (
    <div className="max-w-7xl mx-auto p-6 lg:p-8 space-y-6">
      <div>
        <Link to="/jobs" className="text-sm text-slate-500 hover:text-slate-800 inline-flex items-center gap-1"><ChevronLeft className="h-4 w-4" />All searches</Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">{role.title || "Analysing job description…"}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
              {role.company && <span className="flex items-center gap-1.5"><Building2 className="h-4 w-4" />{role.company}</span>}
              {role.location && <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4" />{role.location}</span>}
              {role.seniority && <Badge tone="violet">{role.seniority}</Badge>}
              {role.industry && <Badge>{role.industry}</Badge>}
              {job.mode && <Badge tone={job.mode.startsWith("AI") ? "green" : "amber"}>{job.mode}</Badge>}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" disabled={job.status === "running" || !ready("strategy")} onClick={() => setTab("refine")}><Wand2 className="h-4 w-4" />Refine search</button>
            <button className="btn-secondary" disabled={job.status === "running"} onClick={async () => { await api.resource(job.id); setTimeout(load, 300); }}><RefreshCw className="h-4 w-4" />Re-source</button>
            <a className="btn-secondary" href={api.exportUrl(job.id)}><Download className="h-4 w-4" />Export CSV</a>
          </div>
        </div>
      </div>

      {job.status !== "complete" && <Progress job={job} />}

      <Tabs value={tab} onChange={setTab} tabs={[
        { key: "overview", label: "Recruiter brief", icon: <ClipboardList className="h-4 w-4" /> },
        { key: "map", label: "Talent map", icon: <Compass className="h-4 w-4" /> },
        { key: "strategy", label: "Sourcing strategy", icon: <Target className="h-4 w-4" /> },
        { key: "refine", label: "Refine", icon: <Wand2 className="h-4 w-4" />, count: job.refinement?.rounds.length || undefined },
        { key: "candidates", label: "Candidates", icon: <Users className="h-4 w-4" />, count: job.candidates.length },
        { key: "pipeline", label: "Pipeline", icon: <KanbanSquare className="h-4 w-4" />, count: shortlisted },
        { key: "activity", label: "Agent activity", icon: <Activity className="h-4 w-4" /> },
      ]} />

      {tab === "overview" && (ready("analyze") ? <Overview job={job} /> : <Waiting />)}
      {tab === "map" && (ready("talent_map") ? <TalentMapView job={job} /> : <Waiting />)}
      {tab === "strategy" && (ready("strategy") ? <StrategyView job={job} /> : <Waiting />)}
      {tab === "refine" && (ready("strategy") ? <RefinePanel job={job} onStarted={load} onShowCandidates={() => setTab("candidates")} /> : <Waiting />)}
      {tab === "candidates" && <CandidatesView job={job} onOpen={setOpen} onPatch={patch} reload={load} />}
      {tab === "pipeline" && <Pipeline job={job} onOpen={setOpen} onPatch={patch} />}
      {tab === "activity" && <ActivityView job={job} />}

      {openC && <CandidateDrawer c={openC} template={job.strategy?.outreach_template} onClose={() => setOpen(null)} onPatch={(p) => patch(openC.id, p)} />}
    </div>
  );
}

function Waiting() {
  return <Empty icon={<Loader2 className="h-5 w-5 animate-spin" />} title="Your AI recruiter is working on this">This section will appear as soon as the step completes.</Empty>;
}

function Progress({ job }: { job: Job }) {
  const last = job.log[job.log.length - 1]?.msg;
  return (
    <div className={clsx("card p-5", job.status === "error" && "border-rose-200")}>
      <div className="flex items-center gap-2 mb-4">
        {job.status === "error" ? <XCircle className="h-5 w-5 text-rose-500" /> : <Loader2 className="h-5 w-5 animate-spin text-brand-600" />}
        <div className="font-medium text-slate-900">{job.status === "error" ? "The agent hit a problem" : "Sourcing agent in progress"}</div>
        <div className="text-sm text-slate-500 truncate">— {job.status === "error" ? job.error : last}</div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {job.steps.map((s, i) => (
          <div key={s.key} className="flex items-start gap-2">
            {s.status === "done" ? <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" /> : s.status === "running" ? <Loader2 className="h-5 w-5 animate-spin text-brand-600 shrink-0" /> : s.status === "error" ? <XCircle className="h-5 w-5 text-rose-500 shrink-0" /> : <CircleDashed className="h-5 w-5 text-slate-300 shrink-0" />}
            <div className="text-xs"><div className="text-slate-400">Step {i + 1}</div><div className={clsx("font-medium", s.status === "pending" ? "text-slate-400" : "text-slate-800")}>{s.label}</div></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Overview({ job }: { job: Job }) {
  const { role, recruiter_brief: b } = job;
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Card title="Executive recruiter summary" icon={<MessageSquareQuote className="h-4 w-4 text-brand-600" />}>
          <p className="text-[15px] leading-relaxed text-slate-700">{b.executive_summary}</p>
          <div className="mt-4 rounded-lg bg-brand-50/60 border border-brand-100 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-700 mb-1">Ideal candidate persona</div>
            <p className="text-sm text-slate-700">{b.ideal_candidate_persona}</p>
          </div>
        </Card>
        <div className="grid md:grid-cols-2 gap-6">
          <Card title="Must-have skills"><div className="flex flex-wrap gap-1.5">{role.must_have_skills?.map((s) => <Badge key={s} tone="blue">{s}</Badge>)}</div>
            <div className="section-title mt-5 mb-2">Nice to have</div><div className="flex flex-wrap gap-1.5">{role.nice_to_have_skills?.map((s) => <Badge key={s}>{s}</Badge>)}</div>
          </Card>
          <Card title="Evaluation scorecard">
            <div className="space-y-3">{b.evaluation_criteria?.map((e) => (
              <div key={e.criterion}><div className="flex justify-between text-sm"><span className="text-slate-700">{e.criterion}</span><span className="font-medium">{e.weight}%</span></div>
                <div className="h-1.5 bg-slate-100 rounded-full mt-1"><div className="h-full bg-brand-500 rounded-full" style={{ width: `${e.weight}%` }} /></div></div>
            ))}</div>
          </Card>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <Card title="Key responsibilities"><List items={role.responsibilities} icon={<ArrowRight className="h-3.5 w-3.5" />} /></Card>
          <Card title="Intake questions for hiring manager" icon={<Lightbulb className="h-4 w-4 text-amber-500" />}><List items={b.intake_questions} icon="?" /></Card>
        </div>
      </div>
      <div className="space-y-6">
        <Card title="Role snapshot">
          <dl className="space-y-3 text-sm">
            {[["Function", role.function], ["Experience", role.years_experience], ["Education", role.education], ["Comp. estimate", role.compensation_hint], ["Source", job.source.label]].map(([k, v]) => v ? (
              <div key={k} className="flex justify-between gap-4"><dt className="text-slate-500 shrink-0">{k}</dt><dd className="text-slate-800 text-right break-all">{v}</dd></div>
            ) : null)}
          </dl>
          {role.summary && <p className="text-sm text-slate-600 mt-4 pt-4 border-t border-slate-100">{role.summary}</p>}
        </Card>
        <Card title="Selling points" icon={<Flame className="h-4 w-4 text-orange-500" />}><List items={b.selling_points} icon={<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />} /></Card>
        <Card title="Red flags to screen for" icon={<AlertTriangle className="h-4 w-4 text-rose-500" />}><List items={b.red_flags} icon={<span className="text-rose-500">!</span>} /></Card>
      </div>
    </div>
  );
}

function TalentMapView({ job }: { job: Job }) {
  const t = job.talent_map;
  const tiers = ["Primary", "Secondary", "Adjacent"];
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <Metric label="Talent pool" value={t.talent_pool_estimate} />
        <Metric label="Competition for talent" value={t.competition_level} tone={t.competition_level === "High" ? "text-rose-600" : "text-amber-600"} />
        <Metric label="Target companies" value={String(t.target_companies?.length ?? 0)} />
      </div>
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2" title={`Hiring firm: ${t.hiring_company_profile?.name}`} icon={<Building2 className="h-4 w-4 text-brand-600" />}>
          <p className="text-sm text-slate-600">{t.hiring_company_profile?.description}</p>
          {!!t.hiring_company_profile?.direct_competitors?.length && (
            <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
              {t.hiring_company_profile.market_segment && <span className="chip bg-brand-50 text-brand-700 font-medium">{t.hiring_company_profile.market_segment}</span>}
              <span className="text-slate-500">Top competitors:</span>
              {t.hiring_company_profile.direct_competitors.map((c) => <span key={c} className="chip bg-slate-100 text-slate-700">{c}</span>)}
            </div>
          )}
          <div className="grid md:grid-cols-2 gap-6 mt-5">
            <div><div className="section-title mb-2">Current team patterns</div><List items={t.hiring_company_profile?.current_team_patterns} /></div>
            <div><div className="section-title mb-2">Culture signals</div><div className="flex flex-wrap gap-1.5">{t.hiring_company_profile?.culture_signals?.map((s) => <Badge key={s} tone="violet">{s}</Badge>)}</div>
              {t.github_footprint && (
                <div className="mt-5">
                  <div className="section-title mb-2 flex items-center gap-2"><GithubIcon />Engineering footprint <a href={t.github_footprint.url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 font-normal">@{t.github_footprint.org}</a></div>
                  <div className="space-y-1.5">{t.github_footprint.languages.slice(0, 6).map(([l, n]) => {
                    const max = t.github_footprint!.languages[0][1];
                    return <div key={l} className="flex items-center gap-2 text-xs"><span className="w-20 text-slate-600">{l}</span><div className="flex-1 h-1.5 bg-slate-100 rounded-full"><div className="h-full bg-slate-700 rounded-full" style={{ width: `${(n / max) * 100}%` }} /></div><span className="text-slate-400 w-5">{n}</span></div>;
                  })}</div>
                </div>
              )}
            </div>
          </div>
          {t.team_benchmark?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-slate-100">
              <div className="section-title mb-2">Benchmark profiles currently at {t.hiring_company_profile?.name}</div>
              <div className="flex flex-wrap gap-2">{t.team_benchmark.map((b) => <a key={b.url} href={b.url} target="_blank" rel="noreferrer" className="chip bg-slate-100 text-slate-700 hover:bg-slate-200"><LinkedinIcon className="h-3 w-3 text-[#0a66c2]" />{b.name}{b.headline && <span className="text-slate-400">· {b.headline.slice(0, 40)}</span>}</a>)}</div>
            </div>
          )}
        </Card>
        <Card title="Common attributes of top performers">
          <div className="space-y-3">{t.common_attributes?.map((a) => (
            <div key={a.attribute}><div className="flex justify-between text-sm gap-2"><span className="text-slate-700">{a.attribute}</span><span className="text-slate-500">{a.prevalence}%</span></div>
              <div className="h-1.5 bg-slate-100 rounded-full mt-1"><div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500" style={{ width: `${a.prevalence}%` }} /></div></div>
          ))}</div>
        </Card>
      </div>

      <Card title="Target company map" icon={<Target className="h-4 w-4 text-brand-600" />}>
        <div className="grid md:grid-cols-3 gap-5">
          {tiers.map((tier) => (
            <div key={tier}>
              <div className="flex items-center gap-2 mb-3"><Badge tone={tierTone[tier]}>{tier}</Badge><span className="text-xs text-slate-500">{tier === "Primary" ? "Direct competitors" : tier === "Secondary" ? "Comparable talent" : "Adjacent pools"}</span></div>
              <div className="space-y-2">{t.target_companies?.filter((c) => c.tier === tier).map((c) => (
                <div key={c.name} className="rounded-lg border border-slate-200 p-3 hover:border-brand-300 transition">
                  <div className="flex items-center gap-2"><Avatar name={c.name} size={26} /><span className="font-medium text-sm text-slate-900">{c.name}</span>{c.est_talent_pool && <span className="ml-auto text-[11px] text-slate-400">{c.est_talent_pool}</span>}</div>
                  <div className="text-xs text-slate-500 mt-1.5">{c.rationale}</div>
                </div>
              ))}</div>
            </div>
          ))}
        </div>
        {t.hiring_company_profile?.competitor_basis && <p className="text-xs text-slate-400 mt-4">Direct competitors: {t.hiring_company_profile.competitor_basis}</p>}
      </Card>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card title="Market trends" icon={<TrendingUp className="h-4 w-4 text-emerald-600" />} className="lg:col-span-2">
          <div className="grid md:grid-cols-2 gap-3">{t.market_trends?.map((m) => (
            <div key={m.trend} className="rounded-lg bg-slate-50 p-3.5"><div className="text-sm font-medium text-slate-900">{m.trend}</div><div className="text-xs text-slate-600 mt-1"><span className="text-brand-600 font-medium">So what: </span>{m.implication}</div></div>
          ))}</div>
        </Card>
        <div className="space-y-6">
          <Card title="Peer titles"><div className="flex flex-wrap gap-1.5">{t.peer_titles?.map((p) => <Badge key={p} tone="blue">{p}</Badge>)}</div></Card>
          <Card title="Talent hubs" icon={<MapPin className="h-4 w-4 text-rose-500" />}><div className="space-y-2">{t.talent_hubs?.map((h) => <div key={h.location} className="text-sm"><span className="font-medium">{h.location}</span><span className="text-slate-500"> — {h.rationale}</span></div>)}</div></Card>
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Typical career paths"><List items={t.career_paths} icon={<ArrowRight className="h-3.5 w-3.5" />} /></Card>
        <Card title="Diversity & slate notes"><p className="text-sm text-slate-600">{t.diversity_notes}</p></Card>
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "text-slate-900" }: { label: string; value: string; tone?: string }) {
  return <div className="card p-5"><div className="text-sm text-slate-500">{label}</div><div className={`text-xl font-semibold mt-1 ${tone}`}>{value || "—"}</div></div>;
}

function StrategyView({ job }: { job: Job }) {
  const s = job.strategy;
  const prio: Record<string, string> = { High: "green", Medium: "amber", Low: "slate" };
  return (
    <div className="space-y-6">
      <Card title="Skills matrix">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-100"><th className="py-2 pr-4">Skill</th><th className="py-2 pr-4">Category</th><th className="py-2 pr-4">Importance</th><th className="py-2">How to verify</th></tr></thead>
            <tbody className="divide-y divide-slate-100">{s.skills_matrix?.map((r) => (
              <tr key={r.skill}><td className="py-2.5 pr-4 font-medium text-slate-900">{r.skill}</td><td className="py-2.5 pr-4 text-slate-600">{r.category}</td>
                <td className="py-2.5 pr-4"><Badge tone={r.importance === "Must-have" ? "blue" : "slate"}>{r.importance}</Badge></td><td className="py-2.5 text-slate-600">{r.signal}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </Card>

      <Card title="Boolean & X-ray search strings" icon={<Search className="h-4 w-4 text-brand-600" />} action={s.linkedin_search_link && <a href={s.linkedin_search_link} target="_blank" rel="noreferrer" className="btn-secondary !py-1.5 text-xs"><LinkedinIcon className="h-3.5 w-3.5 text-[#0a66c2]" />Open LinkedIn search</a>}>
        <div className="space-y-4">
          {([["LinkedIn Recruiter", s.boolean_strings?.linkedin, <LinkedinIcon key="l" className="h-4 w-4 text-[#0a66c2]" />], ["Google X-ray", s.boolean_strings?.google_xray, <Search key="g" className="h-4 w-4" />], ["GitHub", s.boolean_strings?.github, <GithubIcon key="h" />]] as const).map(([label, q, icon]) => q ? (
            <div key={label}>
              <div className="flex items-center justify-between mb-1.5"><div className="text-sm font-medium flex items-center gap-2">{icon}{label}</div><CopyButton text={q} label="Copy" /></div>
              <code className="block rounded-lg bg-ink-900 text-slate-100 p-3 text-xs leading-relaxed break-words">{q}</code>
            </div>
          ) : null)}
          {s.manual_search_links?.length > 0 && (
            <div className="pt-2">
              <div className="text-sm font-medium mb-2">One-click X-ray searches</div>
              <div className="space-y-2">{s.manual_search_links.map((m) => (
                <div key={m.query} className="flex items-center gap-3 rounded-lg border border-slate-200 p-2.5">
                  <code className="flex-1 text-xs text-slate-600 truncate">{m.query}</code>
                  <a href={m.google} target="_blank" rel="noreferrer" className="btn-secondary !py-1 text-xs">Google<ExternalLink className="h-3 w-3" /></a>
                  <a href={m.bing} target="_blank" rel="noreferrer" className="btn-ghost !py-1 text-xs">Bing</a>
                </div>
              ))}</div>
            </div>
          )}
        </div>
      </Card>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card title="Channel plan">
          <div className="space-y-3">{s.channels?.map((c) => (
            <div key={c.channel} className="flex gap-3"><Badge tone={prio[c.priority] ?? "slate"} className="h-fit mt-0.5">{c.priority}</Badge><div><div className="text-sm font-medium text-slate-900">{c.channel}</div><div className="text-xs text-slate-600">{c.tactic}</div></div></div>
          ))}</div>
        </Card>
        <Card title="Search timeline">
          <ol className="relative border-l border-slate-200 ml-2 space-y-4">{s.timeline?.map((t) => (
            <li key={t.week} className="ml-4"><div className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full bg-brand-500 ring-4 ring-brand-50" /><div className="text-sm font-medium">{t.week}</div><div className="text-xs text-slate-600">{t.focus}</div></li>
          ))}</ol>
        </Card>
      </div>
      <Card title="Outreach template" action={<CopyButton text={s.outreach_template} label="Copy" />}>
        <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans">{s.outreach_template}</pre>
      </Card>
    </div>
  );
}

function CandidatesView({ job, onOpen, onPatch, reload }: { job: Job; onOpen: (id: string) => void; onPatch: (id: string, p: Partial<Candidate>) => void; reload: () => void }) {
  const [q, setQ] = useState("");
  const [src, setSrc] = useState("All");
  const [stage, setStage] = useState("All");
  const [adding, setAdding] = useState(false);
  const latest = job.refinement?.rounds.length || 0;
  const sources = ["All", ...Array.from(new Set(job.candidates.map((c) => c.source)))];
  const list = useMemo(() => job.candidates.filter((c) =>
    (src === "All" || c.source === src) && (stage === "All" || c.stage === stage) &&
    (!q || `${c.name} ${c.headline} ${c.company} ${c.location} ${c.skills.join(" ")}`.toLowerCase().includes(q.toLowerCase()))), [job.candidates, q, src, stage]);

  if (!job.candidates.length && job.status === "running") return <Waiting />;
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 px-5 py-3.5 border-b border-slate-100">
        <div className="relative"><Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input className="input pl-9 !w-64 !py-1.5" placeholder="Filter by name, skill, company…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <select className="input !w-auto !py-1.5" value={src} onChange={(e) => setSrc(e.target.value)}>{sources.map((s) => <option key={s}>{s}</option>)}</select>
        <select className="input !w-auto !py-1.5" value={stage} onChange={(e) => setStage(e.target.value)}>{["All", ...STAGES].map((s) => <option key={s}>{s}</option>)}</select>
        <span className="text-sm text-slate-500">{list.length} of {job.candidates.length}</span>
        <button className="btn-secondary !py-1.5 ml-auto" onClick={() => setAdding(true)}><Plus className="h-4 w-4" />Add candidate</button>
      </div>
      {adding && <AddCandidate jobId={job.id} onDone={() => { setAdding(false); reload(); }} />}
      {list.length === 0 ? (
        <Empty icon={<Users className="h-5 w-5" />} title="No candidates match">Try changing filters, re-sourcing, or use the X-ray links in the Strategy tab and add candidates manually.</Empty>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="px-5 py-2.5">Candidate</th><th className="px-3 py-2.5">Match</th><th className="px-3 py-2.5 hidden lg:table-cell">Matched skills</th><th className="px-3 py-2.5">Source</th><th className="px-3 py-2.5">Stage</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {list.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 cursor-pointer" onClick={() => onOpen(c.id)}>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={c.name} src={c.avatar} />
                      <div className="min-w-0">
                        <div className="font-medium text-slate-900 flex items-center gap-1">{c.name}<ProfileLink c={c} />{latest > 0 && c.round === latest && <Badge tone="green">New</Badge>}</div>
                        <div className="text-xs text-slate-500 truncate max-w-xs">{c.headline || c.company || "—"}</div>
                        <div className="text-xs text-slate-400 flex gap-3">{c.company && <span>{c.company}</span>}{c.location && <span>{c.location}</span>}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3"><ScoreRing score={c.score} size={40} /></td>
                  <td className="px-3 py-3 hidden lg:table-cell"><div className="flex flex-wrap gap-1 max-w-xs">{c.skills.slice(0, 4).map((s) => <Badge key={s} tone="blue">{s}</Badge>)}{c.skills.length > 4 && <span className="text-xs text-slate-400">+{c.skills.length - 4}</span>}</div></td>
                  <td className="px-3 py-3"><Badge><SourceIcon source={c.source} />{c.source}</Badge></td>
                  <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                    <select className={clsx("chip border-0 cursor-pointer pr-6", stageSelect[c.stage])} value={c.stage} onChange={(e) => onPatch(c.id, { stage: e.target.value })}>
                      {STAGES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const stageSelect: Record<string, string> = {
  Sourced: "bg-slate-100 text-slate-700", Shortlisted: "bg-brand-50 text-brand-700", Contacted: "bg-violet-50 text-violet-700",
  Interviewing: "bg-amber-50 text-amber-700", Offer: "bg-cyan-50 text-cyan-700", Hired: "bg-emerald-50 text-emerald-700", Rejected: "bg-rose-50 text-rose-700",
};

function AddCandidate({ jobId, onDone }: { jobId: string; onDone: () => void }) {
  const [f, setF] = useState({ name: "", url: "", headline: "", company: "", location: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="px-5 py-4 bg-brand-50/40 border-b border-slate-100 grid md:grid-cols-6 gap-2">
      <input className="input" placeholder="Full name*" value={f.name} onChange={set("name")} />
      <input className="input md:col-span-2" placeholder="LinkedIn / GitHub / profile URL" value={f.url} onChange={set("url")} />
      <input className="input" placeholder="Headline / title" value={f.headline} onChange={set("headline")} />
      <input className="input" placeholder="Company" value={f.company} onChange={set("company")} />
      <div className="flex gap-2"><input className="input" placeholder="Location" value={f.location} onChange={set("location")} />
        <button className="btn-primary" disabled={!f.name} onClick={async () => { await api.addCandidate(jobId, f); onDone(); }}>Add</button></div>
    </div>
  );
}

function Pipeline({ job, onOpen, onPatch }: { job: Job; onOpen: (id: string) => void; onPatch: (id: string, p: Partial<Candidate>) => void }) {
  const [drag, setDrag] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const colors: Record<string, string> = { Sourced: "bg-slate-400", Shortlisted: "bg-brand-500", Contacted: "bg-violet-500", Interviewing: "bg-amber-500", Offer: "bg-cyan-500", Hired: "bg-emerald-500", Rejected: "bg-rose-400" };
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {STAGES.map((s) => {
        const items = job.candidates.filter((c) => c.stage === s);
        return (
          <div key={s} onDragOver={(e) => { e.preventDefault(); setOver(s); }} onDragLeave={() => setOver(null)}
            onDrop={() => { if (drag) onPatch(drag, { stage: s }); setDrag(null); setOver(null); }}
            className={clsx("w-72 shrink-0 rounded-xl bg-slate-100/80 p-3 transition", over === s && "ring-2 ring-brand-300 bg-brand-50")}>
            <div className="flex items-center gap-2 px-1 mb-3"><span className={`h-2 w-2 rounded-full ${colors[s]}`} /><span className="text-sm font-semibold text-slate-800">{s}</span><span className="text-xs text-slate-500 ml-auto">{items.length}</span></div>
            <div className="space-y-2 min-h-[120px]">
              {items.map((c) => (
                <div key={c.id} draggable onDragStart={() => setDrag(c.id)} onClick={() => onOpen(c.id)}
                  className="bg-white rounded-lg border border-slate-200 p-3 shadow-card cursor-grab active:cursor-grabbing hover:border-brand-300">
                  <div className="flex items-center gap-2.5">
                    <Avatar name={c.name} src={c.avatar} size={30} />
                    <div className="min-w-0 flex-1"><div className="text-sm font-medium truncate">{c.name}</div><div className="text-xs text-slate-500 truncate">{c.company || c.headline}</div></div>
                    <ProfileLink c={c} /><span className={clsx("text-xs font-semibold", c.score >= 70 ? "text-emerald-600" : c.score >= 45 ? "text-amber-600" : "text-slate-400")}>{c.score}</span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-2"><SourceIcon source={c.source} />{c.skills.slice(0, 2).map((k) => <Badge key={k} className="!text-[10px]">{k}</Badge>)}</div>
                </div>
              ))}
              {items.length === 0 && <div className="text-xs text-slate-400 text-center py-6 border-2 border-dashed border-slate-200 rounded-lg">Drop candidates here</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActivityView({ job }: { job: Job }) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <Card title="Agent activity log" className="lg:col-span-2">
        <ol className="space-y-3">{job.log.map((l, i) => (
          <li key={i} className="flex gap-3 text-sm"><span className="text-xs text-slate-400 w-20 shrink-0 pt-0.5">{new Date(l.t).toLocaleTimeString()}</span><span className="text-slate-700">{l.msg}</span></li>
        ))}</ol>
      </Card>
      <Card title="Source job description" icon={<LayoutList className="h-4 w-4" />}>
        <pre className="whitespace-pre-wrap text-xs text-slate-600 font-sans max-h-[600px] overflow-y-auto">{job.jd_text}</pre>
      </Card>
    </div>
  );
}
