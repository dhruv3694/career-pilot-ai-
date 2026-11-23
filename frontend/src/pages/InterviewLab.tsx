import React, { useState } from 'react';
import { LoaderCircle, PlayCircle, Send, Award, Sparkles, BookOpen, CheckCircle, ChevronDown } from 'lucide-react';
import { api } from '../services/api';

interface Question {
  id: string;
  question_id?: string;
  question: string;
  category: string;
  difficulty: string;
  sample_answer: string;
}

interface Session {
  session_id: string;
  role: string;
  questions: Question[];
}

interface EvaluationResult {
  question_id: string;
  score: number;
  overall_score: number;
  rating: string;
  feedback: string;
  strengths: string[];
  improvements: string[];
  llm_feedback?: string;
  model_answer?: string;
}

// Available formats with their specific question capacity
const FORMAT_CONFIG: Record<string, { label: string; maxCount: number; defaultCount: number }> = {
  technical: { label: 'Technical In-Depth', maxCount: 20, defaultCount: 5 },
  behavioral: { label: 'Behavioral (STAR Method)', maxCount: 20, defaultCount: 5 },
  system_design: { label: 'System Design & Architecture', maxCount: 20, defaultCount: 4 },
  coding: { label: 'Coding & Data Structures', maxCount: 20, defaultCount: 4 },
  mixed: { label: 'Comprehensive Mixed (All Topics)', maxCount: 80, defaultCount: 8 },
};

