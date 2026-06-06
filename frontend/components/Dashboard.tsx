import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';

interface AnalysisResult {
  time_complexity: string;
  space_complexity: string;
  total_violations: number;
  solid_report: Record<string, { status: string; reason: string; suggestion: string }>;
  clean_report: {
    score?: number;
    grade?: string;
    passed?: boolean;
    issues?: any[];
    metrics?: { maintainability_index?: number; loc?: number; lloc?: number; comments?: number; cc_max?: number };
    pylint?: any[];
  };
}

interface DashboardProps {
  onNavigate: (page: Page) => void;
  code: string;
  onCodeChange: (newCode: string) => void;
  analysisResult: AnalysisResult;
  language: 'python' | 'java';
  setLanguage: (lang: 'python' | 'java') => void;
  onAnalyze: () => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

export const MODEL_OPTIONS = [
  { value: 'llama-3.1-8b',  label: 'Llama 3.1 8B',  desc: 'Fast & efficient' },
  { value: 'llama-3.3-70b', label: 'Llama 3.3 70B', desc: 'Most accurate · 128k ctx' },
];

const statusBg = (status: string) => {
  if (status === 'Pass')      return 'bg-green-500/10 border-green-500/30';
  if (status === 'Violation') return 'bg-red-500/10 border-red-500/30';
  return 'bg-yellow-500/10 border-yellow-500/30';
};

const statusDot = (status: string) => {
  if (status === 'Pass')      return 'bg-green-400';
  if (status === 'Violation') return 'bg-red-400';
  return 'bg-yellow-400';
};

const statusText = (status: string) => {
  if (status === 'Pass')      return 'text-green-400';
  if (status === 'Violation') return 'text-red-400';
  return 'text-yellow-400';
};

const complexityColor = (c: string) => {
  if (!c) return 'text-accent-primary';
  if (c.includes('1') || c.includes('log')) return 'text-green-400';
  if (c.includes('2^') || c.includes('n!')) return 'text-red-400';
  if (c.includes('^2') || c.includes('^3')) return 'text-orange-400';
  return 'text-accent-primary';
};

interface CardProps {
  title: string;
  value: string;
  sub?: string;
  status?: string;
  onClick: () => void;
  valueClass?: string;
}

const AnalysisCard: React.FC<CardProps> = ({ title, value, sub, status, onClick, valueClass }) => (
  <button
    onClick={onClick}
    className={`
      w-full text-left p-4 rounded-xl border transition-all duration-200
      hover:scale-[1.02] hover:shadow-lg active:scale-[0.99]
      bg-ui-panels group
      ${status ? statusBg(status) : 'border-border-color hover:border-accent-primary/50'}
    `}
  >
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{title}</span>
      {status && (
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${statusDot(status)}`} />
          <span className={`text-xs font-bold ${statusText(status)}`}>{status}</span>
        </span>
      )}
    </div>
    <div className={`text-2xl font-mono font-bold ${valueClass ?? 'text-text-primary'}`}>{value}</div>
    {sub && <p className="text-xs text-text-secondary mt-1 truncate">{sub}</p>}
    <p className="text-xs text-accent-primary mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
      View full report →
    </p>
  </button>
);

const Dashboard: React.FC<DashboardProps> = ({
  onNavigate, code, onCodeChange, analysisResult,
  onAnalyze, language, setLanguage, selectedModel, setSelectedModel,
}) => {
  const { time_complexity, space_complexity, total_violations, solid_report, clean_report } = analysisResult;
  const cleanScore = clean_report?.score ?? 0;
  const cleanGrade = clean_report?.grade ?? 'N/A';
  const cleanIssues: any[] = clean_report?.issues || [];
  const mi = clean_report?.metrics?.maintainability_index;
  const displayScore = cleanScore;
  const cleanIssueCount = cleanIssues.length;
  const scoreStatus  = (clean_report?.passed) ? 'Pass' : cleanIssueCount > 0 ? 'Violation' : 'Warning';

  return (
    <div className="flex flex-col h-full py-4 gap-4">

      {/* ── TOP BAR ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-text-primary">Code Analysis</h2>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-bold border
            ${total_violations > 0
              ? 'bg-red-500/10 border-red-500/30 text-red-400'
              : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
            {total_violations > 0 ? `${total_violations} violation${total_violations > 1 ? 's' : ''}` : 'All clear'}
          </span>
          <button
            onClick={() => onNavigate(Page.RESULTS)}
            className="px-4 py-1.5 rounded-lg bg-accent-primary
                       text-white text-sm font-bold
                       hover:opacity-90 transition-all shadow-sm"
          >
            View Full Results
          </button>
        </div>
      </div>

      {/* ── MAIN SPLIT ──────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row gap-4 flex-grow min-h-0">

        {/* LEFT — Editor + model selector + optimize button */}
        <div className="lg:w-1/2 flex flex-col gap-3 min-h-0">

          {/* Editor */}
          <div className="flex-grow border border-border-color rounded-xl overflow-hidden shadow-sm min-h-[400px] lg:min-h-0">
            <CodeEditor value={code} onChange={onCodeChange} language={language} />
          </div>

          {/* Model selector + Optimize button row */}
          <div className="flex gap-3 items-stretch">

            {/* Model selector card */}
            <div className="flex flex-col gap-1 bg-ui-panels border border-border-color rounded-xl px-4 py-3 min-w-[200px]">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                AI Model
              </span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-transparent text-sm font-bold text-text-primary
                           outline-none cursor-pointer"
              >
                {MODEL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <span className="text-xs text-text-secondary">
                {MODEL_OPTIONS.find(o => o.value === selectedModel)?.desc}
              </span>
            </div>

            {/* Optimize button */}
            <button
              onClick={onAnalyze}
              className="flex-1 bg-gradient-to-r from-accent-primary to-accent-secondary
                         text-white font-bold text-base px-6 py-3 rounded-xl
                         hover:opacity-90 transition-all shadow-lg hover:shadow-xl
                         hover:scale-[1.005] active:scale-[0.99]
                         uppercase tracking-widest flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none"
                   viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Optimize Code
            </button>
          </div>
        </div>

        {/* RIGHT — Live analysis cards */}
        <div className="lg:w-1/2 flex flex-col gap-3 overflow-y-auto pr-1">

          {/* Complexity row */}
          <div className="grid grid-cols-2 gap-3">
            <AnalysisCard
              title="Time Complexity"
              value={time_complexity || 'O(1)'}
              sub="Real-time estimate"
              onClick={() => onNavigate(Page.TIME_COMPLEXITY_REPORT)}
              valueClass={complexityColor(time_complexity)}
            />
            <AnalysisCard
              title="Space Complexity"
              value={space_complexity || 'O(1)'}
              sub="Real-time estimate"
              onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)}
              valueClass={complexityColor(space_complexity)}
            />
          </div>

          {/* Clean Code card */}
          <button
            onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)}
            className={`w-full text-left p-4 rounded-xl border transition-all duration-200
                       hover:scale-[1.02] hover:shadow-lg active:scale-[0.99]
                       bg-ui-panels ${statusBg(scoreStatus)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Clean Code</span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full border
                ${scoreStatus === 'Pass'
                  ? 'bg-green-500/10 border-green-500/30 text-green-400'
                  : scoreStatus === 'Warning'
                  ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                {cleanIssueCount === 0 ? 'All Pass' : `${cleanIssueCount} Issues`}
              </span>
            </div>
            <div className={`text-2xl font-mono font-bold ${displayScore >= 80 ? 'text-green-400' : displayScore >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
              {displayScore}/100
            </div>
            <p className="text-xs text-text-secondary mt-1">
              Grade: {cleanGrade} · MI: {mi !== undefined ? Math.round(mi) : 'N/A'}
            </p>

            {cleanIssueCount > 0 && (
              <div className="mt-3 space-y-1">
                {cleanIssues.slice(0, 2).map((issue: any, i: number) => (
                  <p key={i} className="text-xs text-text-secondary truncate">
                    <span className={`font-bold ${issue.sev === 'error' ? 'text-red-400' : issue.sev === 'warning' ? 'text-yellow-400' : 'text-text-secondary'}`}>
                      {issue.sev === 'error' ? 'E' : issue.sev === 'warning' ? 'W' : 'H'}:
                    </span>{' '}
                    {issue.msg}
                  </p>
                ))}
                {cleanIssueCount > 2 && (
                  <p className="text-xs text-accent-primary">+{cleanIssueCount - 2} more →</p>
                )}
              </div>
            )}
          </button>

          {/* SOLID card */}
          <button
            onClick={() => onNavigate(Page.SOLID_REPORT)}
            className="w-full text-left p-4 rounded-xl border border-border-color
                       bg-ui-panels hover:border-accent-primary/50 hover:scale-[1.01]
                       transition-all duration-200 hover:shadow-lg active:scale-[0.99]"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                SOLID Principles
              </span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full border
                ${total_violations === 0
                  ? 'bg-green-500/10 border-green-500/30 text-green-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                {total_violations === 0 ? 'All Pass' : `${total_violations} Violations`}
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {['S', 'O', 'L', 'I', 'D'].map((key) => {
                const principle = solid_report?.[key];
                const st = principle?.status ?? 'Pending';
                return (
                  <div key={key}
                       className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold
                         ${st === 'Pass'
                           ? 'bg-green-500/10 border-green-500/30 text-green-400'
                           : st === 'Violation'
                           ? 'bg-red-500/10 border-red-500/30 text-red-400'
                           : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${statusDot(st)}`} />
                    {key}
                  </div>
                );
              })}
            </div>

            {total_violations > 0 && (
              <div className="mt-3 space-y-1">
                {['S', 'O', 'L', 'I', 'D']
                  .filter(k => solid_report?.[k]?.status === 'Violation')
                  .slice(0, 2)
                  .map(k => (
                    <p key={k} className="text-xs text-text-secondary truncate">
                      <span className="text-red-400 font-bold">{k}:</span>{' '}
                      {solid_report[k].reason}
                    </p>
                  ))}
                {total_violations > 2 && (
                  <p className="text-xs text-accent-primary">+{total_violations - 2} more →</p>
                )}
              </div>
            )}
          </button>

        </div>
      </div>
    </div>
  );
};

export default Dashboard;
