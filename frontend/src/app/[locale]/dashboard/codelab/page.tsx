"use client";

import dynamic from "next/dynamic";

const CodeLabView = dynamic(
  () => import("@/components/codelab/ide/IDECodeLabView"),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-screen bg-[#1e1e1e]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-[#007acc] border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400 text-sm">Loading IDE...</span>
        </div>
      </div>
    ),
  }
);

export default function CodeLabPage() {
  return <CodeLabView />;
}
