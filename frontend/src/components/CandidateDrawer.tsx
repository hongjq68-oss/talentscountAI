import { Building2, ExternalLink, Mail, MapPin, Star, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useEffect, useState } from "react";
import { STAGES } from "../api";
import type { Candidate } from "../types";
import { Avatar, Badge, CopyButton, GithubIcon, LinkedinIcon, ScoreRing } from "./ui";

export function SourceIcon({ source }: { source: string }) {
  if (source === "GitHub") return <GithubIcon className="h-3.5 w-3.5" />;
  if (source === "LinkedIn") return <LinkedinIcon className="h-3.5 w-3.5 text-[#0a66c2]" />;
  return <ExternalLink className="h-3.5 w-3.5" />;
}

export function ProfileLink({ c }: { c: Candidate }) {
  if (!c.url) return null;
  return (
    <a href={c.url} target="_blank" rel="noopener noreferrer" title="Open profile in a new tab" onClick={(e) => e.stopPropagation()} onMouseDown={(e) => e.stopPropagation()}
      className="inline-flex items-center justify-center rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-brand-600 shrink-0"><SourceIcon source={c.source} /></a>
  );
}

export default function CandidateDrawer({ c, template, onClose, onPatch }: { c: Candidate; template?: string; onClose: () => void; onPatch: (p: Partial<Candidate>) => void }) {
  const [notes, setNotes] = useState(c.notes);
  useEffect(() => setNotes(c.notes), [c.id, c.notes]);
  const first = c.name.split(" ")[0];
  const outreach = (template || "").replace(/\{first_name\}/g, first).replace(/\{hook\}/g, c.outreach_hook || (c.github?.top_repos?.[0]?.name ? `${c.github.top_repos[0].name}` : c.headline || "your recent work"));

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-[1px]" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-white h-full shadow-2xl flex flex-col">
        <div className="px-6 py-5 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <Avatar name={c.name} src={c.avatar} size={56} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2"><h2 className="text-lg font-semibold text-slate-900 truncate">{c.name}</h2><Badge><SourceIcon source={c.source} />{c.source}</Badge></div>
              <div className="text-sm text-slate-600 mt-0.5 line-clamp-2">{c.headline || "—"}</div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 mt-2">
                {c.company && <span className="flex items-center gap-1"><Building2 className="h-3.5 w-3.5" />{c.company}</span>}
                {c.location && <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{c.location}</span>}
                {c.email && <a href={`mailto:${c.email}`} className="flex items-center gap-1 text-brand-600"><Mail className="h-3.5 w-3.5" />{c.email}</a>}
              </div>
            </div>
            <button onClick={onClose} className="btn-ghost !p-1.5"><X className="h-5 w-5" /></button>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-4">
            <select className="input !w-auto !py-1.5" value={c.stage} onChange={(e) => onPatch({ stage: e.target.value })}>
              {STAGES.map((s) => <option key={s}>{s}</option>)}
            </select>
            {c.url && <><a href={c.url} target="_blank" rel="noopener noreferrer" className="btn-secondary !py-1.5"><ExternalLink className="h-4 w-4" />View profile</a><CopyButton text={c.url} label="Copy link" /></>}
            <button className="btn-secondary !py-1.5" onClick={() => onPatch({ stage: "Shortlisted" })}><ThumbsUp className="h-4 w-4" />Shortlist</button>
            <button className="btn-ghost !py-1.5 text-rose-600" onClick={() => onPatch({ stage: "Rejected" })}><ThumbsDown className="h-4 w-4" />Reject</button>
            <div className="ml-auto flex">{[1, 2, 3, 4, 5].map((n) => (
              <button key={n} onClick={() => onPatch({ rating: n === c.rating ? 0 : n })}><Star className={`h-4 w-4 ${n <= c.rating ? "fill-amber-400 text-amber-400" : "text-slate-300"}`} /></button>
            ))}</div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          <section className="rounded-xl bg-gradient-to-br from-brand-50 to-white border border-brand-100 p-4">
            <div className="flex items-center gap-4">
              <ScoreRing score={c.score} size={60} />
              <div className="flex-1">
                <div className="text-sm font-semibold text-slate-900">AI match assessment</div>
                <div className="text-sm text-slate-600 mt-0.5">{c.rationale}</div>
              </div>
            </div>
            <div className="grid grid-cols-6 gap-2 mt-4">
              {Object.entries(c.breakdown || {}).map(([k, v]) => {
                const maxes: Record<string, number> = { Skills: 40, "Title/Seniority": 20, Company: 20, Location: 10, Signals: 10, Industry: 10 };
                return (
                  <div key={k}>
                    <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden"><div className="h-full bg-brand-500" style={{ width: `${(v / (maxes[k] || 20)) * 100}%` }} /></div>
                    <div className="text-[11px] text-slate-500 mt-1">{k}</div><div className="text-xs font-semibold">{v}/{maxes[k] || 20}</div>
                  </div>
                );
              })}
            </div>
          </section>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="section-title mb-2 text-emerald-700">Strengths</div>
              <ul className="space-y-1.5">{(c.strengths.length ? c.strengths : ["—"]).map((s, i) => <li key={i} className="text-sm text-slate-700 flex gap-2"><span className="text-emerald-500">+</span>{s}</li>)}</ul>
            </div>
            <div>
              <div className="section-title mb-2 text-rose-700">Gaps / risks</div>
              <ul className="space-y-1.5">{(c.concerns.length ? c.concerns : ["—"]).map((s, i) => <li key={i} className="text-sm text-slate-700 flex gap-2"><span className="text-rose-500">–</span>{s}</li>)}</ul>
            </div>
          </div>

          {c.skills.length > 0 && (
            <div><div className="section-title mb-2">Matched skills</div><div className="flex flex-wrap gap-1.5">{c.skills.map((s) => <Badge key={s} tone="blue">{s}</Badge>)}</div></div>
          )}

          {c.github && (
            <div>
              <div className="section-title mb-2 flex items-center gap-2"><GithubIcon />GitHub signals</div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <Stat label="Followers" v={c.github.followers} /><Stat label="Total stars" v={c.github.stars} /><Stat label="Public repos" v={c.github.public_repos} />
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">{c.github.top_languages.map((l) => <Badge key={l}>{l}</Badge>)}{c.github.hireable && <Badge tone="green">Open to hire</Badge>}</div>
              <div className="space-y-2">
                {c.github.top_repos.map((r) => (
                  <a key={r.url} href={r.url} target="_blank" rel="noreferrer" className="block rounded-lg border border-slate-200 p-3 hover:border-brand-300">
                    <div className="flex items-center justify-between text-sm font-medium text-brand-700">{r.name}<span className="flex items-center gap-1 text-xs text-slate-500"><Star className="h-3 w-3" />{r.stars}</span></div>
                    {r.description && <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{r.description}</div>}
                  </a>
                ))}
              </div>
            </div>
          )}

          {!c.github && c.summary && (
            <div><div className="section-title mb-2">Profile snippet</div><p className="text-sm text-slate-600 leading-relaxed">{c.summary}</p></div>
          )}

          {template && (
            <div>
              <div className="flex items-center justify-between mb-2"><div className="section-title">Personalised outreach</div><CopyButton text={outreach} label="Copy" /></div>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 border border-slate-200 p-3 text-[13px] text-slate-700 font-sans">{outreach}</pre>
            </div>
          )}

          <div>
            <div className="section-title mb-2">Recruiter notes</div>
            <textarea className="input min-h-[90px]" placeholder="Add screening notes…" value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={() => notes !== c.notes && onPatch({ notes })} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return <div className="rounded-lg bg-slate-50 p-2.5 text-center"><div className="font-semibold text-slate-900">{v.toLocaleString()}</div><div className="text-[11px] text-slate-500">{label}</div></div>;
}
