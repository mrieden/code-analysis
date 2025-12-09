
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';
import ComplexityGraph from './ComplexityGraph';

interface TimeComplexityReportProps {
  onNavigate: (page: Page) => void;
}

const codeWithHighlight = `
# A simple example to demonstrate analysis
import math

class DataProcessor:
    def __init__(self, data):
        self.data = data 

    def process(self):
        """Processes the data by summing it."""
        total = 0
        # This loop is O(n)
        for item in self.data:
            total += item
        return total

# ... rest of the code
`;

const TimeComplexityReport: React.FC<TimeComplexityReportProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col gap-8 flex-grow py-8">
      <div>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4">
          &larr; Back to Dashboard
        </button>
        <GradientText as="h1" className="text-4xl font-bold">Detailed Report: Time Complexity</GradientText>
      </div>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-2">Overall Time Complexity: <span className="font-mono text-accent-secondary">O(n)</span></h2>
        <p className="text-text-secondary">The algorithm's execution time grows linearly with the input size.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="flex flex-col gap-4">
            <h3 className="text-xl font-semibold">Code with Hotspots</h3>
            <div className="h-80">
                <CodeEditor initialCode={codeWithHighlight} highlightedLines={[11]} readOnly={true} />
            </div>
        </div>
        <div className="flex flex-col gap-4">
            <h3 className="text-xl font-semibold">Performance Hotspots</h3>
            <div className="bg-ui-panels rounded-lg border border-border-color overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="bg-background">
                        <tr>
                            <th className="p-3">Line #</th>
                            <th className="p-3">Code Snippet</th>
                            <th className="p-3">Complexity</th>
                            <th className="p-3">Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr className="border-t border-border-color hover:bg-background/50 transition-colors">
                            <td className="p-3 font-mono text-accent-primary">11</td>
                            <td className="p-3 font-mono">for item in self.data:</td>
                            <td className="p-3 font-mono">O(n)</td>
                            <td className="p-3">The loop iterates through each element of the input 'data'.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
      </div>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-4">Learn More: Big O Notation</h2>
        <div className="flex flex-col md:flex-row gap-6">
            <p className="md:w-1/2 text-text-secondary">
              Big O notation is a mathematical notation that describes the limiting behavior of a function when the argument tends towards a particular value or infinity. In computer science, it's used to classify algorithms according to how their run time or space requirements grow as the input size grows. Understanding Big O is crucial for writing efficient and scalable code.
            </p>
            <div className="md:w-1/2 min-h-[16rem] bg-background rounded-lg border border-border-color flex items-center justify-center p-4">
                <ComplexityGraph />
            </div>
        </div>
      </div>

    </div>
  );
};

export default TimeComplexityReport;