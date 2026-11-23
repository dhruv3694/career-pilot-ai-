import React, { useState } from 'react';
import { Upload, FileText, Check, AlertTriangle, ArrowRight, Save, Edit3 } from 'lucide-react';
import { api } from '../services/api';
import { CandidateProfile } from '../types';
import { useNavigate } from 'react-router-dom';

export const ResumeStudio: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'upload' | 'paste'>('paste');
  const [rawText, setRawText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resumeId, setResumeId] = useState<string | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

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
    } catch (e: any) {
      setError(e.message || 'Error uploading file');
    } finally {
      setLoading(false);
    }
  };

  const handleParseText = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.parseText(rawText);
      sessionStorage.setItem('careerpilot.resumeId', res.resume_id);
      setResumeId(res.resume_id);
      setProfile(res.profile);
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
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Error updating profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white">Resume Studio</h1>
        <p className="text-sm text-slate-400">
          Upload or paste your resume. Our open-source parser extracts contact info, skills, and work history for user review.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/50 border border-red-500/30 text-red-200 text-sm flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload & Ingestion Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800">
          <div className="flex border-b border-slate-800 pb-3 space-x-4">
            <button
              onClick={() => setActiveTab('paste')}
              className={`text-sm font-semibold pb-1 border-b-2 transition-all ${
                activeTab === 'paste' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400'
              }`}
            >
              Paste Resume Text
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`text-sm font-semibold pb-1 border-b-2 transition-all ${
                activeTab === 'upload' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400'
              }`}
            >
              Upload Document (PDF/DOCX)
            </button>
          </div>

          {activeTab === 'upload' ? (
            <div className="space-y-4">
              <label className="border-2 border-dashed border-slate-700 hover:border-indigo-500/50 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950/40">
                <Upload className="w-10 h-10 text-slate-400 mb-3" />
                <span className="text-sm font-medium text-slate-200">
                  {file ? file.name : 'Select or drop PDF, DOCX, or TXT resume'}
                </span>
                <span className="text-xs text-slate-500 mt-1">Up to 10MB</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>

              <button
                onClick={handleUploadFile}
                disabled={!file || loading}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm disabled:opacity-50 transition-colors"
              >
                {loading ? 'Processing Document...' : 'Parse Uploaded Document'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <textarea
                rows={14}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                className="w-full bg-slate-950/60 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500 leading-relaxed"
                placeholder="Paste plain resume text here..."
              />
              <button
                onClick={handleParseText}
                disabled={loading || rawText.trim().length < 20}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm disabled:opacity-50 transition-colors"
              >
                {loading ? 'Extracting Structure...' : 'Extract Candidate Profile'}
              </button>
            </div>
          )}
        </div>

        {/* Extracted Profile Review & Corrections */}
        <div className="space-y-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Edit3 className="w-4 h-4 text-indigo-400" />
                <h2 className="font-semibold text-white text-sm">Extracted Profile (User Review)</h2>
              </div>
              {profile && (
                <button
                  onClick={handleSaveProfileChanges}
                  disabled={loading}
                  className="inline-flex items-center px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                >
                  <Save className="w-3.5 h-3.5 mr-1" />
                  Save Corrections
                </button>
              )}
            </div>

            {saveSuccess && (
              <div className="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-1.5">
                <Check className="w-4 h-4" />
                <span>Profile corrections saved and ATS scores re-computed.</span>
              </div>
            )}

            {profile ? (
              <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                <div>
                  <label className="text-xs text-slate-400 font-medium">Candidate Name</label>
                  <input
                    type="text"
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 font-medium">Email</label>
                    <input
                      type="text"
                      value={profile.email || ''}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-medium">Phone</label>
                    <input
                      type="text"
                      value={profile.phone || ''}
                      onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                      className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-medium">Summary</label>
                  <textarea
                    rows={3}
                    value={profile.summary || ''}
                    onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-medium">Extracted Technical Skills</label>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {profile.skills.map((skill, i) => (
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
                  <label className="text-xs text-slate-400 font-medium">Experience Entries ({profile.experience?.length || 0})</label>
                  <div className="mt-1 space-y-2">
                    {profile.experience?.map((exp, i) => (
                      <div key={i} className="p-2.5 rounded bg-slate-950/40 border border-slate-800 text-xs">
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
                Extract or upload a resume to review and correct structured candidate details.
              </div>
            )}
          </div>

          {profile && (
            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={() => navigate('/ats-validation')}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center justify-center space-x-2"
              >
                <span>Proceed to ATS Validation & Score Breakdown</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
