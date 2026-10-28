import type { Candidate, Job, JobSummary, Status } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail ?? msg; } catch { /* ignore */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}
const json = (method: string, body: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const STAGES = ["Sourced", "Shortlisted", "Contacted", "Interviewing", "Offer", "Hired", "Rejected"];

export const api = {
  status: () => req<Status>("/api/status"),
  settings: () => req<Record<string, string | boolean>>("/api/settings"),
  saveSettings: (values: Record<string, string>) => req<Status>("/api/settings", json("POST", { values })),
  jobs: () => req<JobSummary[]>("/api/jobs"),
  job: (id: string) => req<Job>(`/api/jobs/${id}`),
  createJob: (fd: FormData) => req<{ id: string }>("/api/jobs", { method: "POST", body: fd }),
  deleteJob: (id: string) => req(`/api/jobs/${id}`, { method: "DELETE" }),
  patchCandidate: (id: string, cid: string, body: Partial<Candidate>) => req<Candidate>(`/api/jobs/${id}/candidates/${cid}`, json("PATCH", body)),
  addCandidate: (id: string, body: Record<string, string>) => req<Candidate>(`/api/jobs/${id}/candidates`, json("POST", body)),
  resource: (id: string) => req(`/api/jobs/${id}/resource`, { method: "POST" }),
  exportUrl: (id: string) => `/api/jobs/${id}/export.csv`,
};
