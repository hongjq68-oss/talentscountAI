export type StepStatus = "pending" | "running" | "done" | "error";
export interface Step { key: string; label: string; status: StepStatus }
export interface GithubInfo {
  login: string; followers: number; public_repos: number; stars: number; top_languages: string[];
  top_repos: { name: string; stars: number; language: string | null; url: string; description: string }[];
  hireable: boolean; blog: string; twitter: string;
}
export interface Candidate {
  id: string; name: string; headline: string; company: string; location: string; source: string; url: string;
  avatar: string; email: string; summary: string; skills: string[]; stage: string; notes: string; rating: number;
  github: GithubInfo | null; score: number; breakdown: Record<string, number>; rationale: string;
  strengths: string[]; concerns: string[]; outreach_hook: string; round?: number; stage_manual?: boolean; excluded?: boolean;
}
export interface Role {
  title: string; company: string; location: string; seniority: string; function: string; industry: string;
  years_experience: string; summary: string; must_have_skills: string[]; target_industries?: string[]; nice_to_have_skills: string[];
  responsibilities: string[]; requirements: string[]; education: string; compensation_hint: string;
}
export interface RecruiterBrief {
  executive_summary: string; ideal_candidate_persona: string; selling_points: string[]; intake_questions: string[];
  red_flags: string[]; evaluation_criteria: { criterion: string; weight: number }[];
}
export interface TalentMap {
  hiring_company_profile: { name: string; description: string; market_segment?: string; direct_competitors?: string[]; competitor_basis?: string; culture_signals: string[]; current_team_patterns: string[] };
  target_companies: { name: string; tier: string; rationale: string; est_talent_pool?: string }[];
  peer_titles: string[]; talent_hubs: { location: string; rationale: string }[];
  market_trends: { trend: string; implication: string }[]; common_attributes: { attribute: string; prevalence: number }[];
  career_paths: string[]; talent_pool_estimate: string; competition_level: string; diversity_notes: string;
  github_footprint: { org: string; url: string; languages: [string, number][]; top_repos: { name: string; stars: number; language: string; url: string; description: string }[] } | null;
  team_benchmark: { name: string; headline: string; url: string }[];
}
export interface Strategy {
  skills_matrix: { skill: string; category: string; importance: string; signal: string }[];
  channels: { channel: string; priority: string; tactic: string }[];
  boolean_strings: { linkedin: string; google_xray: string; github: string };
  xray_queries: string[]; outreach_template: string; timeline: { week: string; focus: string }[];
  manual_search_links: { query: string; google: string; bing: string }[]; linkedin_search_link: string;
}
export interface Job {
  id: string; created_at: string; status: "running" | "complete" | "error"; mode: string; error: string;
  source: { type: string; label: string }; options: Record<string, unknown>; steps: Step[];
  log: { t: string; msg: string }[]; jd_text: string; role: Role; recruiter_brief: RecruiterBrief;
  talent_map: TalentMap; strategy: Strategy; candidates: Candidate[];
  refinement?: { exclude_companies: string[]; avoid_companies: string[]; boost_companies: string[]; rounds: RefineRound[] };
}
export interface Adjustments {
  include_companies: string[]; exclude_companies: string[]; add_skills: string[]; remove_skills: string[];
  add_titles: string[]; remove_titles: string[]; industries: string[]; add_nice: string[]; location: string; seniority: string;
}
export interface PlanItem { q: string; kind: "linkedin" | "web"; cached: boolean; kept?: number | null }
export interface RefinePreview { adjustments: Adjustments; parsed_by: string; signals: RefineSignals; changes: string[]; plan: PlanItem[]; cost: number; warnings: string[] }
export interface RefineSignals { liked: number; rejected: number; liked_companies: string[]; liked_titles: string[]; avoid_companies: string[]; weak_sources: string[] }
export interface RefineRound {
  round: number; t: string; feedback: string; parsed_by: string; changes: string[]; signals: RefineSignals | null;
  added: number; excluded: number; shortlisted_new: number;
}
export interface JobSummary {
  id: string; created_at: string; status: Job["status"]; mode: string; title: string; company: string; location: string;
  seniority: string; source: Job["source"]; stage_counts: Record<string, number>; total: number; top_score: number; steps: Step[];
}
export interface Status { llm: string | null; search: string | null; github_token: boolean; stages: string[] }
