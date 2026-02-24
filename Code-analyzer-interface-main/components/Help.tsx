
import React from 'react';
import { Page } from '../types';
import GradientText from './GradientText';

interface HelpProps {
  onNavigate: (page: Page) => void;
}

const FAQItem: React.FC<{ question: string; children: React.ReactNode }> = ({ question, children }) => (
  <details className="bg-ui-panels/50 p-4 rounded-lg border border-border-color">
    <summary className="font-semibold text-text-primary cursor-pointer">{question}</summary>
    <div className="mt-2 text-text-secondary">
      {children}
    </div>
  </details>
);

const Help: React.FC<HelpProps> = ({ onNavigate }) => {
  return (
    <div className="max-w-4xl mx-auto py-8 flex-grow">
      <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-8">
          &larr; Back to Dashboard
      </button>

      <GradientText as="h1" className="text-5xl font-bold text-center mb-12">
        Help & Documentation
      </GradientText>
      
      <div className="space-y-10">
        <section>
          <h2 className="text-3xl font-bold mb-4 border-b-2 border-border-color pb-2">How to Use the Analyzer</h2>
          <ol className="list-decimal list-inside space-y-2 text-text-primary">
            <li>Select the programming language of your code snippet from the dropdown menu.</li>
            <li>Paste your code into the editor on the left panel.</li>
            <li>Click the "Analyze" button to start the process.</li>
            <li>View the summary results in the right panel, including the Global Quality Score.</li>
            <li>Click on any result card (e.g., "Time Complexity") to view a detailed report.</li>
          </ol>
        </section>

        <section>
          <h2 className="text-3xl font-bold mb-4 border-b-2 border-border-color pb-2">Understanding the Metrics</h2>
          <div className="space-y-4">
            <p><strong className="text-accent-primary">Time Complexity (Big O):</strong> Measures how the runtime of your code scales with the size of the input. Lower is better (e.g., O(1), O(log n)).</p>
            <p><strong className="text-accent-secondary">SOLID Principles:</strong> A set of five design principles for object-oriented programming intended to make software designs more understandable, flexible, and maintainable.</p>
            <p><strong className="text-status-success">Clean Code:</strong> Assesses your code against common best practices for readability, such as meaningful variable names, appropriate comments, and function length.</p>
          </div>
        </section>

        <section>
          <h2 className="text-3xl font-bold mb-4 border-b-2 border-border-color pb-2">Supported Languages & Limitations</h2>
          <p className="text-text-secondary">
            Currently, the analyzer has the best support for Python. Support for JavaScript, Java, and C++ is in beta. The analysis works best on single files or small, self-contained snippets of code. It does not analyze project-wide dependencies or external libraries.
          </p>
        </section>

        <section>
          <h2 className="text-3xl font-bold mb-4 border-b-2 border-border-color pb-2">Frequently Asked Questions (FAQ)</h2>
          <div className="space-y-4">
            <FAQItem question="Is my code stored on your servers?">
              <p>No. The analysis is performed in memory and your code is not stored or logged. This is a non-functional demonstration project.</p>
            </FAQItem>
            <FAQItem question="What does the 'Global Quality Score' mean?">
              <p>It's a composite score derived from all the analysis metrics. It provides a quick, at-a-glance indication of your code's overall health, but the detailed reports contain the most valuable insights.</p>
            </FAQItem>
            <FAQItem question="Can I use this for my commercial project?">
              <p>This tool is an educational graduation project and is not intended for production use. It can be a great learning tool, but it does not replace a thorough manual code review by an experienced engineer.</p>
            </FAQItem>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Help;