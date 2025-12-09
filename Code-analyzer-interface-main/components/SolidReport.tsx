
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';

interface SolidReportProps {
  onNavigate: (page: Page) => void;
}

const codeWithHighlight = `
# A simple example to demonstrate analysis
import math

class DataProcessor:
    def __init__(self, data):
        self.data = data # This couples the class to a specific data structure

    def process(self):
        """Processes the data by summing it."""
        # ... implementation
`;

const SolidPrincipleCard: React.FC<{principle: string, letter: string, status: 'Pass' | 'Violation', reason: string, suggestion: string}> = ({principle, letter, status, reason, suggestion}) => (
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


const SolidReport: React.FC<SolidReportProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col gap-8 flex-grow py-8">
      <div>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4">
          &larr; Back to Dashboard
        </button>
        <GradientText as="h1" className="text-4xl font-bold">Detailed Report: SOLID Principles</GradientText>
      </div>

       <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-2">Overall Status: <span className="text-status-error">1 Violation Found</span></h2>
        <p className="text-text-secondary">The analysis detected a violation of the Dependency Inversion Principle.</p>
      </div>

      <div className="h-64">
         <CodeEditor initialCode={codeWithHighlight} highlightedLines={[4]} readOnly={true} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SolidPrincipleCard 
            letter="S" 
            principle="Single Responsibility"
            status="Pass"
            reason="The 'DataProcessor' class has a single responsibility: to process data."
            suggestion="No refactor needed."
        />
        <SolidPrincipleCard 
            letter="O" 
            principle="Open/Closed"
            status="Pass"
            reason="The class is simple enough that this principle is not violated in a major way, but could be extended."
            suggestion="Consider using an abstract base class if more processor types are needed."
        />
        <SolidPrincipleCard 
            letter="L" 
            principle="Liskov Substitution"
            status="Pass"
            reason="Not applicable as there is no inheritance hierarchy."
            suggestion="If subclassing 'DataProcessor', ensure substitutability."
        />
        <SolidPrincipleCard 
            letter="I" 
            principle="Interface Segregation"
            status="Pass"
            reason="The class has a minimal, cohesive interface."
            suggestion="No refactor needed."
        />
        <SolidPrincipleCard 
            letter="D" 
            principle="Dependency Inversion"
            status="Violation"
            reason="The 'DataProcessor' high-level module depends directly on the concrete 'list' data structure from the low-level module."
            suggestion="Depend on an abstraction, e.g., an iterable interface, not a concrete list."
        />
      </div>

    </div>
  );
};

export default SolidReport;