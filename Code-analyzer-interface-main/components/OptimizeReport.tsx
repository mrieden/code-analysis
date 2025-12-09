
import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';

interface OptimizeReportProps {
  onNavigate: (page: Page) => void;
}

const optimizedCode = `
from typing import Iterable

# Clean Code: Solved magic number warning
EMPTY_RESULT = 0

class DataProcessor:
    # SOLID: Solved Dependency Inversion by using Abstract Base Classes/Typing
    def __init__(self, data: Iterable[int]):
        self.data = data

    def process(self) -> int:
        """Processes the data using optimized built-ins."""
        # Optimization: Built-in sum() is C-optimized and pythonic
        return sum(self.data)

def calculate_average(numbers: list[int]) -> float:
    """Calculates the average of a list of numbers."""
    if not numbers:
        return EMPTY_RESULT
    
    processor = DataProcessor(numbers)
    sum_of_numbers = processor.process()
    return sum_of_numbers / len(numbers)

# Example usage
my_list = [10, 20, 30, 40, 50]
avg = calculate_average(my_list)
print(f"The average is: {avg}")
`;

const ImprovementCard: React.FC<{ title: string, description: string, category: string }> = ({ title, description, category }) => (
    <div className="bg-ui-panels p-4 rounded-lg border border-border-color border-l-4 border-l-status-success shadow-sm">
        <div className="flex justify-between items-center mb-2">
            <h3 className="font-bold text-text-primary">{title}</h3>
            <span className="text-xs font-bold uppercase tracking-wider text-text-secondary border border-border-color px-2 py-1 rounded">{category}</span>
        </div>
        <p className="text-text-secondary text-sm">{description}</p>
    </div>
);

const OptimizeReport: React.FC<OptimizeReportProps> = ({ onNavigate }) => {
  return (
    <div className="flex flex-col gap-6 flex-grow py-8">
      <div>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4">
          &larr; Back to Dashboard
        </button>
        <GradientText as="h1" className="text-4xl font-bold">Optimization Report</GradientText>
        <p className="text-text-secondary mt-2">AI-driven improvements applied to your code.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8 h-full">
          {/* Left Panel: Optimized Code */}
          <div className="lg:w-1/2 flex flex-col gap-4">
              <h2 className="text-xl font-bold text-text-primary">Optimized Code</h2>
              <div className="flex-grow min-h-[500px]">
                <CodeEditor initialCode={optimizedCode} readOnly={true} highlightedLines={[5, 9, 15]} />
              </div>
          </div>

          {/* Right Panel: Report */}
          <div className="lg:w-1/2 flex flex-col gap-4">
               <h2 className="text-xl font-bold text-text-primary">Solved Violations & Improvements</h2>
               
               <div className="flex flex-col gap-4">
                   <ImprovementCard 
                        category="SOLID Principles"
                        title="Dependency Inversion Violation Solved"
                        description="The DataProcessor class now relies on the `Iterable` abstraction rather than a concrete data structure. This makes the class more flexible and testable."
                   />
                   <ImprovementCard 
                        category="Clean Code"
                        title="Magic Number Removed"
                        description="Replaced the literal return value `0` with a named constant `EMPTY_RESULT` to improve readability and maintainability."
                   />
                   <ImprovementCard 
                        category="Performance"
                        title="Pythonic Refactoring"
                        description="Replaced the manual loop with Python's built-in `sum()` function. This is typically implemented in C and is faster than a Python for-loop."
                   />
                   <ImprovementCard 
                        category="Type Safety"
                        title="Type Hints Added"
                        description="Added standard Python type hints (`Iterable[int]`, `-> float`) to improve code clarity and enable static analysis."
                   />
               </div>

               <div className="bg-gradient-to-br from-accent-primary/10 to-accent-secondary/10 p-6 rounded-lg border border-accent-primary/20 mt-4">
                   <h3 className="font-bold text-lg text-accent-primary mb-2">Performance Impact</h3>
                   <div className="grid grid-cols-2 gap-4 text-center">
                       <div>
                           <p className="text-text-secondary text-sm">Original Runtime</p>
                           <p className="font-mono font-bold text-text-primary">~1.2ms</p>
                       </div>
                       <div>
                           <p className="text-text-secondary text-sm">Optimized Runtime</p>
                           <p className="font-mono font-bold text-status-success">~0.8ms</p>
                       </div>
                   </div>
               </div>
          </div>
      </div>
    </div>
  );
};

export default OptimizeReport;