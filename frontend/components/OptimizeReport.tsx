import React, { useState, useEffect } from 'react';
import { Page } from '../types';

interface DiffLine {
  type: 'same' | 'added' | 'removed' | 'changed';
  orig: string;
  ref: string;
  line: number;
}

interface ChangeCard {
  id: number;
  lineNumber: number;
  type: 'added' | 'removed' | 'changed';
  before: string;
  after: string;
}

interface OptimizeReportProps {
  onNavigate: (page: Page) => void;
  results: any;
  code: string;
  isLoading?: boolean;
}

const OptimizeReport: React.FC<OptimizeReportProps> = ({ onNavigate, results, code, isLoading = false }) => {
  const refactored      = results?.refactored_code || '';
  const suggestions     = results?.suggestions || [];
  const verdict         = results?.validator_verdict || '';
  const comparatorReport = results?.comparator_report || '';
  const agentReport     = results?.agent_report || '';

  const [currentCode, setCurrentCode] = useState(refactored || code);
  const [rolledBackIds, setRolledBackIds] = useState<Set<number>>(new Set());
  const [copiedOriginal, setCopiedOriginal]     = useState(false);
  const [copiedRefactored, setCopiedRefactored] = useState(false);

  useEffect(() => {
    setCurrentCode(refactored || code);
    setRolledBackIds(new Set());
  }, [refactored]);

  // ── Loading screen ────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow py-20 gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-accent-primary/20 border-t-accent-primary
                          rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center text-2xl">🦉</div>
        </div>
        <div className="text-center">
          <h2 className="text-xl font-bold text-text-primary mb-2">Optimizing your code...</h2>
          <p className="text-text-secondary text-sm max-w-md">
            Our AI agents are analyzing violations, refactoring your code, and validating the result.
            This usually takes 30–60 seconds.
          </p>
        </div>
        <div className="flex flex-col gap-2 w-64">
          {[
            { label: 'Analysis Agent',   desc: 'Detecting violations...' },
            { label: 'Refactor Agent',   desc: 'Rewriting code...' },
            { label: 'Validation Agent', desc: 'Verifying output...' },
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-2 rounded-lg
                                    bg-ui-panels border border-border-color">
              <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
              <div>
                <p className="text-xs font-bold text-text-primary">{step.label}</p>
                <p className="text-xs text-text-secondary">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <button
          onClick={() => onNavigate(Page.DASHBOARD)}
          className="text-sm text-text-secondary hover:text-text-primary transition-colors mt-4"
        >
          ← Back to editor
        </button>
      </div>
    );
  }

  // ── Diff calculation ──────────────────────────────────────
  const getDiff = (): DiffLine[] => {
    const originalLines  = code.split('\n');
    const refactoredLines = refactored.split('\n');
    const maxLen = Math.max(originalLines.length, refactoredLines.length);
    return Array.from({ length: maxLen }, (_, i) => {
      const orig = originalLines[i] ?? '';
      const ref  = refactoredLines[i] ?? '';
      if (orig === ref)  return { type: 'same'    as const, orig, ref, line: i + 1 };
      if (!orig)         return { type: 'added'   as const, orig: '', ref, line: i + 1 };
      if (!ref)          return { type: 'removed' as const, orig, ref: '', line: i + 1 };
      return             { type: 'changed' as const, orig, ref, line: i + 1 };
    });
  };

  const diff = getDiff();
  const changedLines = diff.filter(d => d.type !== 'same');

  // ── Build change cards ────────────────────────────────────
  const changeCards: ChangeCard[] = changedLines.map((d, i) => ({
    id: i,
    lineNumber: d.line,
    type: d.type as 'added' | 'removed' | 'changed',
    before: d.orig,
    after: d.ref,
  }));

  // ── Rollback a single change card ─────────────────────────
  const rollbackChange = (card: ChangeCard) => {
    const lines = currentCode.split('\n');
    if (card.type === 'added') {
      // Remove the added line
      lines.splice(card.lineNumber - 1, 1);
    } else {
      // Restore original line
      lines[card.lineNumber - 1] = card.before;
    }
    setCurrentCode(lines.join('\n'));
    setRolledBackIds(prev => new Set([...prev, card.id]));
  };

  // ── Undo rollback ─────────────────────────────────────────
  const undoRollback = (card: ChangeCard) => {
    const lines = currentCode.split('\n');
    lines[card.lineNumber - 1] = card.after;
    setCurrentCode(lines.join('\n'));
    setRolledBackIds(prev => {
      const next = new Set(prev);
      next.delete(card.id);
      return next;
    });
  };

  const copyToClipboard = (text: string, type: 'original' | 'refactored') => {
    navigator.clipboard.writeText(text);
    if (type === 'original') {
      setCopiedOriginal(true);
      setTimeout(() => setCopiedOriginal(false), 2000);
    } else {
      setCopiedRefactored(true);
      setTimeout(() => setCopiedRefactored(false), 2000);
    }
  };

  const typeLabel = (type: string) => {
    if (type === 'added')   return { label: 'Added',   color: 'text-green-400',  bg: 'bg-green-500/10 border-green-500/20' };
    if (type === 'removed') return { label: 'Removed', color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/20' };
    return                         { label: 'Modified', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20' };
  };

  return (
    <div className="flex flex-col py-6 gap-6">

      {/* ── HEADER ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate(Page.DASHBOARD)}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-text-primary">Optimization Report</h1>
        </div>
        {verdict && (
          <span className={`px-4 py-1.5 rounded-full text-sm font-bold border
            ${verdict === 'PASS'
              ? 'bg-green-500/10 border-green-500/30 text-green-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
            {verdict === 'PASS' ? '✓ Optimization Passed' : '✗ Optimization Failed'}
          </span>
        )}
      </div>

      {/* ── SUMMARY STRIP ─────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Lines Changed</p>
          <p className="text-3xl font-bold font-mono text-accent-primary">{changedLines.length}</p>
        </div>
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Suggestions Applied</p>
          <p className="text-3xl font-bold font-mono text-accent-secondary">{suggestions.length}</p>
        </div>
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Rolled Back</p>
          <p className="text-3xl font-bold font-mono text-text-primary">{rolledBackIds.size} / {changeCards.length}</p>
        </div>
      </div>

      {/* ── SUGGESTIONS ───────────────────────────────────────── */}
      {suggestions.length > 0 && (
        <div className="bg-ui-panels border border-border-color rounded-xl p-5">
          <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-3">
            What Changed
          </h2>
          <ul className="space-y-2">
            {suggestions.map((s: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-text-primary">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── CHANGE CARDS (rollback per line) ──────────────────── */}
      {changeCards.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary">
              Changes — Click to Rollback
            </h2>
            <span className="text-xs text-text-secondary">
              {rolledBackIds.size} of {changeCards.length} rolled back
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {changeCards.map((card) => {
              const isRolledBack = rolledBackIds.has(card.id);
              const { label, color, bg } = typeLabel(card.type);
              return (
                <div
                  key={card.id}
                  className={`rounded-xl border p-4 transition-all duration-200
                    ${isRolledBack ? 'opacity-50 bg-ui-panels border-border-color' : bg}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${bg} ${color}`}>
                        {label}
                      </span>
                      <span className="text-xs text-text-secondary font-mono">Line {card.lineNumber}</span>
                      {isRolledBack && (
                        <span className="text-xs text-text-secondary italic">rolled back</span>
                      )}
                    </div>
                    <button
                      onClick={() => isRolledBack ? undoRollback(card) : rollbackChange(card)}
                      className={`text-xs font-bold px-3 py-1 rounded-lg border transition-all
                        ${isRolledBack
                          ? 'border-accent-primary/30 text-accent-primary hover:bg-accent-primary/10'
                          : 'border-red-500/30 text-red-400 hover:bg-red-500/10'}`}
                    >
                      {isRolledBack ? 'Undo' : 'Rollback'}
                    </button>
                  </div>

                  {/* Before / After code */}
                  <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                    {card.before && (
                      <div className="bg-red-500/10 rounded-lg px-3 py-2">
                        <p className="text-red-400/60 text-xs mb-1">before</p>
                        <p className="text-red-300 whitespace-pre">{card.before}</p>
                      </div>
                    )}
                    {card.after && (
                      <div className="bg-green-500/10 rounded-lg px-3 py-2">
                        <p className="text-green-400/60 text-xs mb-1">after</p>
                        <p className="text-green-300 whitespace-pre">{card.after}</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── SIDE BY SIDE CODE VIEW ────────────────────────────── */}
      <div className="bg-ui-panels border border-border-color rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-color">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            Code Comparison
          </h2>
          <span className="text-xs text-text-secondary">{changedLines.length} lines modified</span>
        </div>
        <div className="grid grid-cols-2 divide-x divide-border-color">
          {/* Original */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 bg-red-500/5 border-b border-border-color">
              <span className="text-xs font-bold text-red-400 uppercase tracking-wider">Original</span>
              <button onClick={() => copyToClipboard(code, 'original')}
                      className="text-xs text-text-secondary hover:text-text-primary transition-colors">
                {copiedOriginal ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <div className="overflow-auto max-h-96 font-mono text-xs">
              {diff.map((d, i) => (
                <div key={i} className={`flex px-4 py-0.5
                  ${d.type === 'removed' ? 'bg-red-500/10' : d.type === 'changed' ? 'bg-red-500/5' : ''}`}>
                  <span className="text-text-secondary w-8 shrink-0 select-none">{d.line}</span>
                  <span className={`whitespace-pre ${d.type === 'removed' ? 'text-red-400' : d.type === 'changed' ? 'text-orange-300' : 'text-text-primary'}`}>
                    {d.orig}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Current (with rollbacks applied) */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 bg-green-500/5 border-b border-border-color">
              <span className="text-xs font-bold text-green-400 uppercase tracking-wider">
                Refactored {rolledBackIds.size > 0 ? `(${rolledBackIds.size} rolled back)` : ''}
              </span>
              <button onClick={() => copyToClipboard(currentCode, 'refactored')}
                      className="text-xs text-text-secondary hover:text-text-primary transition-colors">
                {copiedRefactored ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <div className="overflow-auto max-h-96 font-mono text-xs">
              {currentCode.split('\n').map((line, i) => (
                <div key={i} className="flex px-4 py-0.5">
                  <span className="text-text-secondary w-8 shrink-0 select-none">{i + 1}</span>
                  <span className="whitespace-pre text-text-primary">{line}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── AGENT REPORT ──────────────────────────────────────── */}
      {agentReport && (
        <div className="bg-ui-panels border border-border-color rounded-xl p-5">
          <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-3">
            Analysis Agent Report
          </h2>
          <pre className="text-xs text-text-primary whitespace-pre-wrap font-mono leading-relaxed">
            {agentReport}
          </pre>
        </div>
      )}

      {/* ── COMPARATOR REPORT ─────────────────────────────────── */}
      {comparatorReport && (
        <div className={`border rounded-xl p-5
          ${comparatorReport.includes('PASS')
            ? 'bg-green-500/5 border-green-500/20'
            : 'bg-red-500/5 border-red-500/20'}`}>
          <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-3">
            Validation Report
          </h2>
          <pre className="text-xs text-text-primary whitespace-pre-wrap font-mono leading-relaxed">
            {comparatorReport}
          </pre>
        </div>
      )}

    </div>
  );
};

export default OptimizeReport;
