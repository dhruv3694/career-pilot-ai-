import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  CheckCircle2,
  Briefcase,
  GitCompare,
  Milestone,
  MessagesSquare,
  CalendarDays,
  Network,
  Database,
  Sliders,
  Sparkles,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  highlight?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/resume-studio', label: 'Resume & ATS Studio', icon: FileText },
  { to: '/jobs', label: 'Job Explorer', icon: Briefcase },
  { to: '/matching', label: 'Job Match & Tailoring', icon: GitCompare },
  { to: '/interview', label: 'Interview Lab', icon: MessagesSquare },
  { to: '/roadmap', label: 'Career Roadmap', icon: Milestone },
  { to: '/events', label: 'Career Fairs & Events', icon: CalendarDays },
  { to: '/agents', label: 'Agent Control Center', icon: Network, badge: 'LangGraph' },
  { to: '/settings', label: 'Settings & Privacy', icon: Sliders },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 flex flex-col justify-between shrink-0">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Core Workflows
        </div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30'
                  : item.highlight
                  ? 'text-violet-300 hover:bg-violet-950/40 hover:text-violet-200 border border-violet-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <div className="flex items-center space-x-3">
              <item.icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </div>
            {item.badge && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                {item.badge}
              </span>
            )}
            {item.highlight && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 font-semibold">
                Exam
              </span>
            )}
          </NavLink>
        ))}
      </div>

      <div className="p-4 border-t border-slate-800 text-xs text-slate-400 space-y-2">
        <div className="flex items-center justify-between">
          <span>Multi-Agent StateGraph</span>
          <span className="flex items-center text-slate-300 font-medium">
            Configured
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>MCP Server</span>
          <span>13 Tools Ready</span>
        </div>
      </div>
    </aside>
  );
};
