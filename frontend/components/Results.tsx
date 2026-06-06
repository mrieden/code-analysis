import React from 'react';
import { Page } from '../types';
import ScoreCircle from './ScoreCircle';
import { MODEL_OPTIONS } from './Dashboard';

interface ResultsProps {
  onNavigate:      (page: Page) => void;
  results:         any;
  code:            string;
  selectedModel:   string;
  setSelectedModel:(m: string) => void;
  onAnalyze:       () => void;
}

// ── Shared score calculator — same formula used in Dashboard ──
export const calculateGlobalScore = (analysisData: any): number => {
  if (!analysisData || analysisData.error) return 0;

  const clean = analysisData.clean_report || {};
  // Use the score directly from the analyzer (0-100)
  const cleanScore = clean.score ?? 0;
  // Normalize to 40 points max for clean code contribution
  const cleanPts = Math.round((cleanScore / 100) * 40);

  const solid      = analysisData.solid_report || {};
  const solidScore = ['S','O','L','I','D'].reduce(
    (acc, key) => acc + (solid[key]?.status === 'Pass' ? 7 : 0), 0
  );

  const timeValue  = analysisData.time_complexity || 'O(1)';
  const timeScore  = (timeValue === 'O(1)' || timeValue === 'O(n)') ? 15 : 7;
  const spaceScore = analysisData.space_complexity === 'O(1)' ? 10 : 7;

  return Math.min(100, Math.round(cleanPts + solidScore + timeScore + spaceScore));
};

const Results: React.FC<ResultsProps> = ({
  onNavigate, results: analysisData, code,
  selectedModel, setSelectedModel, onAnalyze,
}) => {
  const globalScore = calculateGlobalScore(analysisData);

  const solid = analysisData?.solid_report || {};
  const clean = analysisData?.clean_report || {};
  const cleanScore = clean.score ?? 0;
  const cleanGrade = clean.grade ?? 'N/A';
  const cleanPassed = clean.passed ?? false;

  return (
    <div className="flex flex-col items-center justify-center flex-grow py-8 gap-8 max-w-4xl mx-auto w-full">
      <div className="w-full bg-ui-panels/70 p-8 rounded-lg border border-border-color shadow-2xl">

        <button
          onClick={() => onNavigate(Page.DASHBOARD)}
          className="text-accent-primary hover:underline mb-4 self-start font-medium"
        >
          ← Back to Editor
        </button>

        {/* Global Score */}
        <div className="flex justify-center mb-10">
          <ScoreCircle score={globalScore} />
        </div>

        {/* 4 cards — same data as Dashboard cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Time Complexity */}
          <div
            onClick={() => onNavigate(Page.TIME_COMPLEXITY_REPORT)}
            className="bg-ui-panels p-6 rounded-lg border border-border-color
                       transition-all hover:-translate-y-1 hover:shadow-lg
                       hover:border-accent-primary cursor-pointer group"
          >
            <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">
              Time Complexity
            </h3>
            <p className={`text-3xl font-mono ${
              analysisData.time_complexity === 'O(1)' || analysisData.time_complexity === 'O(n)'
                ? 'text-green-400' : 'text-orange-400'}`}>
              {analysisData.time_complexity || 'O(1)'}
            </p>
          </div>

          {/* Space Complexity */}
          <div
            onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)}
            className="bg-ui-panels p-6 rounded-lg border border-border-color
                       transition-all hover:-translate-y-1 hover:shadow-lg
                       hover:border-accent-primary cursor-pointer group"
          >
            <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">
              Space Complexity
            </h3>
            <p className={`text-3xl font-mono ${
              analysisData.space_complexity === 'O(1)' ? 'text-green-400' : 'text-orange-400'}`}>
              {analysisData.space_complexity || 'O(1)'}
            </p>
          </div>

          {/* SOLID */}
          <div
            onClick={() => onNavigate(Page.SOLID_REPORT)}
            className="bg-ui-panels p-6 rounded-lg border border-border-color
                       transition-all hover:-translate-y-1 hover:shadow-lg
                       hover:border-accent-primary cursor-pointer group"
          >
            <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">
              SOLID Principles
            </h3>
            <p className={`text-xl font-semibold ${
              analysisData.total_violations === 0 ? 'text-green-400' : 'text-red-400'}`}>
              {analysisData.total_violations === 0 ? 'All Pass ✅' : `${analysisData.total_violations} Violations`}
            </p>
            {/* SOLID pills — same as Dashboard */}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {['S','O','L','I','D'].map(key => {
                const st = solid[key]?.status ?? 'Pending';
                return (
                  <span key={key} className={`text-xs font-bold px-2 py-0.5 rounded-full border
                    ${st === 'Pass'
                      ? 'bg-green-500/10 border-green-500/30 text-green-400'
                      : st === 'Violation'
                      ? 'bg-red-500/10 border-red-500/30 text-red-400'
                      : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'}`}>
                    {key}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Clean Code */}
          <div
            onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)}
            className="bg-ui-panels p-6 rounded-lg border border-border-color
                       transition-all hover:-translate-y-1 hover:shadow-lg
                       hover:border-accent-primary cursor-pointer group"
          >
            <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">
              Clean Code
            </h3>
            <p className={`text-xl font-semibold ${
              cleanPassed ? 'text-green-400' : cleanScore >= 55 ? 'text-yellow-400' : 'text-red-400'}`}>
              {cleanScore}/100 — Grade {cleanGrade}
            </p>
            <p className="text-sm text-text-secondary mt-1">
              {cleanPassed ? 'Passed' : 'Needs improvement'}
              {clean.metrics?.maintainability_index !== undefined && ` · MI: ${Math.round(clean.metrics.maintainability_index)}`}
            </p>
          </div>
        </div>

        {/* Model selector + Optimize button */}
        <div className="flex gap-3 mt-8 items-stretch">

          {/* Model selector */}
          <div className="flex flex-col gap-1 bg-ui-panels border border-border-color
                          rounded-xl px-4 py-3 min-w-[180px]">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              AI Model
            </span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-transparent text-sm font-bold text-text-primary outline-none cursor-pointer"
            >
              {MODEL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
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
                       text-white font-bold text-xl px-6 py-4 rounded-xl
                       hover:opacity-90 transition-all shadow-md hover:shadow-lg
                       uppercase tracking-wide flex items-center justify-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none"
                 viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Optimize Code
          </button>
        </div>

      </div>
    </div>
  );
};

export default Results;
