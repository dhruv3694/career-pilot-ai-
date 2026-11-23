import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

export const Demonstrations: React.FC = () => {
  const [demos, setDemos] = useState<any[]>([]);
  useEffect(() => { api.getDemonstrations().then((res) => setDemos(res.demonstrations || [])).catch(()=>{}); }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Jury Demonstrations</h1>
        <p className="mt-2 text-sm text-slate-400">Pre-configured demonstration scenarios.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {demos.map((d, idx) => (
          <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-lg font-semibold text-white">{d.title}</h2>
            <p className="mt-1 text-sm text-slate-400">{d.description}</p>
            <p className="mt-2 text-xs text-slate-500">Target: {d.target_role}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
