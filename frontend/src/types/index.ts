export interface CandidateProfile {
  name: string;
  email?: string;
  phone?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  summary?: string;
  skills: string[];
  soft_skills?: string[];
  education: Array<{ degree_or_institution?: string; year?: string }>;
  experience: Array<{ title?: string; bullets?: string[] }>;
  projects: Array<{ title?: string; bullets?: string[] }>;
  certifications?: string[];
  raw_sections?: Record<string, string>;
}

export interface ATSCheckDetail {
  name: string;
  passed: boolean;
  score: number;
  max_score: number;
  details: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface ATSReport {
  overall_score: number;
  category_scores: {
    section_structure_score: number;
    contact_completeness_score: number;
    content_impact_score: number;
    formatting_quality_score: number;
    skill_consistency_score: number;
    job_alignment_score?: number;
  };
  checks: ATSCheckDetail[];
  found_sections: string[];
  missing_sections: string[];
  formatting_warnings: string[];
  suggestions: string[];
  detected_skills: string[];
  evidence_items?: Array<{
    skill: string;
    evidence_found: boolean;
    source: string;
    confidence: number;
  }>;
  disclaimer: string;
}

export interface JobItem {
  id: string;
  title: string;
  employer: string;
  company?: string;
  location?: string;
  work_mode?: string;
  employment_type?: string;
  experience_min?: number;
  experience_max?: number;
  required_skills: string[];
  preferred_skills?: string[];
  description?: string;
  posted_at?: string | null;
  source_name?: string;
  source_url?: string;
  original_url?: string;
  verification_status: 'live_verified' | 'public_listing_found' | 'search_result_lead' | 'user_provided' | 'potentially_expired' | 'unavailable' | 'demo_data';
  publication_date?: string;
  retrieved_at?: string;
  is_demo_data?: boolean;
}

export interface JobSearchResponse {
  status: 'success' | 'partial_success' | 'no_results' | 'unavailable';
  query: string;
  location?: string | null;
  total_results: number;
  jobs: JobItem[];
  sources_searched: string[];
  retrieved_at: string;
  errors: string[];
}

export interface JobMatchResult {
  overall_score: number;
  skill_coverage_score: number;
  preferred_coverage_score: number;
  experience_score: number;
  role_alignment_score: number;
  location_score: number;
  skill_gaps: Array<{ skill: string; importance: string; suggestion: string }>;
  matched_skills: string[];
  recommendations: string[];
  score_breakdown: Record<string, number>;
}

export interface JobComparisonResult {
  status: 'success';
  comparison_id: string;
  saved: boolean;
  candidate: { resume_id: string | null; name: string; skills: string[] };
  job: { id: string; external_id: string; title: string; employer?: string | null; source_name: string; original_url?: string | null };
  match: JobMatchResult;
  skill_analysis: Array<{
    skill: string;
    importance: 'required' | 'preferred';
    status: 'matched' | 'partial' | 'missing';
    evidence: { section: string; text: string } | null;
  }>;
  missing_required_skills: string[];
  partial_skills: string[];
  experience_evidence: Array<{ section: string; text: string }>;
  education_evidence: Array<Record<string, unknown>>;
  certification_evidence: string[];
  scoring: {
    method: 'deterministic';
    weights: Record<string, number>;
    evaluated_categories: string[];
    not_assessed_categories: string[];
    explanation: string;
  };
  interpretation: { status: string; summary: string; provider_used: string | null };
  potential_concerns: string[];
  resume_improvements: string[];
  learning_actions: string[];
  disclaimer: string;
}

export interface CareerMilestone {
  title: string;
  description: string;
  skills_to_learn: string[];
  resources: Array<{
    name: string;
    url: string;
    resource_type: string;
    provider?: string;
    is_free: boolean;
  }>;
  estimated_weeks: number;
  order: number;
}

export interface CareerRoadmap {
  target_role: string;
  current_skills: string[];
  skill_gaps: Array<{ skill: string; current_level: string; target_level: string; priority: string }>;
  milestones: CareerMilestone[];
  estimated_total_weeks: number;
  llm_suggestions?: string;
  provider_used?: string;
}

export interface InterviewQuestion {
  id: string;
  question: string;
  category: string;
  difficulty: string;
  role: string;
  skills_tested: string[];
  sample_answer: string;
  follow_ups: string[];
}

export interface InterviewEvaluation {
  score: number;
  feedback: string;
  strengths: string[];
  areas_for_improvement: string[];
  model_answer?: string;
  llm_feedback?: string;
  provider_used?: string;
  is_fallback?: boolean;
}

export interface CareerEventItem {
  id: string;
  title: string;
  organizer: string;
  start_date: string;
  end_date?: string;
  location: string;
  venue_type: 'online' | 'in-person' | 'hybrid';
  eligibility: string;
  target_roles: string[];
  registration_deadline?: string;
  registration_url: string;
  source_url?: string;
  is_official_organizer: boolean;
  verification_status: string;
  description: string;
}

export interface AgentExecutionRecord {
  agent_name: string;
  status: string;
  started_at: string;
  completed_at: string;
  execution_time_ms: number;
  tool_calls: Array<{ tool: string; input?: any; status: string; output_summary?: string }>;
  errors: string[];
  warnings: string[];
  provider_used?: string;
}

export interface WorkflowRunRecord {
  run_id: string;
  status: string;
  elapsed_seconds: number;
  target_role: string;
  provider_used: string;
  provider_is_proprietary: boolean;
  fallback_used: boolean;
  agent_executions: AgentExecutionRecord[];
  tool_calls: any[];
  messages: Array<{ role: string; content: string }>;
  errors: string[];
  warnings: string[];
  summary: Record<string, any>;
  final_state: Record<string, any>;
}

export interface ApprovalRequestItem {
  id: string;
  action_type: string;
  title: string;
  description: string;
  payload: Record<string, any>;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  decision_comments?: string;
}
