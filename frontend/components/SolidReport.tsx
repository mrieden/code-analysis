import React from 'react';
import { Page } from '../types';
import GradientText from './GradientText';
import CodeEditor from './CodeEditor';

interface SolidReportProps {
  onNavigate: (page: Page) => void;
  results: any;
  code: string;
}

const SolidPrincipleCard: React.FC<{
  principle: string;
  letter: string;
  status: 'Pass' | 'Violation' | string;
  reason: string;
  violations: { line: number | null; message: string; detail: string }[];
}> = ({ principle, letter, status, reason, violations }) => {
  const isPass = status === 'Pass';

  return (
    <div className="bg-ui-panels p-4 rounded-lg border border-border-color flex flex-col h-full">
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-xl font-bold">
          <GradientText>{letter}</GradientText> — {principle}
        </h4>
        <span className={`px-3 py-1 text-sm font-bold rounded-full ${
          isPass
            ? 'bg-status-success/20 text-status-success'
            : 'bg-status-error/20 text-status-error'
        }`}>
          {isPass ? 'Pass' : 'Violation'}
        </span>
      </div>

      <p className="text-text-secondary text-sm mb-3">{reason}</p>

      {!isPass && violations.length > 0 ? (
        <div className="flex flex-col gap-2 mt-1">
          {violations.map((v, i) => (
            <div
              key={i}
              className="bg-background/60 border border-status-error/20 rounded-md p-3 flex flex-col gap-1"
            >
              {v.line !== null && (
                <span className="text-xs font-mono font-bold text-status-error bg-status-error/10 px-2 py-0.5 rounded w-fit">
                  Line {v.line}
                </span>
              )}
              <p className="text-sm text-text-primary font-mono">{v.message}</p>
              {v.detail && (
                <p className="text-xs text-text-secondary">{v.detail}</p>
              )}
            </div>
          ))}
        </div>
      ) : isPass ? (
        <div className="bg-status-success/5 border border-status-success/20 rounded-md p-3 mt-auto">
          <p className="text-sm text-status-success font-mono">✓ No violations detected.</p>
        </div>
      ) : null}
    </div>
  );
};

const SolidReport: React.FC<SolidReportProps> = ({ onNavigate, results, code }) => {
  const solid = results?.solid_report || {};

  const getReport = (key: string) => solid[key] || { status: 'Pass', reason: 'Ready', violations: [] };

  const sReport = getReport('S');
  const oReport = getReport('O');
  const lReport = getReport('L');
  const iReport = getReport('I');
  const dReport = getReport('D');

  return (
    <div className="flex flex-col gap-8 flex-grow py-8">

      <button onClick={() => onNavigate(Page.RESULTS)} className="text-accent-primary hover:underline self-start">
        &larr; Back to Summary
      </button>

      <GradientText as="h1" className="text-4xl font-bold">Detailed Report: SOLID Principles</GradientText>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-2">
          Overall Status:
          <span className={results?.total_violations > 0 ? 'text-status-error' : 'text-status-success'}>
            {results?.total_violations > 0
              ? ` ${results.total_violations} Violation${results.total_violations !== 1 ? 's' : ''} Found`
              : ' No Violations Found'}
          </span>
        </h2>
        <p className="text-text-secondary">
          {results?.total_violations > 0
            ? 'Structural issues detected. See cards below for line-level details.'
            : 'Your code follows all active SOLID principles.'}
        </p>
      </div>

      <div className="h-64">
        <CodeEditor initialCode={code} readOnly={true} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SolidPrincipleCard letter="S" principle="Single Responsibility"
          status={sReport.status} reason={sReport.reason} violations={sReport.violations || []} />
        <SolidPrincipleCard letter="O" principle="Open/Closed"
          status={oReport.status} reason={oReport.reason} violations={oReport.violations || []} />
        <SolidPrincipleCard letter="L" principle="Liskov Substitution"
          status={lReport.status} reason={lReport.reason} violations={lReport.violations || []} />
        <SolidPrincipleCard letter="I" principle="Interface Segregation"
          status={iReport.status} reason={iReport.reason} violations={iReport.violations || []} />
        <SolidPrincipleCard letter="D" principle="Dependency Inversion"
          status={dReport.status} reason={dReport.reason} violations={dReport.violations || []} />
      </div>

      <div className="flex justify-between mt-4">
        <button
          onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)}
          className="bg-ui-panels text-text-primary font-semibold px-6 py-3 rounded-lg border border-border-color hover:opacity-90 transition-all shadow-md"
        >
          &larr; Previous: Space Complexity
        </button>
        <button
          onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)}
          className="bg-accent-secondary text-white font-semibold px-6 py-3 rounded-lg hover:opacity-90 transition-all shadow-md"
        >
          Next: Clean Code Report &rarr;
        </button>
      </div>

    </div>
  );
};

export default SolidReport;
