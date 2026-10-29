import { History, Loader2, Plus, Sparkles, ThumbsDown, ThumbsUp, Wand2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Adjustments, Job, RefinePreview, RefineSignals } from "../types";
import { Badge, Card, timeAgo } from "./ui";

type ListKey = "include_companies" | "exclude_companies" | "add_skills" | "remove_skills" | "add_titles" | "remove_titles";
const EMPTY: Adjustments = { include_companies: [], exclude_companies: [], add_skills: [], remove_skills: [], add_titles: [], remove_titles: [], add_nice: [], location: "", seniority: "" };
const FIELDS: { key: ListKey; label: string; tone: string; placeholder: string }[] = [
  { key: "include_companies", label: "Prioritise companies", tone: "blue", placeholder: "Add company…" },
  { key: "exclude_companies", label: "Exclude companies", tone: "red", placeholder: "Add company…" },
  { key: "add_skills", label: "Add must-have skills", tone: "green", placeholder: "Add skill…" },
  { key: "remove_skills", label: "Drop skills", tone: "amber", placeholder: "Add skill…" },
  { key: "add_titles", label: "Add job titles", tone: "violet", placeholder: "Add title…" },
  { key: "remove_titles", label: "Drop job titles", tone: "slate", placeholder: "Add title…" },
];
const EXAMPLE = "e.g. More people from Brenntag and IMCD, exclude Rio Tinto, must have SAP. Add title FP&A Manager. Only in Singapore.";

function ChipField({ label, tone, values, placeholder, suggestions, onChange }: {
  label: string; tone: string; values: string[]; placeholder: string; suggestions?: string[]; onChange: (v: string[]) => void;
}) {
  const [draft, setDraft] = useState("");
  const add = (v: string) => { const t = v.trim(); if (t && !values.some((x) => x.toLowerCase() === t.toLowerCase())) onChange([...values, t]); setDraft(""); };
  const sugg = (suggestions || []).filter((s) => !values.includes(s)).slice(0, 6);
  return (
    <div>
      <div className="text-xs font-medium text-slate-500 mb-1.5">{label}</div>
      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-slate-200 px-2 py-1.5 min-h-[38px] focus-within:border-brand-400">
        {values.map((v) => (
          <Badge key={v} tone={tone}>{v}<button aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}><X className="h-3 w-3" /></button></Badge>
        ))}
        <input className="flex-1 min-w-[110px] text-sm outline-none bg-transparent" placeholder={placeholder} value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(draft); } }} onBlur={() => draft && add(draft)} />
      </div>
      {sugg.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">{sugg.map((s) => (
          <button key={s} onClick={() => add(s)} className="chip bg-white border border-dashed border-slate-300 text-slate-500 hover:text-slate-800"><Plus className="h-3 w-3" />{s}</button>
        ))}</div>
      )}
    </div>
  );
}

