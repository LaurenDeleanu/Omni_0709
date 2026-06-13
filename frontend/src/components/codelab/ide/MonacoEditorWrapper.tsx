"use client";

import React, { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

const Editor = dynamic(() => import("@monaco-editor/react").then((mod) => ({ default: mod.default })), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-[#1e1e1e]">
      <Loader2 className="animate-spin w-6 h-6 text-zinc-500" />
    </div>
  ),
});

interface MonacoEditorWrapperProps {
  value: string;
  onChange: (value: string | undefined) => void;
  language: string;
  theme?: "vs-dark" | "light";
  readOnly?: boolean;
  gitModifiedLines?: { added: number[]; removed: number[]; modified: number[] };
  onCursorChange?: (line: number, col: number) => void;
}

export default function MonacoEditorWrapper({
  value,
  onChange,
  language,
  theme = "vs-dark",
  readOnly = false,
  gitModifiedLines,
  onCursorChange,
}: MonacoEditorWrapperProps) {
  const editorRef = useRef<any>(null);

  const handleMount = (editor: any, monaco: any) => {
    editorRef.current = editor;

    editor.onDidChangeCursorPosition((e: any) => {
      onCursorChange?.(e.position.lineNumber, e.position.column);
    });

    if (gitModifiedLines) {
      const decorations = [
        ...gitModifiedLines.added.map((line) => ({
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            linesDecorationsClassName: "git-added-line",
            className: "git-added-line-bg",
          },
        })),
        ...gitModifiedLines.removed.map((line) => ({
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            linesDecorationsClassName: "git-removed-line",
            className: "git-removed-line-bg",
          },
        })),
        ...gitModifiedLines.modified.map((line) => ({
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            linesDecorationsClassName: "git-modified-line",
            className: "git-modified-line-bg",
          },
        })),
      ];
      editor.deltaDecorations([], decorations);
    }
  };

  return (
    <div className="w-full h-full bg-[#1e1e1e]">
      <Editor
        height="100%"
        language={language}
        theme={theme}
        value={value}
        onChange={onChange}
        onMount={handleMount}
        options={{
          fontSize: 14,
          fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
          minimap: { enabled: true, scale: 1 },
          wordWrap: "on",
          automaticLayout: true,
          readOnly,
          cursorBlinking: "smooth",
          cursorSmoothCaretAnimation: "on",
          smoothScrolling: true,
          lineNumbersMinChars: 3,
          scrollBeyondLastLine: false,
          padding: { top: 12 },
          renderWhitespace: "selection",
          bracketPairColorization: { enabled: true },
          guides: { bracketPairs: true, indentation: true },
          renderLineHighlight: "all",
          tabSize: 2,
          insertSpaces: true,
          lineDecorationsWidth: 10,
          glyphMargin: true,
        }}
      />
    </div>
  );
}
