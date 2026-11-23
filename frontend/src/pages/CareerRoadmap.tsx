import React, { FormEvent, useEffect, useState } from 'react';
import { CheckCircle2, LoaderCircle, Plus } from 'lucide-react';
import { api } from '../services/api';

interface Milestone {
  title: string;
  description: string;
  skills_to_learn: string[];
  resources: Array<{ name: string; url: string; resource_type: string; is_free: boolean }>;
  estimated_weeks: number;
  order: number;
}

interface Roadmap {
  target_role: string;
  current_skills: string[];
  skill_gaps: Array<{ skill: string; current_level: string; target_level: string; priority: string }>;
  milestones: Milestone[];
  estimated_total_weeks: number;
}

interface ProgressItem {
  milestone_id: string;
  status: string;
  notes?: string;
}

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-500";

export const CareerRoadmap: React.FC = () => {
  const [targetRole, setTargetRole] = useState("Software Engineer");
  const [currentSkills, setCurrentSkills] = useState("");
  const [skillGaps, setSkillGaps] = useState("");
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [progress, setProgress] = useState<ProgressItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCareerProgress().then((res) => setProgress(res.progress || [])).catch(() => {});
  }, []);

  const generate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.generateCareerRoadmap({
        target_role: targetRole,
        current_skills: currentSkills.split(',').map((s) => s.trim()).filter(Boolean),
        skill_gaps: skillGaps.split(',').map((s) => s.trim()).filter(Boolean),
      });
      setRoadmap(res.roadmap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate roadmap");
    } finally {
      setLoading(false);
    }
  };

  const updateProgress = async (milestoneId: string, status: string) => {
    try {
      await api.updateCareerProgress({ milestone_id: milestoneId, status });
      const res = await api.getCareerProgress();
      setProgress(res.progress || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update progress");
    }
  };

  const getStatus = (id: string) => progress.find((p) => p.milestone_id === id)?.status || "not_started";

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Career Roadmap</h1>
        <p className="mt-2 text-sm text-slate-400">Personalized learning plan with milestones and resources.</p>
      </header>

      <form onSubmit={generate} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm text-slate-300">Target Role</label>
            <input value={targetRole} onChange={(e) => setTargetRole(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Current Skills</label>
            <input value={currentSkills} onChange={(e) => setCurrentSkills(e.target.value)} className={inputClass} placeholder="Python, SQL" />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Skill Gaps</label>
            <input value={skillGaps} onChange={(e) => setSkillGaps(e.target.value)} className={inputClass} placeholder="React, Docker" />
          </div>
        </div>
        <button type="submit" disabled={loading} className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {loading ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
          Generate Roadmap
        </button>
        {error && <p className="text-sm text-rose-400">{error}</p>}
      </form>

      {roadmap && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-lg font-semibold text-white">{roadmap.target_role} Roadmap</h2>
            <p className="mt-1 text-sm text-slate-400">Estimated {roadmap.estimated_total_weeks} weeks</p>
          </div>
          {roadmap.milestones?.map((m, idx) => {
            const status = getStatus(`m${idx}`);
            return (
              <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-white">{m.title}</h3>
                    <p className="mt-1 text-sm text-slate-400">{m.description}</p>
                    <p className="mt-2 text-xs text-slate-500">~{m.estimated_weeks} weeks • Skills: {m.skills_to_learn?.join(', ')}</p>
                  </div>
                  <button onClick={() => updateProgress(`m${idx}`, status === "completed" ? "not_started" : "completed")} className="inline-flex items-center rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-emerald-500">
                    <CheckCircle2 className="mr-1 h-3 w-3" /> {status === "completed" ? "Mark Incomplete" : "Mark Complete"}
                  </button>
                </div>
                {m.resources && m.resources.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-slate-400 mb-2">Resources</p>
                    <div className="flex flex-wrap gap-2">
                      {m.resources.map((r, i) => (
                        <a key={i} href={r.url} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-indigo-300 hover:border-indigo-500">
                          {r.name} {r.is_free && "(Free)"}
                        </a>
                      ))}
                    </div>
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
