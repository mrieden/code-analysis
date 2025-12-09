
import React, { useState, useEffect, useMemo } from 'react';

interface CodeEditorProps {
  initialCode: string;
  highlightedLines?: number[];
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ initialCode, highlightedLines = [], readOnly = false }) => {
  const [code, setCode] = useState(initialCode);
  const [lineCount, setLineCount] = useState(code.split('\n').length);

  useEffect(() => {
    setLineCount(code.split('\n').length);
  }, [code]);
  
  const lineNumbers = useMemo(() => {
      return Array.from({ length: lineCount }, (_, i) => i + 1);
  }, [lineCount]);

  return (
    <div className="flex bg-ui-panels rounded-lg border border-border-color font-mono text-sm h-full w-full overflow-hidden">
      <div className="line-numbers bg-background text-text-secondary p-4 text-right select-none">
        {lineNumbers.map((num) => (
          <div key={num} className={`h-[21px] ${highlightedLines.includes(num) ? 'text-accent-primary font-bold' : ''}`}>
            {num}
          </div>
        ))}
      </div>
      <textarea
        value={code}
        onChange={(e) => !readOnly && setCode(e.target.value)}
        readOnly={readOnly}
        spellCheck="false"
        className="flex-grow p-4 bg-ui-panels text-text-primary outline-none resize-none leading-[21px] w-full"
      />
    </div>
  );
};

export default CodeEditor;