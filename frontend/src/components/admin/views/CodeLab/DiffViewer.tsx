import React from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then(mod => ({ default: mod.DiffEditor })),
  {
    ssr: false,
    loading: () => <div className="flex items-center justify-center h-40"><Loader2 className="animate-spin w-6 h-6 text-zinc-500" /></div>,
  }
);

interface DiffViewerProps {
  original: string;
  modified: string;
  language: string;
  theme?: "vs-dark" | "light";
}

export default function DiffViewer({
  original,
  modified,
  language,
  theme = "vs-dark",
}: DiffViewerProps) {
  return (
    <div className="w-full h-full border rounded-lg overflow-hidden border-zinc-800 bg-[#1e1e1e]">
      <DiffEditor
        height="100%"
        language={language}
        theme={theme}
        original={original}
        modified={modified}
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          readOnly: true,
          cursorBlinking: "smooth",
          lineNumbersMinChars: 3,
          scrollBeyondLastLine: false,
          renderSideBySide: true,
        }}
      />
    </div>
  );
}