export default function RefinePanel({ job, onStarted, onShowCandidates }: { job: Job; onStarted: () => void; onShowCandidates: () => void }) {
  const [feedback, setFeedback] = useState("");
  const [adj, setAdj] = useState<Adjustments>(EMPTY);
  const [interpreted, setInterpreted] = useState("");
  const [parsedBy, setParsedBy] = useState("");
  const [useSignals, setUseSignals] = useState(true);
  const [signals, setSignals] = useState<RefineSignals | null>(null);
  const [busy, setBusy] = useState<"" | "interpret" | "apply">("");
  const [err, setErr] = useState("");
  const running = job.status === "running";
  const rounds = [...(job.refinement?.rounds || [])].reverse();
  const role = job.role, tmap = job.talent_map;

  const [plan, setPlan] = useState<RefinePreview | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      api.refinePreview(job.id, { adjustments: adj, use_signals: useSignals }).then((r) => { setSignals(r.signals); setPlan(r); }).catch(() => undefined);
    }, 400);
    return () => clearTimeout(t);
  }, [job.id, job.candidates, adj, useSignals]);

  const merge = (a: Adjustments) => setAdj((cur) => {
    const out = { ...cur };
    FIELDS.forEach(({ key }) => { out[key] = Array.from(new Set([...cur[key], ...a[key]])); });
    out.add_nice = Array.from(new Set([...cur.add_nice, ...a.add_nice]));
    out.location = a.location || cur.location;
    out.seniority = a.seniority || cur.seniority;
    return out;
  });

  const interpret = async () => {
    setBusy("interpret"); setErr("");
    try {
      const r = await api.refinePreview(job.id, { feedback });
      merge(r.adjustments); setParsedBy(r.parsed_by); setInterpreted(feedback); setSignals(r.signals);
      return r.adjustments;
    } catch (e) { setErr((e as Error).message); return null; } finally { setBusy(""); }
  };

  const apply = async () => {
    setBusy("apply"); setErr("");
    try {
      let final = adj;
      if (feedback.trim() && feedback !== interpreted) {
        const r = await api.refinePreview(job.id, { feedback });
        final = { ...adj };
        FIELDS.forEach(({ key }) => { final[key] = Array.from(new Set([...adj[key], ...r.adjustments[key]])); });
        final.add_nice = Array.from(new Set([...adj.add_nice, ...r.adjustments.add_nice]));
        final.location = r.adjustments.location || adj.location;
        final.seniority = r.adjustments.seniority || adj.seniority;
      }
      await api.refine(job.id, { feedback, adjustments: final, use_signals: useSignals });
      setFeedback(""); setInterpreted(""); setAdj(EMPTY); setParsedBy("");
      onStarted();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  };

  const hasChanges = FIELDS.some(({ key }) => adj[key].length) || adj.add_nice.length > 0 || !!adj.location || !!adj.seniority || !!feedback.trim();
  const canSignal = !!signals && signals.liked + signals.rejected > 0;

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Card title="Give the agent feedback" icon={<Wand2 className="h-4 w-4 text-brand-600" />}>
          <div className="space-y-4">
            <div>
              <textarea className="input min-h-[96px]" placeholder={EXAMPLE} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <button className="btn-secondary !py-1.5" disabled={!feedback.trim() || !!busy} onClick={interpret}>
                  {busy === "interpret" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}Interpret feedback
                </button>
                {parsedBy && parsedBy !== "none" && <span className="text-xs text-slate-500">Understood by {parsedBy === "ai" ? "AI" : "built-in rules"} — review and edit below.</span>}
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              {FIELDS.map((f) => (
                <ChipField key={f.key} label={f.label} tone={f.tone} placeholder={f.placeholder} values={adj[f.key]} onChange={(v) => setAdj({ ...adj, [f.key]: v })}
                  suggestions={f.key === "remove_skills" ? role.must_have_skills : f.key === "remove_titles" ? tmap.peer_titles
                    : f.key === "include_companies" ? signals?.liked_companies : f.key === "add_titles" ? signals?.liked_titles.filter((t) => !tmap.peer_titles.includes(t)) : undefined} />
              ))}
              <div>
                <div className="text-xs font-medium text-slate-500 mb-1.5">Location</div>
                <input className="input" placeholder={role.location || "e.g. Singapore"} value={adj.location} onChange={(e) => setAdj({ ...adj, location: e.target.value })} />
              </div>
              <div>
                <div className="text-xs font-medium text-slate-500 mb-1.5">Seniority</div>
                <select className="input" value={adj.seniority} onChange={(e) => setAdj({ ...adj, seniority: e.target.value })}>
                  <option value="">Keep as is</option><option value="more senior">More senior</option><option value="more junior">More junior</option>
                </select>
              </div>
            </div>
            <label className={`flex items-start gap-3 rounded-lg border p-3 ${canSignal ? "border-slate-200" : "border-dashed border-slate-200 opacity-70"}`}>
              <input type="checkbox" className="mt-1" checked={useSignals && canSignal} disabled={!canSignal} onChange={(e) => setUseSignals(e.target.checked)} />
              <div className="text-sm">
                <div className="font-medium text-slate-800 flex items-center gap-3">Learn from my shortlist & rejections
                  {signals && <span className="flex items-center gap-2 text-xs font-normal text-slate-500"><ThumbsUp className="h-3.5 w-3.5 text-emerald-600" />{signals.liked}<ThumbsDown className="h-3.5 w-3.5 text-rose-500" />{signals.rejected}</span>}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {canSignal
                    ? [signals!.liked_companies.length && `prioritise ${signals!.liked_companies.join(", ")}`, signals!.liked_titles.length && `search titles like ${signals!.liked_titles.join(", ")}`,
                       signals!.avoid_companies.length && `down-weight ${signals!.avoid_companies.join(", ")}`].filter(Boolean).join(" · ") || "Uses the candidates you shortlisted, rated or rejected to steer the next round."
                    : "Shortlist, rate (4–5★) or reject candidates and the agent will calibrate the next round on them."}
                </div>
              </div>
            </label>
            {plan && (
              <div className="rounded-lg border border-slate-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium text-slate-800">Searches this round</span>
                  <span className="text-xs text-slate-500">At most {plan.cost} search credit{plan.cost === 1 ? "" : "s"} · stops early once enough relevant people are found</span>
                </div>
                <ul className="mt-2 space-y-1">{plan.plan.map((p) => (
                  <li key={p.q} className="flex gap-2 text-xs" title={p.q}>
                    <span className={`font-mono truncate ${p.cached ? "text-slate-400 line-through" : "text-slate-700"}`}>{p.q}</span>
                    {p.cached && <span className="shrink-0 text-slate-400">already run{p.kept != null ? `, ${p.kept} found` : ""}</span>}
                  </li>
                ))}</ul>
                {plan.warnings.map((w) => <div key={w} className="mt-2 text-xs text-amber-700 bg-amber-50 rounded px-2 py-1">{w}</div>)}
              </div>
            )}
            {err && <div className="text-sm text-rose-600">{err}</div>}
            <div className="flex items-center gap-3">
              <button className="btn-primary" disabled={running || !!busy || (!hasChanges && !(useSignals && canSignal))} onClick={apply}>
                {busy === "apply" || running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}{running ? "Refining…" : `Apply & re-source${plan ? ` (≤${plan.cost} searches)` : ""}`}
              </button>
              <span className="text-xs text-slate-500">Updates the strategy, searches again and adds only new people. Your pipeline is kept.</span>
            </div>
          </div>
        </Card>

        <Card title="Refinement history" icon={<History className="h-4 w-4 text-brand-600" />}>
          {rounds.length === 0 ? <div className="text-sm text-slate-500">No refinements yet. Each round you apply is logged here with what changed and what it found.</div> : (
            <ol className="space-y-4">
              {rounds.map((r) => (
                <li key={r.round} className="border-l-2 border-brand-200 pl-4">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold text-slate-900">Round {r.round}</span>
                    <span className="text-xs text-slate-400">{timeAgo(r.t)}</span>
                    <Badge tone="green">+{r.added} new</Badge>
                    {r.shortlisted_new > 0 && <Badge tone="blue">{r.shortlisted_new} shortlisted</Badge>}
                    {r.excluded > 0 && <Badge tone="red">{r.excluded} excluded</Badge>}
                    {r.added > 0 && <button className="text-xs text-brand-600 hover:underline" onClick={onShowCandidates}>View candidates</button>}
                  </div>
                  {r.feedback && <div className="mt-1 text-sm text-slate-600 italic">“{r.feedback}”</div>}
                  <ul className="mt-1.5 space-y-0.5 text-xs text-slate-500 list-disc pl-4">{(r.changes.length ? r.changes : ["No strategy changes — searched again"]).map((c) => <li key={c}>{c}</li>)}</ul>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      <Card title="Current search" icon={<Sparkles className="h-4 w-4 text-brand-600" />} className="h-fit">
        <div className="space-y-4 text-sm">
          <Section label="Must-have skills" items={role.must_have_skills} tone="green" />
          <Section label="Job titles searched" items={tmap.peer_titles} tone="violet" />
          <Section label="Target companies" items={(tmap.target_companies || []).filter((c) => c.tier === "Primary").map((c) => c.name)} tone="blue" />
          {!!job.refinement?.exclude_companies.length && <Section label="Excluded" items={job.refinement.exclude_companies} tone="red" />}
          {!!job.refinement?.avoid_companies.length && <Section label="Down-weighted" items={job.refinement.avoid_companies} tone="amber" />}
          <div><div className="text-xs font-medium text-slate-500 mb-1">Location</div><div className="text-slate-800">{role.location || "Not specified"}</div></div>
        </div>
      </Card>
    </div>
  );
}

function Section({ label, items, tone }: { label: string; items?: string[]; tone: string }) {
  return (
    <div>
      <div className="text-xs font-medium text-slate-500 mb-1">{label}</div>
      <div className="flex flex-wrap gap-1">{(items || []).slice(0, 10).map((i) => <Badge key={i} tone={tone}>{i}</Badge>)}{!items?.length && <span className="text-slate-400">—</span>}</div>
    </div>
  );
}
