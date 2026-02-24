import React, { useEffect } from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';

interface CleanCodeReportProps {
  onNavigate: (page: Page) => void;
  results: any;
  code: string;
}

const CleanCodeCard: React.FC<{
  principle: string, 
  status: 'Pass' | 'Warning' | 'Issue', 
  reason: string, 
  suggestion: string
}> = ({ principle, status, reason, suggestion }) => {
  const statusStyles = {
    'Pass': 'bg-status-success/20 text-status-success',
    'Warning': 'bg-status-warning/20 text-status-warning',
    'Issue': 'bg-status-error/20 text-status-error',
  };

  return (
    <div className="bg-ui-panels p-4 rounded-lg border border-border-color flex flex-col h-full">
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-xl font-bold">{principle}</h4>
        <span className={`px-3 py-1 text-sm font-bold rounded-full ${statusStyles[status]}`}>
          {status}
        </span>
      </div>
      <p className="text-text-secondary mb-3 flex-grow">{reason}</p>
      <div className="bg-background/50 border-l-4 border-accent-primary/50 mt-auto p-3 rounded-r">
        <p className="font-bold text-accent-primary mb-1">💡 Suggestion</p>
        <p className="text-sm text-text-primary font-mono">{suggestion}</p>
      </div>
    </div>
  );
}

const CleanCodeReport: React.FC<CleanCodeReportProps> = ({ onNavigate, results, code }) => {
  
  // Debugging: This will show you exactly what is arriving from the WebSocket
  useEffect(() => {
    console.log("CleanCodeReport received results:", results);
  }, [results]);

  // GUARD: If results aren't ready yet, show a loading state
  if (!results || !results.clean_report) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary"></div>
        <p className="text-text-secondary font-medium text-lg">Analyzing Clean Code metrics...</p>
        <div className="text-xs text-text-secondary opacity-50 font-mono">
            Waiting for backend response...
        </div>
        <button 
          onClick={() => onNavigate(Page.RESULTS)} 
          className="mt-4 px-6 py-2 bg-ui-panels border border-border-color rounded-full text-accent-primary hover:bg-accent-primary/10 transition-all"
        >
          &larr; Back to Results
        </button>
      </div>
    );
  }

  // Safe data extraction from results.clean_report
  const naming = results.clean_report.naming_quality || { naming_score: 100, issues: [] };
  const mi = results.clean_report.radon?.maintainability_index ?? 0;
  const raw = results.clean_report.radon?.raw_metrics || { total_lines_of_code: 0, logical_lines_of_code: 0, comments: 0 };
  const pylintIssues = results.clean_report.pylint || [];

  // Logic to determine overall status
  const getOverallStatus = () => {
    if (mi > 80 && naming.naming_score > 85) return { text: "Code is Clean ✅", color: "text-status-success" };
    if (mi > 50) return { text: "Needs Refactoring ⚠️", color: "text-status-warning" };
    return { text: "Poor Maintainability ❌", color: "text-status-error" };
  };

  const status = getOverallStatus();

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

      {/* Main Stats Header */}
      <div className="bg-ui-panels p-6 rounded-xl border border-border-color shadow-xl">
        <h2 className="text-2xl font-bold text-text-primary mb-2">
          Maintainability Index: <span className={status.color}>{mi.toFixed(2)}</span>
        </h2>
        <div className="flex flex-wrap gap-6 text-sm">
            <p className="text-text-secondary">
                Status: <strong className={status.color}>{status.text}</strong>
            </p>
            <p className="text-text-secondary">
                Total Lines: <strong>{raw.total_lines_of_code}</strong>
            </p>
            <p className="text-text-secondary">
                Logical Lines: <strong>{raw.logical_lines_of_code}</strong>
            </p>
        </div>
      </div>

      {/* Code Section */}
      <div className="flex flex-col gap-3">
        <h3 className="text-lg font-bold text-text-secondary px-1">Analyzed Snippet</h3>
        <div className="h-64 rounded-xl overflow-hidden border border-border-color shadow-inner">
            <CodeEditor initialCode={code || ""} readOnly={true} />
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <CleanCodeCard 
  principle="Naming Conventions"
  /* 60 or below is now a Red "Issue" */
  status={naming.naming_score > 85 ? "Pass" : naming.naming_score > 60 ? "Warning" : "Issue"}
  reason={`Naming Score: ${naming.naming_score}/100. Found ${naming.issues?.length || 0} violations.`}
  suggestion={naming.issues?.length > 0 ? naming.issues[0].violation : "Standard naming detected."}
/>

<CleanCodeCard 
  principle="Logical Complexity"
  // If you want it to be more "forgiving", lower the Pass threshold to 70
  status={mi > 70 ? "Pass" : mi > 40 ? "Warning" : "Issue"}
  reason={`Maintainability Index: ${mi.toFixed(2)}`}
  suggestion={mi < 70 ? "Simplify nested logic." : "Logic is well-structured."}
/>
        <CleanCodeCard 
          principle="Static Analysis"
          status={pylintIssues.length === 0 ? "Pass" : pylintIssues.length < 5 ? "Warning" : "Issue"}
          reason={`Linter flagged ${pylintIssues.length} potential improvements or style inconsistencies.`}
          suggestion={pylintIssues.length > 0 ? pylintIssues[0].message : "Code passes all internal style and syntax checks."}
        />

        <CleanCodeCard 
  principle="Documentation & Density"
  // Change logic: Only warn if code is long (>10 lines) AND has no comments
  status={(raw.comments > 0 || raw.total_lines_of_code < 10) ? "Pass" : "Warning"}
  reason={`Logical Lines: ${raw.logical_lines_of_code}. Comments: ${raw.comments}.`}
  suggestion="Add a comment or docstring to explain your logic."
/>
      </div>
    </div>
  );
};

export default CleanCodeReport;