import {
  CandidateProfile,
  ATSReport,
  JobItem,
  JobSearchResponse,
  JobComparisonResult,
  JobMatchResult,
  CareerRoadmap,
  InterviewQuestion,
  InterviewEvaluation,
  CareerEventItem,
  WorkflowRunRecord,
  ApprovalRequestItem,
} from '../types';

const API_BASE = '/api';

export const api = {
  // Resumes & ATS
  async uploadResume(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/resumes/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to upload resume');
    return res.json();
  },
  async parseText(raw_text: string, job_description?: string) {
    const res = await fetch(`${API_BASE}/resumes/parse-text`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text, job_description }),
    });
    if (!res.ok) throw new Error('Failed to parse text');
    return res.json();
  },
  async getResume(resume_id: string) {
    const res = await fetch(`${API_BASE}/resumes/${resume_id}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Resume not found');
    return data;
  },
  async updateProfile(resume_id: string, profile: Partial<CandidateProfile>) {
    const res = await fetch(`${API_BASE}/resumes/${resume_id}/profile`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile),
    });
    return res.json();
  },
  async runLLMReview(resume_id: string, job_description?: string) {
    const form = new FormData();
    if (job_description) form.append('job_description', job_description);
    const res = await fetch(`${API_BASE}/resumes/${resume_id}/llm-review`, { method: 'POST', body: form });
    return res.json();
  },
  async analyzeAgainstJob(resume_id: string, job_description: string, required_skills: string[], preferred_skills: string[] = []) {
    const res = await fetch(`${API_BASE}/resumes/analyze-against-job`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_id, job_description, required_skills, preferred_skills }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to analyze resume against this job');
    return data;
  },
  async tailorApplication(payload: {
    resume_id: string;
    job_title: string;
    employer?: string;
    job_description?: string;
    required_skills?: string[];
  }) {
    const res = await fetch(`${API_BASE}/resumes/tailor-application`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to tailor application');
    return data;
  },

  // Jobs
  async searchJobs(query = 'software engineer', location?: string, sources: string[] = ['greenhouse', 'lever', 'web'], limit = 30) {
    const res = await fetch(`${API_BASE}/jobs/search`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, location, sources, limit }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to search jobs');
    return data as JobSearchResponse;
  },
  async getJob(job_id: string) { const res = await fetch(`${API_BASE}/jobs/${job_id}`); return res.json(); },
  async saveJob(job: JobItem) { const res = await fetch(`${API_BASE}/jobs/save`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ job }) }); return res.json(); },
  async getSavedJobs() { const res = await fetch(`${API_BASE}/jobs/saved/list`); return res.json(); },

  // Matching
  async calculateMatch(resume_id: string, job: JobItem) {
    const res = await fetch(`${API_BASE}/matching/calculate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_id, job }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to calculate match');
    return data as JobComparisonResult;
  },
  async getSavedMatches(resume_id: string) {
    const res = await fetch(`${API_BASE}/matching/saved/${resume_id}`);
    return res.json();
  },
  async deleteSavedMatch(match_id: string) {
    const res = await fetch(`${API_BASE}/matching/saved/${match_id}`, { method: 'DELETE' });
    return res.json();
  },

  // Career
  async generateCareerRoadmap(data: { target_role: string; current_skills?: string[]; skill_gaps?: string[] }) {
    const res = await fetch(`${API_BASE}/career/roadmap`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to generate roadmap');
    return res.json();
  },
  async getCareerProgress() { const res = await fetch(`${API_BASE}/career/progress`); return res.json(); },
  async updateCareerProgress(data: { milestone_id: string; status: string; notes?: string }) {
    const res = await fetch(`${API_BASE}/career/progress/update`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    return res.json();
  },

  // Interview
  async startInterviewSession(data: { role: string; session_type: string; count: number; skills?: string[] }) {
    const res = await fetch(`${API_BASE}/interview/session/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to start interview session');
    }
    return res.json();
  },
  async evaluateInterviewAnswer(data: any) {
    const res = await fetch(`${API_BASE}/interview/evaluate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = typeof err.detail === 'string' ? err.detail : (Array.isArray(err.detail) ? err.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ') : 'Failed to evaluate answer');
      throw new Error(msg);
    }
    return res.json();
  },
  async getInterviewRoles() { const res = await fetch(`${API_BASE}/interview/roles`); return res.json(); },

  // Events
  async getCareerEvents(params: any = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/events/discover${qs ? '?' + qs : ''}`);
    return res.json();
  },

  // Agents
  async runAgentWorkflow(data: any) {
    const res = await fetch(`${API_BASE}/agents/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    return res.json();
  },
  async getAgentRuns() { const res = await fetch(`${API_BASE}/agents/runs`); return res.json(); },
  async getAgentRun(runId: string) { const res = await fetch(`${API_BASE}/agents/runs/${runId}`); return res.json(); },

  // Memory
  async getMemory() { const res = await fetch(`${API_BASE}/memory/`); return res.json(); },
  async getPreferences() { const res = await fetch(`${API_BASE}/memory/preferences`); return res.json(); },
  async deleteMemory(id: string) { const res = await fetch(`${API_BASE}/memory/${id}`, { method: 'DELETE' }); return res.json(); },

  // Settings/Approvals
  async getProvidersStatus() { const res = await fetch(`${API_BASE}/settings/providers`); return res.json(); },
  async getComplianceInventory() { const res = await fetch(`${API_BASE}/settings/compliance-inventory`); return res.json(); },
  async getApprovals() { const res = await fetch(`${API_BASE}/settings/approvals`); return res.json(); },
  async decideApproval(request_id: string, decision: 'approve' | 'reject', comments = '') {
    const res = await fetch(`${API_BASE}/settings/approvals/${request_id}/decision`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, comments }),
    });
    return res.json();
  },

  // Demonstrations
  async getDemonstrations() { const res = await fetch(`${API_BASE}/demonstrations/`); return res.json(); },
  async runScenario(scenario: 'a' | 'b' | 'c' | 'd' | 'e' | 'f') {
    const res = await fetch(`${API_BASE}/demonstrations/scenario-${scenario}`, { method: 'POST' });
    return res.json();
  },
};
