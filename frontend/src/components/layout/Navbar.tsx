import React, { useEffect, useState } from 'react';
import { Bot, Cpu, ShieldCheck, Zap, AlertCircle, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const [providerInfo, setProviderInfo] = useState<{
    primary: string;
    is_proprietary: boolean;
    is_fallback: boolean;
    healthy: boolean;
  }>({
    primary: 'Checking provider status',
    is_proprietary: false,
    is_fallback: false,
    healthy: false,
  });

  useEffect(() => {
    api.getProvidersStatus()
      .then((data) => {
        if (data.providers) {
          if (data.providers.groq?.available) {
            setProviderInfo({
              primary: `Groq (${data.providers.groq.model}) [Tier 2 Open-Weight]`,
              is_proprietary: false,
              is_fallback: false,
              healthy: true,
            });
          } else if (data.providers.gemini?.available) {
            setProviderInfo({
              primary: `Gemini (${data.providers.gemini.model}) [Tier 3 Proprietary]`,
              is_proprietary: true,
              is_fallback: false,
              healthy: true,
            });
          } else {
            setProviderInfo({
              primary: 'Deterministic Rule Engine (Tier 1 Local)',
              is_proprietary: false,
              is_fallback: true,
              healthy: true,
            });
          }
        }
      })
      .catch(() => {
        setProviderInfo({
          primary: 'Provider status unavailable',
          is_proprietary: false,
          is_fallback: false,
          healthy: false,
        });
      });
  }, []);

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Platform Tag */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
              CareerPilot AI
            </span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              v1.0 Open-Source First
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            Agentic Career Intelligence & ATS Validation System
          </p>
        </div>
      </div>

      {/* Center/Right Status Badges */}
      <div className="flex items-center space-x-3">
        {/* Active Model / Provider Pill */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
          <Cpu className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-400">LLM Mode:</span>
          <span className={`font-medium ${!providerInfo.healthy ? 'text-red-300' : providerInfo.is_proprietary ? 'text-amber-400' : providerInfo.is_fallback ? 'text-emerald-400' : 'text-cyan-400'}`}>
            {providerInfo.primary}
          </span>
          {!providerInfo.healthy && <AlertCircle className="h-3.5 w-3.5 text-red-300" />}
          {providerInfo.is_fallback && (
            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">
              Zero External Quotas
            </span>
          )}
        </div>

        {/* Jury Demo Shortcut */}
        <Link
          to="/demonstrations"
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Jury Demo (Scenarios Aâ€“F)</span>
        </Link>
      </div>
    </header>
  );
};
