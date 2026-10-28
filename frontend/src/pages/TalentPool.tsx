import { Search, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { SourceIcon } from "../components/CandidateDrawer";
import { Avatar, Badge, Empty, ScoreRing, stageTone } from "../components/ui";
import type { Candidate } from "../types";

type Row = Candidate & { jobId: string; jobTitle: string };

export default function TalentPool() {
  const [params] = useSearchParams();
  const [rows, setRows] = useState<Row[]>([]);
  const [q, setQ] = useState(params.get("q") ?? "");
  useEffect(() => setQ(params.get("q") ?? ""), [params]);
  useEffect(() => {
    (async () => {
      const jobs = await api.jobs();
      const full = await Promise.all(jobs.map((j) => api.job(j.id)));
      setRows(full.flatMap((j) => j.candidates.map((c) => ({ ...c, jobId: j.id, jobTitle: j.role?.title || "Search" }))));
    })();
  }, []);
  const list = useMemo(() => rows.filter((c) => !q || `${c.name} ${c.headline} ${c.company} ${c.location} ${c.skills.join(" ")} ${c.jobTitle}`.toLowerCase().includes(q.toLowerCase())).sort((a, b) => b.score - a.score), [rows, q]);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-semibold text-slate-900">Talent pool</h1><p className="text-sm text-slate-500 mt-1">Every candidate your agent has found, across all searches.</p></div>
      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-3">
          <div className="relative"><Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input className="input pl-9 !w-80 !py-1.5" placeholder="Search talent pool…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <span className="text-sm text-slate-500">{list.length} candidates</span>
        </div>
        {list.length === 0 ? <Empty icon={<Users className="h-5 w-5" />} title="No candidates yet">Run a search to start building your talent pool.</Empty> : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-2.5">Candidate</th><th className="px-3 py-2.5">Match</th><th className="px-3 py-2.5">Search</th><th className="px-3 py-2.5">Source</th><th className="px-3 py-2.5">Stage</th></tr></thead>
            <tbody className="divide-y divide-slate-100">{list.map((c) => (
              <tr key={c.jobId + c.id} className="hover:bg-slate-50/70">
                <td className="px-5 py-3"><a href={c.url} target="_blank" rel="noreferrer" className="flex items-center gap-3"><Avatar name={c.name} src={c.avatar} /><div><div className="font-medium text-slate-900 hover:text-brand-700">{c.name}</div><div className="text-xs text-slate-500 truncate max-w-sm">{c.headline || c.company}</div></div></a></td>
                <td className="px-3 py-3"><ScoreRing score={c.score} size={38} /></td>
                <td className="px-3 py-3"><Link to={`/jobs/${c.jobId}`} className="text-brand-700 hover:underline">{c.jobTitle}</Link></td>
                <td className="px-3 py-3"><Badge><SourceIcon source={c.source} />{c.source}</Badge></td>
                <td className="px-3 py-3"><Badge tone={stageTone[c.stage]}>{c.stage}</Badge></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
