import React, { useState, useEffect } from 'react';
import { Upload, FileText, Check, AlertTriangle, Save, Edit3, CheckCircle2, SearchCheck, LoaderCircle, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { CandidateProfile, ATSReport } from '../types';

interface ResumeAssessment {
  id: string;
  filename: string;
  quality_score: number;
  is_scanned: boolean;
  warnings: string[];
  page_count: number;
  word_count: number;
  profile: CandidateProfile;
  ats_report: ATSReport;
}

const scoreItems: Array<{ key: keyof ATSReport['category_scores']; label: string }> = [
  { key: 'section_structure_score', label: 'Section structure' },
  { key: 'contact_completeness_score', label: 'Contact completeness' },
  { key: 'content_impact_score', label: 'Content impact' },
  { key: 'formatting_quality_score', label: 'Formatting quality' },
  { key: 'skill_consistency_score', label: 'Skill evidence' },
];

export const ResumeStudio: React.FC = () => {
  const [activeMode, setActiveMode] = useState<'editor' | 'ats'>('editor');
  const [inputTab, setInputTab] = useState<'paste' | 'upload'>('paste');
  const [rawText, setRawText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resumeId, setResumeId] = useState<string | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [resumeAssessment, setResumeAssessment] = useState<ResumeAssessment | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Quick ATS job alignment test
  const [jobDescription, setJobDescription] = useState('');
  const [requiredSkills, setRequiredSkills] = useState('');
  const [preferredSkills, setPreferredSkills] = useState('');
  const [analyzingJob, setAnalyzingJob] = useState(false);

  // Load existing session resume if available
  useEffect(() => {
    const storedId = sessionStorage.getItem('careerpilot.resumeId');
    if (storedId) {
      setResumeId(storedId);
      api.getResume(storedId)
        .then((res: any) => {
          setResumeAssessment(res);
          setProfile(res.profile);
        })
        .catch(() => {});
    }
  }, []);

  const handleUploadFile = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.uploadResume(file);
      if (res.status === 'needs_ocr') {
        sessionStorage.removeItem('careerpilot.resumeId');
        setResumeId(null);
        setProfile(null);
        setError(res.warnings?.join(' ') || 'This scanned document could not be read.');
        return;
      }
      sessionStorage.setItem('careerpilot.resumeId', res.resume_id);
      setResumeId(res.resume_id);
      setProfile(res.profile);
      setRawText(res.raw_text);

      const assessment = await api.getResume(res.resume_id);
      setResumeAssessment(assessment);
    } catch (e: any) {
      setError(e.message || 'Error uploading file');
    } finally {
      setLoading(false);
    }
  };

  const handleParseText = async () => {
    if (!rawText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.parseText(rawText);
      sessionStorage.setItem('careerpilot.resumeId', res.resume_id);
      setResumeId(res.resume_id);
      setProfile(res.profile);

      const assessment = await api.getResume(res.resume_id);
      setResumeAssessment(assessment);
    } catch (e: any) {
      setError(e.message || 'Error parsing text');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfileChanges = async () => {
    if (!resumeId || !profile) return;
    setLoading(true);
    try {
      await api.updateProfile(resumeId, profile);
      setSaveSuccess(true);
      const assessment = await api.getResume(resumeId);
      setResumeAssessment(assessment);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Error updating profile');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeJobAlignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resumeId || !requiredSkills.trim()) {
      setError('Please provide at least one required skill for job alignment.');
      return;
    }
    setAnalyzingJob(true);
    setError(null);
    try {
      const req = requiredSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const pref = preferredSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await api.analyzeAgainstJob(resumeId, jobDescription, req, pref);
      if (resumeAssessment) {
        setResumeAssessment({ ...resumeAssessment, ats_report: res.ats_report });
      }
    } catch (e: any) {
      setError(e.message || 'Failed to analyze against job');
    } finally {
      setAnalyzingJob(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header with View Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <span>Resume & ATS Studio</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium">Unified</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Extract profile data, review & edit skills, and inspect real-time ATS compliance and job-targeting scores.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveMode('editor')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
              activeMode === 'editor'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Profile & Editor</span>
          </button>
          <button
            onClick={() => setActiveMode('ats')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
              activeMode === 'ats'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <SearchCheck className="w-3.5 h-3.5" />
            <span>ATS Score & Checks</span>
            {resumeAssessment?.ats_report && (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-indigo-900 text-indigo-200 text-[10px]">
                {resumeAssessment.ats_report.overall_score}%
              </span>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-200 text-sm flex items-start space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Editor Tab View */}
      {activeMode === 'editor' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload / Paste Column */}
          <div className="space-y-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800">
            <div className="flex border-b border-slate-800">
              <button
                className={`pb-2.5 px-4 text-xs font-semibold transition-colors flex items-center space-x-2 border-b-2 ${
                  inputTab === 'paste'
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
                onClick={() => setInputTab('paste')}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Paste Resume Text</span>
              </button>
              <button
                className={`pb-2.5 px-4 text-xs font-semibold transition-colors flex items-center space-x-2 border-b-2 ${
                  inputTab === 'upload'
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
                onClick={() => setInputTab('upload')}
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Document (.pdf, .docx, .txt)</span>
              </button>
            </div>

            {inputTab === 'paste' ? (
              <div className="space-y-3">
                <textarea
                  className="w-full h-80 bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none resize-none leading-relaxed"
                  placeholder="Paste your raw resume text here..."
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                />
                <button
                  onClick={handleParseText}
                  disabled={loading || !rawText.trim()}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-2 disabled:opacity-50 transition-colors shadow-lg shadow-indigo-600/20"
                >
                  {loading ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  <span>{loading ? 'Analyzing Structure...' : 'Extract & Parse Resume'}</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 text-center transition-colors">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-400 mb-2">Drop your resume file or browse</p>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                  />
                  {file && <p className="text-xs text-indigo-400 mt-3 font-medium">Selected: {file.name}</p>}
                </div>
                <button
                  onClick={handleUploadFile}
                  disabled={loading || !file}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-2 disabled:opacity-50 transition-colors"
                >
                  {loading ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  <span>{loading ? 'Processing File...' : 'Upload & Extract'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Profile Review & Corrections Column */}
          <div className="space-y-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <Edit3 className="w-4 h-4 text-indigo-400" />
                  <h2 className="font-semibold text-white text-sm">Extracted Profile Review</h2>
                </div>
                {profile && (
                  <button
                    onClick={handleSaveProfileChanges}
                    disabled={loading}
                    className="inline-flex items-center px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5 mr-1" />
                    Save Corrections
                  </button>
                )}
              </div>

              {saveSuccess && (
                <div className="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-1.5">
                  <Check className="w-4 h-4" />
                  <span>Profile saved and ATS scores recalculated.</span>
                </div>
              )}

              {profile ? (
                <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1 text-xs">
                  <div>
                    <label className="text-slate-400 font-medium">Candidate Name</label>
                    <input
                      type="text"
                      value={profile.name}
                      onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                      className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 font-medium">Email</label>
                      <input
                        type="text"
                        value={profile.email || ''}
                        onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                        className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 font-medium">Phone</label>
                      <input
                        type="text"
                        value={profile.phone || ''}
                        onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                        className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 font-medium">Professional Summary</label>
                    <textarea
                      rows={3}
                      value={profile.summary || ''}
                      onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                      className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="text-slate-400 font-medium">Extracted Technical Skills ({profile.skills?.length || 0})</label>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {profile.skills?.map((skill, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 font-medium">Experience ({profile.experience?.length || 0})</label>
                    <div className="mt-1 space-y-2">
                      {profile.experience?.map((exp, i) => (
                        <div key={i} className="p-2.5 rounded bg-slate-950/40 border border-slate-800">
                          <div className="font-semibold text-slate-200">{exp.title}</div>
                          <ul className="list-disc list-inside text-slate-400 mt-1 space-y-0.5">
                            {exp.bullets?.slice(0, 2).map((b, bi) => (
                              <li key={bi} className="truncate">{b}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-24 text-center text-slate-500 text-xs">
                  Upload or paste a resume to inspect and edit extracted credentials.
                </div>
              )}
            </div>

            {resumeAssessment && (
              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <div className="text-xs text-slate-400">
                  ATS Score: <span className="text-white font-bold text-sm ml-1">{resumeAssessment.ats_report.overall_score}%</span>
                </div>
                <button
                  onClick={() => setActiveMode('ats')}
                  className="px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold border border-indigo-500/30 transition-colors"
                >
                  View Full ATS Audit →
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ATS Validation View */}
      {activeMode === 'ats' && (
        <div className="space-y-6">
          {!resumeAssessment ? (
            <div className="text-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800 p-8">
              <SearchCheck className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-white">No Resume Extracted Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-4">
                Please upload or paste your resume in the Editor view first to run automatic ATS validation checks.
              </p>
              <button
                onClick={() => setActiveMode('editor')}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold"
              >
                Go to Editor
              </button>
            </div>
          ) : (
            <>
              {/* Score summary cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-5 flex flex-col justify-between">
                  <div>
                    <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider">Overall Score</span>
                    <div className="mt-2 text-4xl font-extrabold text-white">
                      {resumeAssessment.ats_report.overall_score}<span className="text-base font-medium text-slate-400">/100</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 mt-3">Weighted average of structure, formatting, and skills.</p>
                </div>

                <div className="md:col-span-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                  <div className="text-xs font-semibold text-slate-300 mb-3">Category Breakdown</div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                    {scoreItems.map(({ key, label }) => (
                      <div key={key} className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl">
                        <div className="text-[11px] text-slate-500 truncate">{label}</div>
                        <div className="text-lg font-bold text-slate-100 mt-1">
                          {resumeAssessment.ats_report.category_scores[key] ?? 0}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Detailed Checks and Job Alignment */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Structural Checks */}
                <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>ATS Compliance Checks</span>
                  </h3>
                  <div className="space-y-3">
                    {resumeAssessment.ats_report.checks.map((chk, i) => (
                      <div key={i} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-start justify-between">
                        <div>
                          <div className="text-xs font-medium text-slate-200">{chk.name}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{chk.details}</div>
                        </div>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${chk.passed ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-300'}`}>
                          {chk.score}/{chk.max_score}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Job Alignment Simulation */}
                <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                    <SearchCheck className="w-4 h-4 text-indigo-400" />
                    <span>Target Job Alignment</span>
                  </h3>
                  <form onSubmit={handleAnalyzeJobAlignment} className="space-y-3">
                    <div>
                      <label className="text-[11px] text-slate-400 font-medium">Required Skills (comma separated)</label>
                      <input
                        type="text"
                        value={requiredSkills}
                        onChange={(e) => setRequiredSkills(e.target.value)}
                        placeholder="e.g. React, TypeScript, Node.js"
                        className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 font-medium">Job Description (optional)</label>
                      <textarea
                        rows={3}
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="Paste target job requirements to check keyword density..."
                        className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={analyzingJob}
                      className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-2 disabled:opacity-50"
                    >
                      {analyzingJob ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <SearchCheck className="w-4 h-4" />}
                      <span>Compute Job Match Score</span>
                    </button>
                  </form>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
