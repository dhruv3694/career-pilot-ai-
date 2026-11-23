import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Cpu,
  FileText,
  Play,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';

interface WorkflowRun {
  run_id: string;
  status: string;
  target_role?: string;
  elapsed_seconds?: number;
  agent_executions?: Array<{ agent_name: string }>;
}

interface ProviderStatus {
  providers?: Record<string, { available?: boolean; model?: string }>;
  active_priority?: string[];
}

const describeError = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);

export const Dashboard: React.FC = () => {
  const [runs, setRuns] = useState<WorkflowRun[] | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const [isRunningAgent, setIsRunningAgent] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const refreshDashboard = useCallback(async () => {
    const errors: string[] = [];
    const [runsResult, providerResult] = await Promise.allSettled([
      api.getAgentRuns(),
      api.getProvidersStatus(),
    ]);

    if (runsResult.status === 'fulfilled') {
      setRuns(runsResult.value.runs ?? []);
    } else {
      setRuns(null);
      errors.push(`Workflow history: ${describeError(runsResult.reason)}`);
    }

    if (providerResult.status === 'fulfilled') {
      setProviderStatus(providerResult.value);
    } else {
      setProviderStatus(null);
      errors.push(`Provider status: ${describeError(providerResult.reason)}`);
    }

    setLoadErrors(errors);
  }, []);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const handleTriggerQuickWorkflow = async () => {
    setIsRunningAgent(true);
    setRunMessage(null);
    setRunError(null);
    try {
      const result = await api.runAgentWorkflow('Software Engineer');
      setRunMessage(
        `Workflow ${result.status ?? 'finished'} (${result.run_id.slice(0, 8)}); ${result.agent_executions?.length ?? 0} agent executions recorded.`,
      );
      await refreshDashboard();
    } catch (error) {
      setRunError(error instanceof Error ? error.message : 'Workflow request failed.');
    } finally {
      setIsRunningAgent(false);
    }
  };

  const providers = providerStatus?.providers ?? {};
  const priority = providerStatus?.active_priority ?? Object.keys(providers);
  const availableProviders = priority
    .filter((name) => providers[name]?.available)
    .map((name) => `${name}${providers[name].model ? ` (${providers[name].model})` : ''}`);

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-8">
      <section className="relative overflow-hidden rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900 p-8">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center space-x-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Career intelligence, backed by evidence</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Welcome to CareerPilot AI
          </h1>
          <p className="text-sm leading-relaxed text-slate-300">
            Analyze a resume with deterministic ATS checks, then explore career
            workflows. Results are shown only when returned by the backend.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              to="/resume-studio"
              className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition-colors hover:bg-indigo-500"
            >
              <FileText className="mr-2 h-4 w-4" />
              Open Resume Studio
            </Link>
            <button
              onClick={handleTriggerQuickWorkflow}
              disabled={isRunningAgent}
              className="inline-flex items-center rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-700 disabled:opacity-50"
            >
              <Play className={`mr-2 h-4 w-4 text-indigo-400 ${isRunningAgent ? 'animate-pulse' : ''}`} />
              {isRunningAgent ? 'Running workflow...' : 'Run Career Workflow'}
            </button>
          </div>
          {runMessage && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/60 p-3 text-xs text-emerald-300">
              {runMessage}
            </div>
          )}
          {runError && (
            <div role="alert" className="rounded-lg border border-red-500/30 bg-red-950/50 p-3 text-xs text-red-200">
              Workflow did not complete: {runError}
            </div>
          )}
        </div>
      </section>

      {loadErrors.length > 0 && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-950/30 p-4 text-sm text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">Some dashboard data could not be loaded.</p>
            <ul className="mt-1 list-inside list-disc text-amber-100/80">
              {loadErrors.map((error) => <li key={error}>{error}</li>)}
            </ul>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Bot className="h-4 w-4 text-indigo-400" />
              Workflow activity
            </h2>
            <span className="text-xs text-slate-500">Backend run history</span>
          </div>
          {runs === null ? (
            <p className="text-sm text-slate-500">Workflow history unavailable.</p>
          ) : (
            <>
              <p className="text-2xl font-bold text-white">{runs.length}</p>
              <p className="text-xs text-slate-500">Recorded runs in this server session</p>
              {runs.length > 0 && (
                <ul className="space-y-2 border-t border-slate-800 pt-3">
                  {runs.slice(-3).reverse().map((run) => (
                    <li key={run.run_id} className="flex items-center justify-between gap-3 text-xs">
                      <span className="truncate text-slate-300">{run.target_role || run.run_id}</span>
                      <span className="shrink-0 text-slate-500">
                        {run.status} Â· {run.agent_executions?.length ?? 0} agents
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>

        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Cpu className="h-4 w-4 text-cyan-400" />
            Model provider availability
          </h2>
          {providerStatus === null ? (
            <p className="text-sm text-slate-500">Provider status unavailable.</p>
          ) : availableProviders.length > 0 ? (
            <>
              <p className="text-lg font-semibold text-cyan-300">{availableProviders.length} provider(s) available</p>
              <p className="text-xs text-slate-400">{availableProviders.join(', ')}</p>
            </>
          ) : (
            <>
              <p className="flex items-center gap-2 text-sm font-medium text-emerald-300">
                <ShieldCheck className="h-4 w-4" />
                No remote provider available
              </p>
              <p className="text-xs text-slate-400">
                The deterministic local fallback keeps supported workflows usable without paid API calls.
              </p>
            </>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="font-semibold text-white">Continue</h2>
        <p className="mt-1 text-sm text-slate-400">
          Resume parsing and structured profile review are available in the current frontend.
        </p>
        <Link to="/resume-studio" className="mt-4 inline-flex items-center text-sm font-medium text-indigo-400 hover:text-indigo-300">
          Go to Resume Studio <ArrowRight className="ml-1 h-4 w-4" />
        </Link>
      </section>
    </div>
  );
};
