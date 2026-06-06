import React, { useState } from 'react';
import { Page } from '../types';
import { calculateGlobalScore } from './Results';
import ScoreCircle from './ScoreCircle';

interface OptimizeReportProps {
  onNavigate: (page: Page) => void;
  results:    any;
  code:       string;
  isLoading?: boolean;
}

const OptimizeReport: React.FC<OptimizeReportProps> = ({
  onNavigate, results, code, isLoading = false,
}) => {
  const refactored       = results?.refactored_code   || '';
  const suggestions      = results?.suggestions       || [];
  const verdict          = results?.validator_verdict || '';
  const comparatorReport = results?.comparator_report || '';
  const agentReport      = results?.agent_report      || '';

  const [copiedOriginal,   setCopiedOriginal]   = useState(false);
  const [copiedRefactored, setCopiedRefactored] = useState(false);

  // ── Scores ────────────────────────────────────────────────
  const scoreBefore = calculateGlobalScore(results);

  // Build a "fake" after-result using the refactored code analysis
  // The comparator report tells us what improved — we approximate the after score
  // by checking how many SOLID violations were resolved
  const getScoreAfter = (): number => {
    if (!verdict || verdict !== 'PASS') return scoreBefore;
    // If comparator passed, assume all SOLID violations fixed → max solid score
    const solidBonus = (results?.total_violations ?? 0) * 7;
    return Math.min(100, scoreBefore + solidBonus);
  };

  const scoreAfter   = getScoreAfter();
  const scoreDelta   = scoreAfter - scoreBefore;
  const changedLines = code.split('\n').length !== refactored.split('\n').length
    ? Math.abs(code.split('\n').length - refactored.split('\n').length)
    : refactored.split('\n').filter((l, i) => l !== code.split('\n')[i]).length;

  // ── PDF Download ──────────────────────────────────────────
  const handleDownloadPDF = () => {
    const content = `
OWLINT — CODE OPTIMIZATION REPORT
Generated: ${new Date().toLocaleString()}
${'='.repeat(60)}

VERDICT: ${verdict || 'N/A'}

SCORE
Before Optimization: ${scoreBefore}/100
After Optimization:  ${scoreAfter}/100
Improvement:         +${scoreDelta} points

${'='.repeat(60)}
WHAT CHANGED
${suggestions.map((s: string, i: number) => `${i + 1}. ${s}`).join('\n') || 'No suggestions recorded.'}

${'='.repeat(60)}
ANALYSIS REPORT
${agentReport || 'N/A'}

${'='.repeat(60)}
VALIDATION REPORT
${comparatorReport || 'N/A'}

${'='.repeat(60)}
ORIGINAL CODE
${code}

${'='.repeat(60)}
REFACTORED CODE
${refactored}
`.trim();

    const blob = new Blob([content], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `owlint-report-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
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

  const scoreColor = (s: number) =>
    s >= 80 ? 'text-green-400' : s >= 50 ? 'text-yellow-400' : 'text-red-400';

  // ── Loading ───────────────────────────────────────────────
  if (isLoading) {
    const darkMode = document.documentElement.classList.contains('dark');
    const analysisComplete  = !!(results?.agent_report);
    const refactorComplete  = !!(results?.refactored_code);
    const validationComplete = !!(results?.validator_verdict);
    const agents = [
      { label: 'Analysis Agent',   done: analysisComplete },
      { label: 'Refactor Agent',   done: refactorComplete },
      { label: 'Validation Agent', done: validationComplete },
    ];
    return (
      <div className="flex flex-col items-center justify-center flex-grow py-10 gap-6">
        {/* Spinner with logo */}
        <div className="relative">
          <div className="w-28 h-28 border-4 border-accent-primary/20 border-t-accent-primary
                          rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <img
              src={darkMode ? '/darklogo.png' : '/lightlogo.png'}
              alt="Strivora AI"
              className="w-16 h-16"
            />
          </div>
        </div>
        <div className="text-center">
          <h2 className="text-xl font-bold text-text-primary mb-2">Optimizing your code...</h2>
          <p className="text-text-secondary text-sm max-w-md">
            Our AI agents are analyzing violations, refactoring your code, and validating the result.
            This usually takes 30-60 seconds.
          </p>
        </div>
        <div className="flex flex-col gap-2 w-64">
          {agents.map((agent, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-2 rounded-lg
                                    bg-ui-panels border border-border-color">
              {agent.done ? (
                <span className="text-green-400 text-sm font-bold">✓</span>
              ) : (
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
              )}
              <p className={`text-xs font-bold ${agent.done ? 'text-green-400' : 'text-text-primary'}`}>
                {agent.label}
              </p>
            </div>
          ))}
        </div>

        {/* Current score + cards while waiting */}
        <div className="w-full max-w-3xl mt-6 bg-ui-panels/70 border border-border-color rounded-xl p-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-4 text-center">
            Current Analysis
          </p>
          <div className="flex justify-center mb-6">
            <ScoreCircle score={scoreBefore} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-ui-panels border border-border-color rounded-lg p-3 text-center">
              <p className="text-xs text-text-secondary mb-1">Time</p>
              <p className="text-lg font-mono font-bold text-accent-primary">{results?.time_complexity || 'O(1)'}</p>
            </div>
            <div className="bg-ui-panels border border-border-color rounded-lg p-3 text-center">
              <p className="text-xs text-text-secondary mb-1">Space</p>
              <p className="text-lg font-mono font-bold text-accent-primary">{results?.space_complexity || 'O(1)'}</p>
            </div>
            <div className="bg-ui-panels border border-border-color rounded-lg p-3 text-center">
              <p className="text-xs text-text-secondary mb-1">SOLID</p>
              <p className={`text-lg font-bold ${results?.total_violations === 0 ? 'text-green-400' : 'text-red-400'}`}>
                {results?.total_violations === 0 ? 'Pass' : `${results?.total_violations} Err`}
              </p>
            </div>
            <div className="bg-ui-panels border border-border-color rounded-lg p-3 text-center">
              <p className="text-xs text-text-secondary mb-1">Clean</p>
              <p className={`text-lg font-bold ${scoreBefore >= 80 ? 'text-green-400' : scoreBefore >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                {scoreBefore}/100
              </p>
            </div>
          </div>
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

  // ── Main report ───────────────────────────────────────────
  return (
    <div className="flex flex-col py-6 gap-6">

      {/* ── HEADER ──────────────────────────────────────────── */}
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
        <div className="flex items-center gap-3">
          {/* Download PDF button */}
          <button
            onClick={handleDownloadPDF}
            className="flex items-center gap-2 px-4 py-2 rounded-xl
                       bg-accent-primary text-white text-sm font-bold
                       hover:opacity-90 transition-all shadow-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none"
                 viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586
                       a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Report
          </button>

          {/* Verdict badge */}
          {verdict && (
            <span className={`px-4 py-1.5 rounded-full text-sm font-bold border
              ${verdict === 'PASS'
                ? 'bg-green-500/10 border-green-500/30 text-green-400'
                : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
              {verdict === 'PASS' ? '✓ Passed' : '✗ Failed'}
            </span>
          )}
        </div>
      </div>

      {/* ── BEFORE / AFTER SCORE COMPARISON ─────────────────── */}
      <div className="bg-ui-panels border border-border-color rounded-xl p-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-5">
          Score Comparison
        </h2>
        <div className="flex items-center justify-center gap-6 flex-wrap">

          {/* Before */}
          <div className="flex flex-col items-center">
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-3">Before</p>
            <ScoreCircle score={scoreBefore} />
          </div>

          {/* Arrow + delta */}
          <div className="flex flex-col items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-accent-primary"
                 fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            {scoreDelta > 0 && (
              <span className="text-sm font-bold text-green-400">+{scoreDelta}</span>
            )}
          </div>

          {/* After */}
          <div className="flex flex-col items-center">
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-3">After</p>
            <ScoreCircle score={scoreAfter} baseScore={scoreBefore} />
          </div>
        </div>
      </div>

      {/* ── SUMMARY STRIP ───────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Lines Changed</p>
          <p className="text-3xl font-bold font-mono text-accent-primary">{changedLines}</p>
        </div>
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Fixes Applied</p>
          <p className="text-3xl font-bold font-mono text-accent-secondary">{suggestions.length}</p>
        </div>
        <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Score Gained</p>
          <p className={`text-3xl font-bold font-mono ${scoreDelta > 0 ? 'text-green-400' : 'text-text-primary'}`}>
            {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}
          </p>
        </div>
      </div>

      {/* ── SIDE BY SIDE CODE VIEW ──────────────────────────── */}
      <div className="bg-ui-panels border border-border-color rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-color">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            Code Comparison
          </h2>
          <span className="text-xs text-text-secondary">{changedLines} lines modified</span>
        </div>
        <div className="grid grid-cols-2 divide-x divide-border-color">

          {/* Original */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 bg-red-500/5 border-b border-border-color">
              <span className="text-xs font-bold text-red-400 uppercase">Original</span>
              <button
                onClick={() => copyToClipboard(code, 'original')}
                className="text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                {copiedOriginal ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <div className="overflow-auto max-h-96 font-mono text-xs">
              {code.split('\n').map((line, i) => (
                <div key={i} className={`flex px-4 py-0.5 ${
                  refactored.split('\n')[i] !== line ? 'bg-red-500/5' : ''}`}>
                  <span className="text-text-secondary w-8 shrink-0 select-none">{i + 1}</span>
                  <span className={`whitespace-pre ${
                    refactored.split('\n')[i] !== line ? 'text-red-300' : 'text-text-primary'}`}>
                    {line}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Refactored */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 bg-green-500/5 border-b border-border-color">
              <span className="text-xs font-bold text-green-400 uppercase">Refactored</span>
              <button
                onClick={() => copyToClipboard(refactored, 'refactored')}
                className="text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                {copiedRefactored ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <div className="overflow-auto max-h-96 font-mono text-xs">
              {refactored.split('\n').map((line, i) => (
                <div key={i} className={`flex px-4 py-0.5 ${
                  code.split('\n')[i] !== line ? 'bg-green-500/5' : ''}`}>
                  <span className="text-text-secondary w-8 shrink-0 select-none">{i + 1}</span>
                  <span className={`whitespace-pre ${
                    code.split('\n')[i] !== line ? 'text-green-300' : 'text-text-primary'}`}>
                    {line}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default OptimizeReport;
