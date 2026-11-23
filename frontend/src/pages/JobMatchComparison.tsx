import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ExternalLink,
  FileDown,
  LoaderCircle,
  Plus,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';
import { CandidateProfile, JobComparisonResult, JobItem } from '../types';

interface ResumeDetails {
  id: string;
  filename: string;
  profile_reviewed: boolean;
  profile: CandidateProfile;
}

interface SavedComparison {
  id: string;
  resume_id: string;
  job: JobItem;
  overall_score: number;
  skill_matches: JobComparisonResult['skill_analysis'];
  skill_gaps: JobComparisonResult['match']['skill_gaps'];
  score_breakdown: Record<string, number>;
  created_at: string | null;
}

const inputClass =
  'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-500';

const parseCommaList = (value: string) => value.split(',').map((item) => item.trim()).filter(Boolean);

const readRecentJobs = (): JobItem[] => {
  try {
    const value = JSON.parse(sessionStorage.getItem('careerpilot.recentJobs') || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The comparison could not be completed.';
}

function getExternalUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

export const JobMatchComparison: React.FC = () => {
  const [resumeId, setResumeId] = useState('');
  const [resume, setResume] = useState<ResumeDetails | null>(null);
  const [savedJobs, setSavedJobs] = useState<JobItem[]>([]);
  const [recentJobs] = useState<JobItem[]>(readRecentJobs);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [requiredSkills, setRequiredSkills] = useState('');
  const [preferredSkills, setPreferredSkills] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [employer, setEmployer] = useState('');
  const [jobLocation, setJobLocation] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [results, setResults] = useState<JobComparisonResult[]>([]);
  const [savedComparisons, setSavedComparisons] = useState<SavedComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [tailoringForId, setTailoringForId] = useState<string | null>(null);
  const [tailoredData, setTailoredData] = useState<{
    tailored_summary: string;
    prioritized_skills: string[];
    tailored_bullet_points: string[];
    cover_letter: string;
  } | null>(null);
  const [tailorModalOpen, setTailorModalOpen] = useState(false);

  const handleGenerateTailored = async (job: {
    id: string;
    title: string;
    employer?: string | null;
    description?: string;
    required_skills?: string[];
  }) => {
    if (!resumeId) {
      setError('Please extract a resume first in Resume Studio.');
      return;
    }
    setTailoringForId(job.id);
    setError(null);
    try {
      const res = await api.tailorApplication({
        resume_id: resumeId,
        job_title: job.title,
        employer: job.employer || undefined,
        job_description: job.description || undefined,
        required_skills: job.required_skills || [],
      });
      setTailoredData(res.tailored);
      setTailorModalOpen(true);
    } catch (e: any) {
      setError(e.message || 'Failed to generate tailored application documents');
    } finally {
      setTailoringForId(null);
    }
  };

  const availableJobs = useMemo(() => {
    const combined = [...savedJobs, ...recentJobs];
    return combined.filter((job, index) => combined.findIndex((candidate) => candidate.id === job.id) === index);
  }, [savedJobs, recentJobs]);

  const refreshComparisons = async (id: string) => {
    const response = await api.getSavedMatches(id);
    setSavedComparisons(response.comparisons ?? []);
  };

  useEffect(() => {
    const id = sessionStorage.getItem('careerpilot.resumeId') || '';
    setResumeId(id);
    const requests: Promise<unknown>[] = [
      api.getSavedJobs().then((data) => setSavedJobs(data.saved_jobs ?? [])),
    ];
    if (id) {
      requests.push(
        api.getResume(id).then((data: ResumeDetails) => setResume(data)),
        refreshComparisons(id),
      );
    }
    Promise.allSettled(requests).then((settled) => {
      const rejected = settled.find((item): item is PromiseRejectedResult => item.status === 'rejected');
      if (rejected) setError(getErrorMessage(rejected.reason));
      if (id && settled.some((item) => item.status === 'rejected')) {
        setResume((existing) => existing);
      }
      setLoading(false);
    });
  }, []);

  const addJob = (job: JobItem) => {
    setSelectedJobIds((ids) => ids.includes(job.id) ? ids.filter((id) => id !== job.id) : [...ids, job.id]);
    setError(null);
  };

  const compareJobs = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);

    if (!resumeId || !resume) {
      setError('Parse a resume in Resume Studio during this backend session before comparing jobs.');
      return;
    }
    const required = parseCommaList(requiredSkills);
    if (required.length === 0) {
      setError('Enter at least one required skill from the job description. The score will not treat missing requirements as a perfect match.');
      return;
    }

    const selectedJobs = availableJobs.filter((job) => selectedJobIds.includes(job.id));
    const jobsToCompare: JobItem[] = selectedJobs.map((job) => ({
      ...job,
      required_skills: Array.from(new Set([...(job.required_skills || []), ...required])),
      preferred_skills: Array.from(new Set([...(job.preferred_skills || []), ...parseCommaList(preferredSkills)])),
    }));

    if (jobTitle.trim() && jobDescription.trim()) {
      jobsToCompare.push({
        id: `manual:${Date.now()}`,
        title: jobTitle.trim(),
        employer: employer.trim() || 'User-provided job',
        company: employer.trim(),
        location: jobLocation.trim(),
        required_skills: required,
        preferred_skills: parseCommaList(preferredSkills),
        description: jobDescription.trim(),
        source_name: 'user_provided',
        source_url: undefined,
        original_url: undefined,
        verification_status: 'user_provided',
        is_demo_data: false,
      });
    }

    if (jobsToCompare.length === 0) {
      setError('Select a saved/recent job from the list, or enter both a job title and description.');
      return;
    }
    if (jobsToCompare.length > 5) {
      setError('Compare at most five jobs at a time.');
      return;
    }

    setComparing(true);
    const completed: JobComparisonResult[] = [];
    const failures: string[] = [];
    for (const job of jobsToCompare) {
      try {
        const result = await api.calculateMatch(resumeId, job);
        completed.push(result);
      } catch (comparisonError) {
        failures.push(`${job.title}: ${getErrorMessage(comparisonError)}`);
      }
    }
    setResults(completed);
    setComparing(false);

    if (failures.length) {
      setError(failures.join(' '));
    }
    if (completed.length) {
      setInfo(`${completed.length} comparison${completed.length === 1 ? '' : 's'} saved to the application database.`);
      try {
        await refreshComparisons(resumeId);
      } catch (refreshError) {
        setError(getErrorMessage(refreshError));
      }
    }
  };

  const removeSaved = async (id: string) => {
    setError(null);
    try {
      await api.deleteSavedMatch(id);
      setSavedComparisons((items) => items.filter((item) => item.id !== id));
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    }
  };

  const exportResults = () => {
    if (!results.length) return;
    const content = JSON.stringify(results, null, 2);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([content], { type: 'application/json' }));
    link.download = 'careerpilot-job-comparisons.json';
    link.click();
    URL.revokeObjectURL(link.href);
  };

  if (loading) {
    return <div className="p-8 text-sm text-slate-400">Loading candidate and saved comparison data…</div>;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-300">Candidate evidence · Job requirements</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Job Match Comparison</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">
          Compare a parsed resume against source-backed job descriptions or text you provide. Scores are deterministic and only include categories with enough input evidence.
        </p>
      </header>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {info && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-950/20 p-3 text-sm text-emerald-200">
          <Check className="h-4 w-4" /> {info}
        </div>
      )}

      {!resume && (
        <section className="rounded-xl border border-amber-500/25 bg-amber-950/20 p-5">
          <h2 className="font-semibold text-amber-100">A parsed resume is needed</h2>
          <p className="mt-1 text-sm leading-relaxed text-amber-100/70">
            This app currently keeps parsed resume records in the running backend's memory. Parse your resume first; after a backend restart, parse it again before comparing.
          </p>
          <Link to="/resume-studio" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500">
            Open Resume Studio <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      )}

      {resume && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-white">Candidate evidence</h2>
              <p className="mt-1 text-sm text-slate-400">{resume.profile.name || 'Name not identified'} · {resume.filename}</p>
            </div>
            <Link to="/resume-studio" className="text-xs text-indigo-300 hover:text-indigo-200">Review profile in Resume Studio</Link>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {resume.profile.skills.length
              ? resume.profile.skills.map((skill) => <span key={skill} className="rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300">{skill}</span>)
              : <span className="text-sm text-amber-300">No skills were extracted; review the profile in Resume Studio.</span>}
          </div>
          <p className="mt-3 text-xs text-slate-500">Skills originate from the parsed resume profile. Evidence snippets below let you inspect where the resume mentions each requirement.</p>
          {!resume.profile_reviewed && (
            <p role="alert" className="mt-3 rounded-lg border border-amber-500/30 bg-amber-950/30 p-3 text-xs text-amber-200">
              Review the extracted profile in Resume Studio and save it before calculating a match. This ensures extracted skills are treated as candidate-confirmed evidence.
            </p>
          )}
        </section>
      )}

      <form onSubmit={compareJobs} className="space-y-5">
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-semibold text-white">Select real job records</h2>
              <p className="mt-1 text-xs text-slate-500">Choose saved jobs or recent Job Explorer results. Add up to five.</p>
            </div>
            <Link to="/jobs" className="text-xs text-indigo-300 hover:text-indigo-200">Open Job Explorer <ArrowRight className="inline h-3.5 w-3.5" /></Link>
          </div>
          {availableJobs.length ? (
            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {availableJobs.map((job) => {
                const selected = selectedJobIds.includes(job.id);
                return (
                  <button
                    type="button"
                    key={job.id}
                    onClick={() => addJob(job)}
                    aria-pressed={selected}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                      selected ? 'border-indigo-500/50 bg-indigo-500/10' : 'border-slate-800 bg-slate-950/50 hover:border-slate-700'
                    }`}
                  >
                    <span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${selected ? 'border-indigo-400 bg-indigo-500 text-white' : 'border-slate-600'}`}>
                      {selected && <Check className="h-3 w-3" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-100">{job.title}</span>
                      <span className="mt-1 block truncate text-xs text-slate-400">{job.employer || job.company} · {job.location || 'Location not provided'} · {job.source_name || 'saved'}</span>
                      {!job.required_skills?.length && <span className="mt-1 block text-[11px] text-amber-300">No structured requirements from source; enter skills below.</span>}
                    </span>
                    {getExternalUrl(job.original_url) && <ExternalLink className="ml-auto h-3.5 w-3.5 shrink-0 text-slate-500" />}
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="mt-4 rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
              No saved or recent listings. Search real feeds in <Link className="text-indigo-300 hover:underline" to="/jobs">Job Explorer</Link>, or paste a job description below.
            </p>
          )}
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <div>
              <h2 className="font-semibold text-white">Requirements to compare</h2>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">Enter the requirements as written in the posting. This same skill list is added to each selected job and used as the comparison criteria.</p>
            </div>
            <label className="block text-xs font-medium text-slate-400">
              Required skills <span className="text-rose-300">*</span>
              <input className={`${inputClass} mt-1.5`} value={requiredSkills} onChange={(event) => setRequiredSkills(event.target.value)} placeholder="Python, SQL, REST APIs" />
            </label>
            <label className="block text-xs font-medium text-slate-400">
              Preferred skills
              <input className={`${inputClass} mt-1.5`} value={preferredSkills} onChange={(event) => setPreferredSkills(event.target.value)} placeholder="Docker, AWS" />
            </label>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <div>
              <h2 className="font-semibold text-white">Or paste a job description</h2>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">External URL retrieval is not supported. Paste the official posting content; no source or application URL will be invented.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-medium text-slate-400">Role title
                <input className={`${inputClass} mt-1.5`} value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} maxLength={500} placeholder="Backend Engineer" />
              </label>
              <label className="text-xs font-medium text-slate-400">Employer (optional)
                <input className={`${inputClass} mt-1.5`} value={employer} onChange={(event) => setEmployer(event.target.value)} maxLength={500} placeholder="Company name" />
              </label>
            </div>
            <label className="block text-xs font-medium text-slate-400">Location (optional)
              <input className={`${inputClass} mt-1.5`} value={jobLocation} onChange={(event) => setJobLocation(event.target.value)} placeholder="Remote or city" />
            </label>
            <label className="block text-xs font-medium text-slate-400">Job description
              <textarea className={`${inputClass} mt-1.5 min-h-28 resize-y`} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} maxLength={20000} placeholder="Paste the job responsibilities and requirements…" />
            </label>
          </div>
        </section>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-2xl text-xs leading-relaxed text-slate-500">Candidate data remains in the local application for this deterministic comparison; no resume information is sent to Gemini or Grok.</p>
          <button
            type="submit"
            disabled={comparing || !resume || !resume.profile_reviewed}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {comparing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            {comparing ? 'Comparing…' : 'Compare and save'}
          </button>
        </div>
      </form>

      {results.length > 0 && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">Comparison results</h2>
              <p className="mt-1 text-xs text-slate-500">The score is deterministic. Semantic interpretation is not enabled in this comparison.</p>
            </div>
            <button onClick={exportResults} type="button" className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800">
              <FileDown className="h-4 w-4" /> Export JSON
            </button>
          </div>

          {results.length > 1 && (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
                  <tr><th className="px-4 py-3">Role</th><th className="px-4 py-3">Employer</th><th className="px-4 py-3">Deterministic score</th><th className="px-4 py-3">Required skills matched</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {results.map((result) => (
                    <tr key={result.comparison_id} className="bg-slate-950/40">
                      <td className="px-4 py-3 font-medium text-slate-200">{result.job.title}</td>
                      <td className="px-4 py-3 text-slate-400">{result.job.employer || 'Not provided'}</td>
                      <td className="px-4 py-3 font-semibold text-white">{result.match.overall_score.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-slate-400">{result.match.skill_coverage_score.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="grid gap-4 xl:grid-cols-2">
            {results.map((result) => (
              <article key={result.comparison_id} className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-white">{result.job.title}</h3>
                    <p className="mt-1 text-sm text-slate-400">{result.job.employer || 'Employer not provided'}</p>
                    {result.job.original_url && getExternalUrl(result.job.original_url) && (
                      <a href={getExternalUrl(result.job.original_url) || undefined} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-300 hover:underline">
                        Open original posting <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-4 py-3 text-right">
                    <p className="text-[10px] uppercase tracking-wide text-indigo-200/70">Match</p>
                    <p className="text-2xl font-bold text-white">{result.match.overall_score.toFixed(1)}<span className="text-sm text-slate-400">%</span></p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleGenerateTailored(result.job)}
                    disabled={tailoringForId === result.job.id}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all"
                  >
                    {tailoringForId === result.job.id ? (
                      <LoaderCircle className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileDown className="w-3.5 h-3.5" />
                    )}
                    <span>Generate Tailored Resume & Cover Letter</span>
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {Object.entries(result.match.score_breakdown).map(([category, points]) => (
                    <div key={category} className="rounded-lg bg-slate-950/70 p-3">
                      <p className="text-[11px] capitalize text-slate-500">{category.replace(/_/g, ' ')}</p>
                      <p className="mt-1 text-sm font-semibold text-slate-200">{points.toFixed(1)} weighted points</p>
                    </div>
                  ))}
                </div>
                {result.scoring.not_assessed_categories.length > 0 && (
                  <p className="text-xs text-slate-500">Not assessed due to missing job/profile information: {result.scoring.not_assessed_categories.map((name) => name.replace(/_/g, ' ')).join(', ')}.</p>
                )}

                <div>
                  <h4 className="mb-2 text-sm font-semibold text-slate-200">Requirement evidence</h4>
                  {result.skill_analysis.length ? (
                    <div className="overflow-x-auto rounded-lg border border-slate-800">
                      <table className="min-w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-500"><tr><th className="px-3 py-2">Skill</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Resume evidence</th></tr></thead>
                        <tbody className="divide-y divide-slate-800">
                          {result.skill_analysis.map((item) => (
                            <tr key={`${item.importance}-${item.skill}`}>
                              <td className="px-3 py-2 font-medium text-slate-200">{item.skill}</td>
                              <td className="px-3 py-2 capitalize text-slate-400">{item.importance}</td>
                              <td className={`px-3 py-2 capitalize ${item.status === 'matched' ? 'text-emerald-300' : item.status === 'partial' ? 'text-amber-300' : 'text-rose-300'}`}>{item.status}</td>
                              <td className="max-w-[260px] px-3 py-2 text-slate-400">{item.evidence ? `${item.evidence.section}: ${item.evidence.text}` : 'No supporting text found'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : <p className="text-xs text-slate-500">No skill requirements were provided.</p>}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">Relevant experience and projects</h4>
                    {result.experience_evidence.length ? (
                      <ul className="mt-2 space-y-2 text-xs leading-relaxed text-slate-400">
                        {result.experience_evidence.slice(0, 4).map((item, index) => <li key={`${item.section}-${index}`}><span className="text-slate-500">{item.section}:</span> {item.text}</li>)}
                      </ul>
                    ) : <p className="mt-2 text-xs text-slate-500">No experience/project evidence was extracted.</p>}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">Education and certifications</h4>
                    <p className="mt-2 text-xs text-slate-400">{result.education_evidence.length ? result.education_evidence.map((entry) => Object.values(entry).filter(Boolean).join(' · ')).join('; ') : 'No education evidence extracted.'}</p>
                    <p className="mt-2 text-xs text-slate-400">{result.certification_evidence.length ? result.certification_evidence.join(', ') : 'No certifications extracted.'}</p>
                    <p className="mt-2 text-[11px] text-slate-500">Employer education/certification requirements were not separately provided; alignment is not assessed.</p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  {[
                    ['Potential concerns', result.potential_concerns],
                    ['Resume improvements', result.resume_improvements],
                    ['Learning actions', result.learning_actions],
                  ].map(([heading, items]) => (
                    <div key={heading as string}>
                      <h4 className="text-xs font-semibold text-slate-300">{heading}</h4>
                      {(items as string[]).length ? (
                        <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-slate-400">
                          {(items as string[]).map((item) => <li key={item}>• {item}</li>)}
                        </ul>
                      ) : <p className="mt-2 text-xs text-slate-500">No specific items from the supplied requirements.</p>}
                    </div>
                  ))}
                </div>

                <p className="border-t border-slate-800 pt-3 text-[11px] leading-relaxed text-slate-500">{result.disclaimer}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-white">Saved comparison history</h2>
            <p className="mt-1 text-xs text-slate-500">Stored in the application's database; up to 100 recent comparisons shown.</p>
          </div>
          <button type="button" onClick={() => resumeId && void refreshComparisons(resumeId).catch((loadError: unknown) => setError(getErrorMessage(loadError)))} className="text-xs text-indigo-300 hover:text-indigo-200">Refresh</button>
        </div>
        {savedComparisons.length ? (
          <div className="mt-4 divide-y divide-slate-800">
            {savedComparisons.map((comparison) => (
              <div key={comparison.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-200">{comparison.job.title} <span className="font-normal text-slate-500">· {comparison.job.employer || 'Employer not provided'}</span></p>
                  <p className="mt-1 text-xs text-slate-500">{comparison.created_at ? new Date(comparison.created_at).toLocaleString() : 'Saved'} · {comparison.skill_matches.filter((item) => item.status === 'matched').length} skills matched</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-white">{comparison.overall_score.toFixed(1)}%</span>
                  <button type="button" onClick={() => void removeSaved(comparison.id)} aria-label={`Delete saved comparison for ${comparison.job.title}`} className="rounded-md p-2 text-slate-500 hover:bg-rose-950/30 hover:text-rose-300">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : <p className="mt-4 text-sm text-slate-500">No saved comparisons for this resume yet.</p>}
      </section>

      {/* Tailored Application Modal */}
      {tailorModalOpen && tailoredData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileDown className="w-5 h-5 text-indigo-400" />
                  <span>Tailored Application Assets</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Custom-tailored summary, targeted bullets, and ready-to-send cover letter.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setTailorModalOpen(false)}
                className="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 font-medium"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  Targeted Executive Summary
                </label>
                <div className="mt-1.5 p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 leading-relaxed font-sans">
                  {tailoredData.tailored_summary}
                </div>
              </div>

              <div>
                <label className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  Prioritized High-Relevance Skills
                </label>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {tailoredData.prioritized_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  Role-Tailored Bullet Points
                </label>
                <ul className="mt-1.5 space-y-2 p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200">
                  {tailoredData.tailored_bullet_points.map((bullet, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-indigo-400 font-bold">•</span>
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                    Tailored Cover Letter
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(tailoredData.cover_letter);
                      alert('Cover letter copied to clipboard!');
                    }}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold underline"
                  >
                    Copy to Clipboard
                  </button>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 whitespace-pre-line leading-relaxed font-sans">
                  {tailoredData.cover_letter}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
