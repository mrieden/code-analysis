import React from 'react';
import { Page } from '../types';
import GradientText from './GradientText';
import CodeEditor from './CodeEditor';

// 1. MUST DEFINE PROPS INTERFACE
interface SolidReportProps {
  onNavigate: (page: Page) => void;
  results: any;
  code: string;
}

const SolidPrincipleCard: React.FC<{
  principle: string, 
  letter: string, 
  status: 'Pass' | 'Violation', 
  reason: string, 
  suggestion: string
}> = ({principle, letter, status, reason, suggestion}) => (
    <div className="bg-ui-panels p-4 rounded-lg border border-border-color flex flex-col h-full">
        <div className="flex justify-between items-start mb-2">
            <h4 className="text-xl font-bold"><GradientText>{letter}</GradientText> - {principle}</h4>
            <span className={`px-3 py-1 text-sm font-bold rounded-full ${status === 'Pass' ? 'bg-status-success/20 text-status-success' : 'bg-status-error/20 text-status-error'}`}>
                {status}
            </span>
        </div>
        <p className="text-text-secondary mb-3 flex-grow">{reason}</p>
        <div className="bg-background/50 border-l-4 border-accent-primary/50 mt-auto p-3 rounded-r">
            <p className="font-bold text-accent-primary mb-1">💡 Suggested Refactor</p>
            <p className="text-sm text-text-primary font-mono">{suggestion}</p>
        </div>
    </div>
);

const SolidReport: React.FC<SolidReportProps> = ({ onNavigate, results, code }) => {
  // 2. EXTRACT S, O, and L from the WebSocket results
  const sReport = results.solid_report?.S || { status: 'Pass', reason: 'Ready', suggestion: 'N/A' };
  const oReport = results.solid_report?.O || { status: 'Pass', reason: 'Ready', suggestion: 'N/A' };
  const lReport = results.solid_report?.L || { status: 'Pass', reason: 'Ready', suggestion: 'N/A' };
  const iReport = results.solid_report?.I || { status: 'Pass', reason: 'Ready', suggestion: 'N/A' };
  const dReport = results.solid_report?.D || { status: 'Pass', reason: 'Ready', suggestion: 'N/A' };

  return (
    <div className="flex flex-col gap-8 flex-grow py-8">
      <button onClick={() => onNavigate(Page.RESULTS)} className="text-accent-primary hover:underline self-start">&larr; Back to Summary</button>
      <GradientText as="h1" className="text-4xl font-bold">Detailed Report: SOLID Principles</GradientText>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
       <h2 className="text-2xl font-bold text-text-primary mb-2">
        Overall Status: 
        <span className={results.total_violations > 0 ? "text-status-error" : "text-status-success"}>
            {results.total_violations > 0 
                ? ` ${results.total_violations} Violation${results.total_violations !== 1 ? 's' : ''} Found` 
                : " No Violations Found"}
        </span>
    </h2>
        <p className="text-text-secondary">{results.total_violations > 0 ? "Structural issues detected." : "Your code follows the active principles."}</p>
      </div>

      <div className="h-64"><CodeEditor initialCode={code} readOnly={true} /></div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SolidPrincipleCard 
            letter="S" 
            principle="Single Responsibility" 
            status={sReport.status} 
            reason={sReport.reason} 
            suggestion={sReport.suggestion} 
        />
        <SolidPrincipleCard 
            letter="O" 
            principle="Open/Closed" 
            status={oReport.status} 
            reason={oReport.reason} 
            suggestion={oReport.suggestion} 
        />
        <SolidPrincipleCard 
            letter="L" 
            principle="Liskov Substitution" 
            status={lReport.status} 
            reason={lReport.reason} 
            suggestion={lReport.suggestion} 
        />
        
        <SolidPrincipleCard 
    letter="I" 
    principle="Interface Segregation" 
    status={iReport.status} 
    reason={iReport.reason} 
    suggestion={iReport.suggestion} 
/>
        <SolidPrincipleCard letter="D" principle="Dependency Inversion" status={dReport.status} reason={dReport.reason} suggestion={dReport.suggestion} />
      </div>
<div className="flex justify-end mt-4">
                <button
                    onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)}
                    className="bg-accent-secondary text-white font-semibold px-6 py-3 rounded-lg hover:opacity-90 transition-all shadow-md">
                    Next: Clean Code Report &rarr;
                </button>
            </div>
    </div>
  );
};

export default SolidReport;