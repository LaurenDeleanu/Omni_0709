import React from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

const Editor = dynamic(() => import("@monaco-editor/react").then(mod => ({ default: mod.default })), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-40"><Loader2 className="animate-spin w-6 h-6 text-zinc-500" /></div>,
});

interface MonacoEditorProps {
  value: string;
  onChange: (value: string | undefined) => void;
  language: string;
  theme?: "vs-dark" | "light";
  readOnly?: boolean;
}

export default function MonacoEditor({
  value,
  onChange,
  language,
  theme = "vs-dark",
  readOnly = false,
}: MonacoEditorProps) {
  return (
    <div className="w-full h-full border rounded-lg overflow-hidden border-zinc-800 bg-[#1e1e1e]">
      <Editor
        height="100%"
        language={language}
        theme={theme}
        value={value}
        onChange={onChange}
        options={{
          fontSize: 14,
          minimap: { enabled: true },
          wordWrap: "on",
          automaticLayout: true,
          readOnly,
          cursorBlinking: "smooth",
          lineNumbersMinChars: 3,
          scrollBeyondLastLine: false,
          padding: { top: 8, bottom: 8 }
        }}
      />
    </div>
  );
}