export const InterviewLab: React.FC = () => {
  const [role, setRole] = useState('software_engineer');
  const [sessionType, setSessionType] = useState('technical');
  const [count, setCount] = useState(5);
  const [session, setSession] = useState<Session | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  
  // Store evaluation results per question_id so multiple evaluations remain visible cleanly
  const [evaluations, setEvaluations] = useState<Record<string, EvaluationResult>>({});
  const [loading, setLoading] = useState(false);
  const [evaluatingQId, setEvaluatingQId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // When format changes, dynamically adapt the count slider to that format's capacity
  const handleFormatChange = (newFormat: string) => {
    setSessionType(newFormat);
    const config = FORMAT_CONFIG[newFormat] || FORMAT_CONFIG.technical;
    setCount(Math.min(count, config.maxCount) || config.defaultCount);
  };

  const currentFormatConfig = FORMAT_CONFIG[sessionType] || FORMAT_CONFIG.technical;

  const startSession = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.startInterviewSession({ role, session_type: sessionType, count });
      setSession(res.session);
      setEvaluations({});
      setAnswers({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (q: Question) => {
    const qKey = q.id || q.question_id || q.question;
    setError(null);
    setEvaluatingQId(qKey);
    try {
      const candidateAnswer = answers[qKey] || '';
      const res = await api.evaluateInterviewAnswer({
        question_id: qKey,
        question: q.question,
        sample_answer: q.sample_answer || '',
        candidate_answer: candidateAnswer,
        category: q.category,
        role,
      });
      // Save evaluation strictly for this question
      setEvaluations((prev) => ({
        ...prev,
        [qKey]: res.evaluation,
      }));
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setEvaluatingQId(null);
    }
  };

  // Strictly insert reference outline ONLY into the specific question clicked
  const insertReferenceOutline = (questionKey: string, sample: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionKey]: sample || 'In my previous experience, I addressed this requirement by applying structured architecture...',
    }));
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white">Interview Preparation Lab</h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Targeted interview practice with custom question formats, answer outlines, and instant rubric-based AI scoring.
        </p>
      </header>

      {/* Session Config with format-adaptive range slider */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-xs font-semibold text-slate-300 uppercase tracking-wider">Target Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
            >
              <option value="software_engineer">Software Engineer</option>
              <option value="frontend_developer">Frontend Developer</option>
              <option value="backend_developer">Backend Developer</option>
              <option value="data_scientist">Data Scientist</option>
              <option value="ml_engineer">ML Engineer</option>
              <option value="devops_engineer">DevOps Engineer</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold text-slate-300 uppercase tracking-wider">Interview Format</label>
            <select
              value={sessionType}
              onChange={(e) => handleFormatChange(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
            >
              {Object.entries(FORMAT_CONFIG).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.label} (Up to {config.maxCount} Qs)
                </option>
              ))}
            </select>
          </div>

          {/* Dynamic Format-Specific Slider */}
          <div className="flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Question Count
              </label>
              <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold">
                {count} {count === 1 ? 'Question' : 'Questions'}
              </span>
            </div>
            <div className="space-y-2 pt-1">
              <input
                type="range"
                min={1}
                max={currentFormatConfig.maxCount}
                value={Math.min(count, currentFormatConfig.maxCount)}
                onChange={(e) => setCount(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 transition-all"
              />
              <div className="flex justify-between text-[11px] text-slate-500 font-medium px-0.5">
                <span>1</span>
                <span>{Math.round(currentFormatConfig.maxCount / 2)}</span>
                <span>{currentFormatConfig.maxCount} Max</span>
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={startSession}
          disabled={loading}
          className="inline-flex items-center rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors shadow-lg shadow-indigo-600/20"
        >
          {loading ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
          Start Interview Session
        </button>
        {error && <p className="text-xs text-rose-400">{error}</p>}
      </div>

      {/* Questions list */}
      {session && (
        <div className="space-y-6">
          {session.questions?.map((q, idx) => {
            const qKey = q.id || q.question_id || q.question;
            const qEval = evaluations[qKey];
            const isEvaluatingThis = evaluatingQId === qKey;

            return (
              <div key={qKey} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold">
                      Question {idx + 1}
                    </span>
                    <span className="text-xs text-slate-500 uppercase tracking-wider">
                      {q.category} • {q.difficulty}
                    </span>
                  </div>
                  {qEval && (
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Evaluated: {qEval.overall_score}%</span>
                    </span>
                  )}
                </div>

                <p className="text-sm font-medium text-white leading-relaxed">{q.question}</p>

                <div className="space-y-2">
                  <label className="text-xs text-slate-400 font-medium">Your Response:</label>
                  <textarea
                    value={answers[qKey] || ''}
                    onChange={(e) => setAnswers({ ...answers, [qKey]: e.target.value })}
                    placeholder="Type your response here..."
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3.5 text-xs text-slate-200 h-32 outline-none focus:border-indigo-500 leading-relaxed font-sans"
                  />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => submitAnswer(q)}
                      disabled={isEvaluatingThis || !answers[qKey]?.trim()}
                      className="inline-flex items-center rounded-xl bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white disabled:opacity-40 transition-colors shadow-sm"
                    >
                      {isEvaluatingThis ? (
                        <LoaderCircle className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <Send className="w-3.5 h-3.5 mr-1.5" />
                      )}
                      <span>Evaluate Answer</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => insertReferenceOutline(qKey, q.sample_answer)}
                      className="inline-flex items-center space-x-1 text-xs text-slate-400 hover:text-slate-300 underline ml-2"
                    >
                      <BookOpen className="w-3.5 h-3.5 mr-1" />
                      <span>Insert Reference Outline</span>
                    </button>
                  </div>

                  {answers[qKey]?.trim() && (
                    <button
                      type="button"
                      onClick={() => setAnswers({ ...answers, [qKey]: '' })}
                      className="text-[11px] text-slate-500 hover:text-slate-400"
                    >
                      Clear
                    </button>
                  )}
                </div>

                {/* Per-Question Evaluation Card */}
                {qEval && (
                  <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/80 p-5 space-y-3.5 animate-in fade-in duration-200">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                      <h3 className="text-xs font-bold text-white flex items-center space-x-1.5 uppercase tracking-wider">
                        <Award className="w-4 h-4 text-indigo-400" />
                        <span>Evaluation for Question {idx + 1}</span>
                      </h3>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs text-slate-400">Score:</span>
                        <span className="text-sm font-extrabold text-white">
                          {qEval.overall_score}<span className="text-[11px] text-slate-500">/100</span>
                        </span>
                        <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[11px] font-bold uppercase">
                          {qEval.rating}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {qEval.strengths && qEval.strengths.length > 0 && (
                        <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/20">
                          <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-1.5">Key Strengths</p>
                          <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                            {qEval.strengths.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {qEval.improvements && qEval.improvements.length > 0 && (
                        <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20">
                          <p className="text-[11px] font-bold text-amber-400 uppercase tracking-wider mb-1.5">Improvement Areas</p>
                          <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                            {qEval.improvements.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {qEval.feedback && (
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
                        <span className="font-semibold text-slate-200">Rubric Feedback: </span>
                        {qEval.feedback}
                      </div>
                    )}

                    {qEval.llm_feedback && (
                      <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                        <p className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Coach Commentary</span>
                        </p>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans">
                          {qEval.llm_feedback}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
