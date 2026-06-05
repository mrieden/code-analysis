import React, { useState, useEffect, useMemo } from 'react';

interface CodeEditorProps {
  value?: string;
  onChange?: (newCode: string) => void;
  language?: string;
  initialCode?: string;
  highlightedLines?: number[];
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  value, 
  onChange, 
  initialCode = '', 
  highlightedLines = [], 
  readOnly = false 
}) => {
  const [internalCode, setInternalCode] = useState(initialCode);

  const currentCode = value !== undefined ? value : internalCode;

  const lineCount = useMemo(() => currentCode.split('\n').length, [currentCode]);
  const lineNumbers = useMemo(() => Array.from({ length: lineCount }, (_, i) => i + 1), [lineCount]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newCode = e.target.value;
    if (onChange) onChange(newCode);
    if (!readOnly && value === undefined) setInternalCode(newCode);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (readOnly) return;

    if (e.key === 'Tab') {
      e.preventDefault(); // stop browser tab-switch

      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const TAB = '    '; // 4 spaces

      const newCode = currentCode.substring(0, start) + TAB + currentCode.substring(end);

      if (onChange) onChange(newCode);
      if (value === undefined) setInternalCode(newCode);

      // Move cursor after the inserted spaces
      requestAnimationFrame(() => {
        textarea.selectionStart = start + TAB.length;
        textarea.selectionEnd = start + TAB.length;
      });
    }
  };

  return (
    <div className="flex bg-ui-panels rounded-lg border border-border-color font-mono text-sm h-full w-full overflow-hidden">
      {/* Line Numbers */}
      <div className="line-numbers bg-background text-text-secondary p-4 text-right select-none min-w-[3rem] border-r border-border-color">
        {lineNumbers.map((num) => (
          <div key={num} className={`h-[21px] ${highlightedLines.includes(num) ? 'text-accent-primary font-bold' : ''}`}>
            {num}
          </div>
        ))}
      </div>

      {/* Editor */}
      <textarea
        value={currentCode}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        readOnly={readOnly}
        spellCheck="false"
        className="flex-grow p-4 bg-ui-panels text-text-primary outline-none resize-none leading-[21px] w-full font-mono"
        placeholder="Type your code here..."
      />
    </div>
  );
};

export default CodeEditor;
