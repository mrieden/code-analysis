
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import ScoreCircle from './ScoreCircle';

interface DashboardProps {
  onNavigate: (page: Page) => void;
}

const pythonExample = `
# A simple example to demonstrate analysis
import math

class DataProcessor:
    def __init__(self, data):
        self.data = data # This couples the class to a specific data structure

    def process(self):
        """Processes the data by summing it."""
        total = 0
        # This loop is O(n)
        for item in self.data:
            total += item
        return total

def calculate_average(numbers):
    """Calculates the average of a list of numbers."""
    if not numbers:
        return 0
    processor = DataProcessor(numbers)
    sum_of_numbers = processor.process()
    return sum_of_numbers / len(numbers)

# Example usage
my_list = [10, 20, 30, 40, 50]
avg = calculate_average(my_list)
print(f"The average is: {avg}")
`;

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col lg:flex-row gap-8 flex-grow py-8">
      {/* Left Panel: Input */}
      <div className="lg:w-[55%] flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <select className="bg-ui-panels border border-border-color rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-accent-primary w-full max-w-xs">
            <option>Python</option>
            <option>JavaScript</option>
            <option>Java</option>
            <option>C++</option>
          </select>
          <button className="bg-gradient-to-r from-accent-primary to-accent-secondary text-white dark:text-background font-bold px-6 py-2 rounded-md hover:opacity-90 transition-opacity shadow-md hover:shadow-lg">
            Analyze
          </button>
        </div>
        <div className="flex-grow min-h-[300px]">
          <CodeEditor initialCode={pythonExample} />
        </div>
      </div>

      {/* Right Panel: Results */}
      <div className="lg:w-[45%] flex flex-col gap-6 bg-ui-panels/70 p-6 rounded-lg border border-border-color shadow-2xl shadow-background">
        <div className="flex justify-center">
          <ScoreCircle score={85} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div onClick={() => onNavigate(Page.TIME_COMPLEXITY_REPORT)} className="bg-ui-panels p-4 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary">
            <h3 className="font-bold text-lg text-text-primary mb-2">Time Complexity</h3>
            <p className="text-3xl font-mono text-accent-secondary">O(n)</p>
          </div>

          <div onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)} className="bg-ui-panels p-4 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary">
             <h3 className="font-bold text-lg text-text-primary mb-2">Space Complexity</h3>
             <p className="text-3xl font-mono text-accent-secondary">O(1)</p>
          </div>

          <div onClick={() => onNavigate(Page.SOLID_REPORT)} className="bg-ui-panels p-4 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary">
            <h3 className="font-bold text-lg text-text-primary mb-2">SOLID Principles</h3>
            <p className="text-xl text-status-error font-semibold">Violation Found</p>
          </div>

          <div onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)} className="bg-ui-panels p-4 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary">
            <h3 className="font-bold text-lg text-text-primary mb-2">Clean Code</h3>
            <p className="text-xl text-status-success font-semibold">Looks Good ✅</p>
          </div>
        </div>
        <button 
            onClick={() => onNavigate(Page.OPTIMIZE_REPORT)}
            className="w-full bg-gradient-to-r from-accent-primary to-accent-secondary text-white dark:text-background font-bold text-lg px-6 py-3 rounded-md hover:opacity-90 transition-opacity shadow-md hover:shadow-lg mt-2">
            Optimize
        </button>
      </div>
    </div>
  );
};

export default Dashboard;