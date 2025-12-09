
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';

interface CleanCodeReportProps {
  onNavigate: (page: Page) => void;
}

const codeWithHighlight = `
def calculate_average(numbers): # Good name
    """Calculates the average of a list of numbers.""" # Clear docstring
    if not numbers:
        return 0
    processor = DataProcessor(numbers)
    sum_of_numbers = processor.process() # Descriptive variable
    return sum_of_numbers / len(numbers)
`;

const CleanCodeCard: React.FC<{principle: string, status: 'Pass' | 'Warning' | 'Issue', reason: string, suggestion: string}> = ({principle, status, reason, suggestion}) => {
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


const CleanCodeReport: React.FC<CleanCodeReportProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col gap-8 flex-grow py-8">
      <div>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4">
          &larr; Back to Dashboard
        </button>
        <GradientText as="h1" className="text-4xl font-bold">Detailed Report: Clean Code</GradientText>
      </div>

       <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-2">Overall Status: <span className="text-status-success">Looks Good ✅</span></h2>
        <p className="text-text-secondary">The code adheres to several common clean code practices. A few minor areas for improvement were noted.</p>
      </div>

      <div className="h-64">
         <CodeEditor initialCode={codeWithHighlight} highlightedLines={[1, 2, 6]} readOnly={true} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CleanCodeCard 
            principle="Naming Conventions"
            status="Pass"
            reason="Variables ('sum_of_numbers') and functions ('calculate_average') have clear, descriptive names that reveal their intent."
            suggestion="No refactor needed. Continue using intention-revealing names."
        />
        <CleanCodeCard 
            principle="Function Length"
            status="Pass"
            reason="The 'calculate_average' function is short, focused, and performs a single task."
            suggestion="Keep functions small and focused on one responsibility."
        />
        <CleanCodeCard 
            principle="Comments & Docstrings"
            status="Pass"
            reason="A clear and concise docstring explains the function's purpose without restating the obvious."
            suggestion="Good use of documentation. Avoid comments that explain 'what' the code does; focus on 'why'."
        />
        <CleanCodeCard 
            principle="Magic Numbers"
            status="Warning"
            reason="The value '0' is used directly. While clear in this context, complex logic could benefit from named constants."
            suggestion="For non-obvious numbers, define a constant (e.g., EMPTY_LIST_AVERAGE = 0)."
        />
      </div>

    </div>
  );
};

export default CleanCodeReport;