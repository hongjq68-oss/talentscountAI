import { Briefcase, Loader2, MapPin, Plus, Sparkles, Star, Target, Trash2, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, STAGES } from "../api";
import { Badge, Empty, timeAgo } from "../components/ui";
import type { JobSummary } from "../types";

const stageBar: Record<string, string> = { Sourced: "bg-slate-300", Shortlisted: "bg-brand-500", Contacted: "bg-violet-500", Interviewing: "bg-amber-500", Offer: "bg-cyan-500", Hired: "bg-emerald-500", Rejected: "bg-rose-300" };

export default function Dashboard({ listOnly = false }: { listOnly?: boolean }) {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const navigate = useNavigate();
  const load = () => api.jobs().then(setJobs);
  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  const total = jobs?.reduce((a, j) => a + j.total, 0) ?? 0;
  const shortlisted = jobs?.reduce((a, j) => a + (j.stage_counts.Shortlisted ?? 0), 0) ?? 0;
  const pipeline = jobs?.reduce((a, j) => a + (j.stage_counts.Contacted ?? 0) + (j.stage_counts.Interviewing ?? 0) + (j.stage_counts.Offer ?? 0), 0) ?? 0;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{listOnly ? "Searches" : "Welcome back"}</h1>
          <p className="text-sm text-slate-500 mt-1">{listOnly ? "All sourcing mandates run by your AI recruiter." : "Drop in a job description and your AI executive recruiter maps the market and builds a shortlist."}</p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/new")}><Plus className="h-4 w-4" />New search</button>
      </div>

      {!listOnly && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Kpi icon={<Briefcase className="h-5 w-5" />} label="Active searches" value={jobs?.length ?? 0} tone="bg-brand-50 text-brand-600" />
          <Kpi icon={<Users className="h-5 w-5" />} label="Candidates sourced" value={total} tone="bg-violet-50 text-violet-600" />
          <Kpi icon={<Star className="h-5 w-5" />} label="Shortlisted" value={shortlisted} tone="bg-amber-50 text-amber-600" />
          <Kpi icon={<Target className="h-5 w-5" />} label="In process" value={pipeline} tone="bg-emerald-50 text-emerald-600" />
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <div className="section-title">{listOnly ? `${jobs?.length ?? 0} searches` : "Recent searches"}</div>
        </div>
        {jobs === null ? (
          <div className="p-10 flex justify-center"><Loader2 className="h-5 w-5 animate-spin text-slate-400" /></div>
        ) : jobs.length === 0 ? (
          <Empty icon={<Sparkles className="h-5 w-5" />} title="No searches yet">
            Start with a JD link, a Word/PDF/Excel file, or pasted text.
            <div className="mt-4"><button className="btn-primary" onClick={() => navigate("/new")}><Plus className="h-4 w-4" />Create your first search</button></div>
          </Empty>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobs.map((j) => (
              <div key={j.id} className="group flex flex-wrap items-center gap-4 px-5 py-4 hover:bg-slate-50/70 transition">
                <Link to={`/jobs/${j.id}`} className="flex-1 min-w-[240px]">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-900 group-hover:text-brand-700">{j.title}</span>
                    {j.status === "running" && <Badge tone="blue"><Loader2 className="h-3 w-3 animate-spin" />Agent working</Badge>}
                    {j.status === "error" && <Badge tone="red">Error</Badge>}
                  </div>
                  <div className="text-sm text-slate-500 mt-0.5 flex flex-wrap items-center gap-x-3">
                    {j.company && <span>{j.company}</span>}
                    {j.location && <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{j.location}</span>}
                    {j.seniority && <span>{j.seniority}</span>}
                    <span className="text-slate-400">· {timeAgo(j.created_at)}</span>
                  </div>
                </Link>
                <div className="w-56 hidden lg:block">
                  <div className="flex h-2 rounded-full overflow-hidden bg-slate-100">
                    {STAGES.map((s) => j.stage_counts[s] ? <div key={s} className={stageBar[s]} style={{ width: `${(j.stage_counts[s] / Math.max(1, j.total)) * 100}%` }} title={`${s}: ${j.stage_counts[s]}`} /> : null)}
                  </div>
                  <div className="text-xs text-slate-500 mt-1.5">{j.total} candidates · {j.stage_counts.Shortlisted ?? 0} shortlisted</div>
                </div>
                <div className="w-20 text-right">
                  <div className="text-xs text-slate-400">Top match</div>
                  <div className="font-semibold text-slate-900">{j.top_score || "—"}</div>
                </div>
                <button className="btn-ghost !p-2 opacity-0 group-hover:opacity-100" title="Delete" onClick={async () => { if (confirm("Delete this search?")) { await api.deleteJob(j.id); load(); } }}><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: number; tone: string }) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={`h-11 w-11 rounded-xl flex items-center justify-center ${tone}`}>{icon}</div>
      <div><div className="text-2xl font-semibold text-slate-900">{value}</div><div className="text-sm text-slate-500">{label}</div></div>
    </div>
  );
}
