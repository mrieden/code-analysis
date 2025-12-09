
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';
import ComplexityGraph from './ComplexityGraph';

interface SpaceComplexityReportProps {
  onNavigate: (page: Page) => void;
}

const codeExample = `
# A simple example to demonstrate analysis
import math

class DataProcessor:
    def __init__(self, data):
        self.data = data 

    def process(self):
        """Processes the data by summing it."""
        total = 0 # O(1) space
        # This loop does not create new data structures
        for item in self.data:
            total += item
        return total
`;

const SpaceComplexityReport: React.FC<SpaceComplexityReportProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col gap-8 flex-grow py-8">
      <div>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4">
          &larr; Back to Dashboard
        </button>
        <GradientText as="h1" className="text-4xl font-bold">Detailed Report: Space Complexity</GradientText>
      </div>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-2">Overall Space Complexity: <span className="font-mono text-accent-secondary">O(1)</span></h2>
        <p className="text-text-secondary">The memory usage of the algorithm remains constant, regardless of the input size.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="flex flex-col gap-4">
            <h3 className="text-xl font-semibold">Analyzed Code</h3>
            <div className="h-80">
                <CodeEditor initialCode={codeExample} highlightedLines={[9]} readOnly={true} />
            </div>
        </div>
        <div className="flex flex-col gap-4">
            <h3 className="text-xl font-semibold">Memory Hotspots</h3>
            <div className="bg-ui-panels rounded-lg border border-border-color overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="bg-background">
                        <tr>
                            <th className="p-3">Line #</th>
                            <th className="p-3">Variable</th>
                            <th className="p-3">Complexity</th>
                            <th className="p-3">Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr className="border-t border-border-color hover:bg-background/50 transition-colors">
                            <td className="p-3 font-mono text-accent-primary">9</td>
                            <td className="p-3 font-mono">total</td>
                            <td className="p-3 font-mono">O(1)</td>
                            <td className="p-3">A single integer variable is allocated.</td>
                        </tr>
                         <tr className="border-t border-border-color hover:bg-background/50 transition-colors">
                            <td className="p-3 font-mono text-accent-primary">11</td>
                            <td className="p-3 font-mono">item</td>
                            <td className="p-3 font-mono">O(1)</td>
                            <td className="p-3">Reference to an existing item, no new space allocated per iteration.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
      </div>

      <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
        <h2 className="text-2xl font-bold text-text-primary mb-4">Learn More: Space Complexity</h2>
        <div className="flex flex-col md:flex-row gap-6">
            <p className="md:w-1/2 text-text-secondary">
              Space complexity is a measure of the amount of working storage an algorithm needs. It describes how the memory consumption of an algorithm grows with the input size. Like time complexity, it's usually expressed with Big O notation. Efficient memory usage is critical for applications running on devices with limited memory or processing large datasets.
            </p>
            <div className="md:w-1/2 min-h-[16rem] bg-background rounded-lg border border-border-color flex items-center justify-center p-4">
                <ComplexityGraph />
            </div>
        </div>
      </div>

    </div>
  );
};

export default SpaceComplexityReport;