import React, { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CheckCircle2, LoaderCircle, SearchCheck } from 'lucide-react';
import { api } from '../services/api';
import { ATSReport } from '../types';

interface ResumeAssessment {
  id: string;
  filename: string;
  quality_score: number;
  is_scanned: boolean;
  ocr_status?: string;
  warnings: string[];
  page_count: number;
  word_count: number;
  detected_sections: string[];
  profile: { name: string; skills: string[] };
  ats_report: ATSReport;
}

const scoreItems: Array<{ key: keyof ATSReport['category_scores']; label: string }> = [
  { key: 'section_structure_score', label: 'Section structure' },
  { key: 'contact_completeness_score', label: 'Contact completeness' },
  { key: 'content_impact_score', label: 'Content impact' },
  { key: 'formatting_quality_score', label: 'Formatting quality' },
  { key: 'skill_consistency_score', label: 'Skill evidence' },
];

export const ATSValidation: React.FC = () => {
  const [resume, setResume] = useState<ResumeAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [requiredSkills, setRequiredSkills] = useState('');
  const [preferredSkills, setPreferredSkills] = useState('');

  useEffect(() => {
    const resumeId = sessionStorage.getItem('careerpilot.resumeId');
    if (!resumeId) {
      setError('Parse or upload a resume in Resume Studio before running ATS validation.');
      setLoading(false);
      return;
    }

    api.getResume(resumeId)
      .then((data: ResumeAssessment) => setResume(data))
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load this resume assessment.');
      })
      .finally(() => setLoading(false));
  }, []);

  const analyzeJob = async (event: FormEvent) => {
    event.preventDefault();
    if (!resume || !requiredSkills.trim()) {
      setError('Enter at least one required skill to calculate job alignment.');
      return;
    }

    setAnalyzing(true);
    setError(null);
    try {
      const required = requiredSkills.split(',').map((skill) => skill.trim()).filter(Boolean);
      const preferred = preferredSkills.split(',').map((skill) => skill.trim()).filter(Boolean);
      const result = await api.analyzeAgainstJob(
        resume.id,
        jobDescription,
        required,
        preferred,
      );
      setResume({ ...resume, ats_report: result.ats_report });
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : 'Job alignment could not be calculated.');
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-sm text-slate-400">Loading resume assessment…</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-8">
      <header>
        <Link to="/resume-studio" className="mb-4 inline-flex items-center text-sm text-indigo-400 hover:text-indigo-300">
          <ArrowLeft className="mr-1.5 h-4 w-4" /> Resume Studio
        </Link>
        <h1 className="text-2xl font-bold text-white">ATS-Style Validation</h1>
        <p className="mt-1 text-sm text-slate-400">
          Deterministic checks on extracted resume text. This is not an official ATS score and does not predict screening outcomes.
        </p>
      </header>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-950/30 p-4 text-sm text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
          {!resume && (
            <Link to="/resume-studio" className="ml-auto shrink-0 underline">Open Resume Studio</Link>
          )}
        </div>
      )}

      {resume && (
        <>
          {resume.warnings.length > 0 && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-950/20 p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-amber-200">
                <AlertTriangle className="h-4 w-4" /> Extraction warnings
              </h2>
              <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-amber-100/80">
                {resume.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
              <p className="mt-2 text-xs text-slate-400">
                {resume.page_count} page(s) · {resume.word_count} extracted words · quality {(resume.quality_score * 100).toFixed(0)}%
              </p>
            </div>
          )}

          <section className="grid gap-4 md:grid-cols-[1fr_2fr]">
            <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-indigo-300">General ATS-style score</p>
              <p className="mt-2 text-4xl font-bold text-white">
                {resume.ats_report.overall_score}<span className="text-lg font-medium text-slate-400"> / 100</span>
              </p>
              <p className="mt-3 text-xs leading-relaxed text-slate-400">
                Heuristic score from structure, contact details, content impact, formatting and skill evidence.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="font-semibold text-white">{resume.profile.name || 'Candidate profile'}</h2>
              <p className="mt-1 truncate text-xs text-slate-500">{resume.filename}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                {scoreItems.map(({ key, label }) => (
                  <div key={key} className="rounded-lg bg-slate-950/70 p-3">
                    <p className="text-[11px] text-slate-500">{label}</p>
                    <p className="mt-1 text-lg font-semibold text-slate-100">
                      {resume.ats_report.category_scores[key] ?? '—'}
                      {resume.ats_report.category_scores[key] !== undefined && <span className="text-xs text-slate-500">%</span>}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="mb-4 flex items-center gap-2 font-semibold text-white">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Structural checks
              </h2>
              <div className="space-y-3">
                {resume.ats_report.checks.map((check) => (
                  <article key={check.name} className="border-b border-slate-800 pb-3 last:border-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-medium text-slate-200">{check.name}</h3>
                      <span className={`shrink-0 text-xs ${check.passed ? 'text-emerald-400' : 'text-amber-300'}`}>
                        {check.score}/{check.max_score}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">{check.details}</p>
                  </article>
                ))}
              </div>
              {resume.ats_report.missing_sections.length > 0 && (
                <p className="mt-4 text-xs text-amber-300">
                  Sections not detected: {resume.ats_report.missing_sections.join(', ')}
                </p>
              )}
              {resume.ats_report.found_sections.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">
                  Detected: {resume.ats_report.found_sections.join(', ')}
                </p>
              )}
            </div>

            <div className="space-y-6">
              <form onSubmit={analyzeJob} className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <h2 className="flex items-center gap-2 font-semibold text-white">
                  <SearchCheck className="h-4 w-4 text-cyan-400" /> Compare with a job
                </h2>
                <p className="text-xs text-slate-400">
                  Job alignment checks listed skills against extracted resume skills. It is separate from the general score.
                </p>
                <textarea
                  value={jobDescription}
                  onChange={(event) => setJobDescription(event.target.value)}
                  rows={4}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
                  placeholder="Paste the job description (optional context)"
                />
                <input
                  value={requiredSkills}
                  onChange={(event) => setRequiredSkills(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
                  placeholder="Required skills, comma separated (e.g. Python, SQL)"
                />
                <input
                  value={preferredSkills}
                  onChange={(event) => setPreferredSkills(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
                  placeholder="Preferred skills, comma separated (optional)"
                />
                <button
                  type="submit"
                  disabled={analyzing || !requiredSkills.trim()}
                  className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {analyzing && <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />}
                  {analyzing ? 'Comparing…' : 'Calculate job alignment'}
                </button>
                {resume.ats_report.category_scores.job_alignment_score !== undefined &&
                  resume.ats_report.category_scores.job_alignment_score !== null && (
                    <p className="text-sm font-medium text-cyan-300">
                      Job alignment: {resume.ats_report.category_scores.job_alignment_score}/100
                    </p>
                  )}
              </form>

              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <h2 className="font-semibold text-white">Evidence and suggestions</h2>
                <div className="mt-3 space-y-2">
                  {(resume.ats_report.evidence_items ?? []).map((item) => (
                    <p key={`${item.skill}-${item.source}`} className="text-xs text-slate-400">
                      <span className={item.evidence_found ? 'text-emerald-300' : 'text-amber-300'}>
                        {item.evidence_found ? 'Evidence found' : 'Not evidenced'}
                      </span>
                      {' · '}{item.skill}: {item.source}
                    </p>
                  ))}
                  {resume.ats_report.suggestions.map((suggestion) => (
                    <p key={suggestion} className="text-xs leading-relaxed text-slate-300">• {suggestion}</p>
                  ))}
                  {resume.ats_report.formatting_warnings.map((warning) => (
                    <p key={warning} className="text-xs leading-relaxed text-amber-300">• {warning}</p>
                  ))}
                </div>
                <p className="mt-4 border-t border-slate-800 pt-3 text-[11px] leading-relaxed text-slate-500">
                  {resume.ats_report.disclaimer}
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
};
