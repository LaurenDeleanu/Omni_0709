import React, { useState } from "react";
import FileTree from "./FileTree";
import MonacoEditor from "./MonacoEditor";
import DiffViewer from "./DiffViewer";
import GitPanel from "./GitPanel";
import AIAssistantPanel from "./AIAssistantPanel";
import { FileItem } from "@/lib/git/types";

interface CodeLabViewProps {
  botId: string;
}

export default function CodeLabView({ botId }: CodeLabViewProps) {
  const [files, setFiles] = useState<FileItem[]>([
    { path: "index.js", content: "// Initial scaffolding\nmodule.exports = async (ctx) => {\n  console.log('NexusForge Agent trigger initialized');\n};", language: "javascript" },
    { path: "package.json", content: "{\n  \"name\": \"agent-module\",\n  \"version\": \"1.0.0\",\n  \"dependencies\": {}\n}", language: "json" },
    { path: "README.md", content: "# NexusForge AI Generated Module\nThis module contains code scoped to real-time execution workflow triggers.", language: "markdown" }
  ]);

  const [activeFilePath, setActiveFilePath] = useState("index.js");
  const [isDiffMode, setIsDiffMode] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<"git" | "ai">("ai");

  // Keep track of original files to show differences in Diff mode
  const [originalFiles, setOriginalFiles] = useState<FileItem[]>([
    { path: "index.js", content: "// Initial scaffolding\nmodule.exports = async (ctx) => {\n  console.log('NexusForge Agent trigger initialized');\n};", language: "javascript" },
    { path: "package.json", content: "{\n  \"name\": \"agent-module\",\n  \"version\": \"1.0.0\",\n  \"dependencies\": {}\n}", language: "json" },
    { path: "README.md", content: "# NexusForge AI Generated Module\nThis module contains code scoped to real-time execution workflow triggers.", language: "markdown" }
  ]);

  const activeFile = files.find((f) => f.path === activeFilePath) || null;
  const originalFile = originalFiles.find((f) => f.path === activeFilePath) || null;

  const handleSelectFile = (path: string) => {
    setActiveFilePath(path);
  };

  const handleAddFile = (path: string) => {
    // Determine language from extension
    const ext = path.split(".").pop() || "";
    let language = "plaintext";
    if (["js", "jsx"].includes(ext)) language = "javascript";
    else if (["ts", "tsx"].includes(ext)) language = "typescript";
    else if (ext === "json") language = "json";
    else if (ext === "md") language = "markdown";
    else if (ext === "css") language = "css";
    else if (ext === "html") language = "html";

    const newFile: FileItem = {
      path,
      content: `// Scaffolding for ${path}\n`,
      language,
    };

    setFiles((prev) => [...prev, newFile]);
    setOriginalFiles((prev) => [...prev, { ...newFile }]);
    setActiveFilePath(path);
  };

  const handleDeleteFile = (path: string) => {
    setFiles((prev) => prev.filter((f) => f.path !== path));
    setOriginalFiles((prev) => prev.filter((f) => f.path !== path));
    if (activeFilePath === path) {
      const remaining = files.filter((f) => f.path !== path);
      if (remaining.length > 0) {
        setActiveFilePath(remaining[0].path);
      } else {
        setActiveFilePath("");
      }
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value === undefined) return;
    setFiles((prev) =>
      prev.map((f) => (f.path === activeFilePath ? { ...f, content: value } : f))
    );
  };

  const handleApplyAIChanges = (code: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.path === activeFilePath ? { ...f, content: code } : f))
    );
  };

  const handleProposalSuccess = (
    branchName: string,
    prUrl?: string,
    score?: number,
    feedback?: string
  ) => {
    // Reset original files to match current files after a successful PR proposal
    setOriginalFiles(files.map((f) => ({ ...f })));
    alert(`🎉 ¡Propuesta enviada con éxito!\n\nAuditoría de IA: ${score}/100\nRama: ${branchName}${prUrl ? `\nPR: ${prUrl}` : ""}`);
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0e27] text-white">
      {/* Workspace Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-[#0c1033] shadow-md">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            💻 Laboratorio de Código
          </h2>
          <p className="text-xs text-zinc-400">
            Genera módulos, edita en tiempo real y propón cambios directamente a la rama de desarrollo.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsDiffMode(false)}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              !isDiffMode
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white"
            }`}
          >
            ✏️ Editor
          </button>
          <button
            onClick={() => setIsDiffMode(true)}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              isDiffMode
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white"
            }`}
          >
            🔎 Revisar Cambios
          </button>
        </div>
      </div>

      {/* Main Splits Panel */}
      <div className="flex-1 flex overflow-hidden p-4 gap-4 min-h-0 bg-[#080b20]">
        {/* Left column - Filetree */}
        <div className="w-1/5 min-w-[200px] max-w-[300px] h-full shrink-0">
          <FileTree
            files={files}
            activeFilePath={activeFilePath}
            onSelectFile={handleSelectFile}
            onAddFile={handleAddFile}
            onDeleteFile={handleDeleteFile}
          />
        </div>

        {/* Center column - Code Editor / Diff Editor */}
        <div className="flex-1 h-full min-w-0 flex flex-col">
          {activeFile ? (
            <div className="flex-1 min-h-0 relative">
              {isDiffMode ? (
                <DiffViewer
                  original={originalFile?.content || ""}
                  modified={activeFile.content}
                  language={activeFile.language}
                />
              ) : (
                <MonacoEditor
                  value={activeFile.content}
                  onChange={handleEditorChange}
                  language={activeFile.language}
                />
              )}
            </div>
          ) : (
            <div className="flex-1 border border-zinc-800 rounded-lg flex flex-col items-center justify-center bg-zinc-950/20 text-zinc-500">
              <span className="text-3xl mb-2">📂</span>
              <span className="text-xs">Selecciona un archivo del navegador</span>
            </div>
          )}
        </div>

        {/* Right column - Side panel (Git & AI Assistant) */}
        <div className="w-1/3 min-w-[320px] max-w-[450px] h-full shrink-0 flex flex-col gap-3">
          {/* Tab selector */}
          <div className="flex bg-zinc-950 border border-zinc-800 rounded-lg p-1 shrink-0">
            <button
              onClick={() => setRightPanelTab("ai")}
              className={`flex-1 py-1.5 rounded text-xs font-semibold transition-colors ${
                rightPanelTab === "ai"
                  ? "bg-zinc-900 text-white border border-zinc-800"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              🤖 Asistente de Código
            </button>
            <button
              onClick={() => setRightPanelTab("git")}
              className={`flex-1 py-1.5 rounded text-xs font-semibold transition-colors ${
                rightPanelTab === "git"
                  ? "bg-zinc-900 text-white border border-zinc-800"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              🔌 Control Git
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 min-h-0">
            {rightPanelTab === "ai" ? (
              <AIAssistantPanel
                botId={botId}
                activeFile={activeFile}
                allFiles={files}
                onApplyGeneratedCode={handleApplyAIChanges}
              />
            ) : (
              <GitPanel
                botId={botId}
                files={files}
                onProposalSuccess={handleProposalSuccess}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
