import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';

interface CleanCodeReportProps {
  onNavigate: (page: Page) => void;
  results: any;
  code: string;
}

const CleanCodeReport: React.FC<CleanCodeReportProps> = ({ onNavigate, results, code }) => {

  if (!results || !results.clean_report) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary"></div>
        <p className="text-text-secondary font-medium text-lg">Analyzing Clean Code metrics...</p>
        <button
          onClick={() => onNavigate(Page.RESULTS)}
          className="mt-4 px-6 py-2 bg-ui-panels border border-border-color rounded-full text-accent-primary hover:bg-accent-primary/10 transition-all"
        >
          &larr; Back to Results
        </button>
      </div>
    );
  }

  const clean = results.clean_report;
  const score = clean.score ?? 0;
  const grade = clean.grade ?? 'N/A';
  const passed = clean.passed ?? false;
  const issues: any[] = clean.issues || [];
  const metrics = clean.metrics || {};
  const pylintIssues = clean.pylint || [];

  const errorIssues = issues.filter((i: any) => i.sev === 'error');
  const warningIssues = issues.filter((i: any) => i.sev === 'warning');
  const hintIssues = issues.filter((i: any) => i.sev === 'hint');

  const getOverallStatus = () => {
    if (passed) return { text: `Grade ${grade} — Clean`, color: "text-status-success" };
    if (score >= 55) return { text: `Grade ${grade} — Needs Work`, color: "text-status-warning" };
    return { text: `Grade ${grade} — Poor`, color: "text-status-error" };
  };

  const status = getOverallStatus();

  const sevStyles = {
    error: 'bg-status-error/20 text-status-error',
    warning: 'bg-status-warning/20 text-status-warning',
    hint: 'bg-accent-primary/20 text-accent-primary',
  };

  return (
    <div className="flex flex-col gap-8 flex-grow py-8 max-w-7xl mx-auto w-full">
      <div className="flex flex-col gap-2">
        <button
          onClick={() => onNavigate(Page.RESULTS)}
          className="text-accent-primary hover:underline mb-2 flex items-center gap-2 w-fit transition-all"
        >
          &larr; Back to Results
        </button>
        <GradientText as="h1" className="text-4xl font-bold italic tracking-tight">Detailed Report: Clean Code</GradientText>
      </div>

      {/* Score overview */}
      <div className="bg-ui-panels p-6 rounded-xl border border-border-color shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold text-text-primary">
            Score: <span className={status.color}>{score}/100</span>
          </h2>
          <span className={`px-3 py-1 text-sm font-bold rounded-full ${passed ? 'bg-status-success/20 text-status-success' : 'bg-status-error/20 text-status-error'}`}>
            {passed ? 'PASSED' : 'FAILED'}
          </span>
        </div>
        <div className="flex flex-wrap gap-6 text-sm">
          <p className="text-text-secondary">Status: <strong className={status.color}>{status.text}</strong></p>
          <p className="text-text-secondary">MI: <strong>{metrics.maintainability_index ?? 'N/A'}</strong></p>
          <p className="text-text-secondary">Lines: <strong>{metrics.loc ?? 0}</strong></p>
          <p className="text-text-secondary">Logical Lines: <strong>{metrics.lloc ?? 0}</strong></p>
          <p className="text-text-secondary">Max CC: <strong>{metrics.cc_max ?? 0}</strong></p>
          <p className="text-text-secondary">Pylint: <strong>{metrics.pylint_score ?? 'N/A'}/10</strong></p>
        </div>
      </div>

      {/* Key metrics — Maintainability Index, Cyclomatic Complexity, Pylint */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Maintainability Index', value: metrics.maintainability_index ?? 'N/A', suffix: (metrics.maintainability_index !== undefined && metrics.maintainability_index !== null) ? '/100' : '', hint: 'Higher is better (radon mi_visit)' },
          { label: 'Cyclomatic Complexity', value: metrics.cc_max ?? 'N/A', suffix: '', hint: 'Worst function (radon cc_visit)' },
          { label: 'Pylint Score', value: metrics.pylint_score ?? 'N/A', suffix: (metrics.pylint_score !== undefined && metrics.pylint_score !== null) ? '/10' : '', hint: 'Static lint rating' },
        ].map((m: any) => (
          <div key={m.label} className="bg-ui-panels p-5 rounded-xl border border-border-color shadow-md">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{m.label}</p>
            <p className="text-3xl font-bold text-text-primary mt-1">{m.value}<span className="text-base text-text-secondary">{m.suffix}</span></p>
            <p className="text-xs text-text-secondary mt-1">{m.hint}</p>
          </div>
        ))}
      </div>

      {/* Code snippet */}
      <div className="flex flex-col gap-3">
        <h3 className="text-lg font-bold text-text-secondary px-1">Analyzed Snippet</h3>
        <div className="h-64 rounded-xl overflow-hidden border border-border-color shadow-inner">
          <CodeEditor initialCode={code || ""} readOnly={true} />
        </div>
      </div>

      {/* Issues — grouped by severity like SOLID */}
      {issues.length > 0 ? (
        <div className="flex flex-col gap-5">
          <h3 className="text-lg font-bold text-text-secondary px-1">
            Issues ({issues.length})
          </h3>

          {[
            { label: 'Errors', items: errorIssues, sev: 'error' as const },
            { label: 'Warnings', items: warningIssues, sev: 'warning' as const },
            { label: 'Hints', items: hintIssues, sev: 'hint' as const },
          ].filter(g => g.items.length > 0).map(group => (
            <div key={group.label} className="flex flex-col gap-3">
              <h4 className="text-sm font-bold uppercase tracking-wider text-text-secondary flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs ${sevStyles[group.sev]}`}>
                  {group.items.length}
                </span>
                {group.label}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {group.items.map((issue: any, i: number) => (
                  <div key={i} className="bg-ui-panels p-4 rounded-lg border border-border-color">
                    <div className="flex justify-between items-start mb-2">
                      <h5 className="text-sm font-bold text-text-primary">
                        {issue.target ? `${issue.target}` : issue.cat}
                      </h5>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${sevStyles[group.sev]}`}>
                        {issue.sev}
                      </span>
                    </div>
                    <p className="text-sm text-text-secondary mb-2">{issue.msg}</p>
                    <div className="flex gap-3 text-xs text-text-secondary">
                      {issue.line && <span>Line {issue.line}</span>}
                      <span className="text-accent-primary">{issue.id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-ui-panels p-6 rounded-xl border border-border-color text-center">
          <p className="text-status-success text-lg font-bold">No issues found — code is clean!</p>
        </div>
      )}

      {/* Pylint raw */}
      {pylintIssues.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-lg font-bold text-text-secondary px-1">
            Pylint Findings ({pylintIssues.length})
          </h3>
          <div className="bg-ui-panels rounded-xl border border-border-color overflow-hidden">
            {pylintIssues.map((item: any, i: number) => (
              <div key={i} className={`flex items-start gap-3 px-4 py-3 ${i > 0 ? 'border-t border-border-color' : ''}`}>
                <span className="text-xs font-mono text-text-secondary w-8 shrink-0">L{item.line}</span>
                <span className="text-sm text-text-primary flex-1">{item.msg}</span>
                <span className="text-xs text-accent-primary">{item.symbol}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-4">
        <button
          onClick={() => onNavigate(Page.SOLID_REPORT)}
          className="bg-ui-panels text-text-primary font-semibold px-6 py-3 rounded-lg border border-border-color hover:opacity-90 transition-all shadow-md"
        >
          &larr; Previous: SOLID Report
        </button>
      </div>

    </div>
  );
};

export default CleanCodeReport;
