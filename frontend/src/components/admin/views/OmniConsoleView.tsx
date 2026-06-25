"use client";

import React, { useState, useEffect, useRef } from "react";
import MonacoEditor from "./CodeLab/MonacoEditor";
import DiffViewer from "./CodeLab/DiffViewer";
import GitPanel from "./CodeLab/GitPanel";
import { fetchClient } from "@/lib/api/client";
import { toast } from "sonner";

interface FileItem {
  path: string;
  isDir: boolean;
  language: string;
}

interface TraceStep {
  step: number;
  thought: string;
  tool: string;
  arguments: any;
  timestamp: string;
  latencyMs: number;
}

interface RunLog {
  id: string;
  botId: string;
  triggerSource: string;
  status: string;
  inputPayload: string; // JSON string
  outputResult: string;
  loopCount: number;
  tokenUsage: number;
  costUsd: number;
  latencyMs: number;
  executionTrace: string; // JSON string of TraceStep[]
  createdAt: string;
}

interface OmniConsoleViewProps {
  botId?: string;
}

export default function OmniConsoleView({ botId }: OmniConsoleViewProps) {
  const activeOrgId = "default";
  const activeOrg = { name: "Acme Corp" };
  const [currentPath, setCurrentPath] = useState(".");
  const [filesList, setFilesList] = useState<FileItem[]>([]);
  const [fileSearch, setFileSearch] = useState("");
  const [activeFilePath, setActiveFilePath] = useState("");
  const [activeFileContent, setActiveFileContent] = useState("");
  const [isDiffMode, setIsDiffMode] = useState(false);

  // File operations state
  const [newFileName, setNewFileName] = useState("");
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  
  // Diff viewer state
  const [diffOriginal, setDiffOriginal] = useState("");
  const [diffModified, setDiffModified] = useState("");
  const [diffPath, setDiffPath] = useState("");
  const [diffLanguage, setDiffLanguage] = useState("typescript");

  // Chat/Run state
  const [prompt, setPrompt] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [runs, setRuns] = useState<RunLog[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunLog | null>(null);
  const [activeTab, setActiveTab] = useState<"editor" | "diff" | "logs" | "settings">("editor");
  const [compilerLogs, setCompilerLogs] = useState("");

  // Agent configuration states
  const [agentName, setAgentName] = useState("");
  const [agentModel, setAgentModel] = useState("openai/gpt-4o");
  const [agentPrompt, setAgentPrompt] = useState("");
  const [agentMaxLoops, setAgentMaxLoops] = useState(8);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Right Panel Tabs: "agent" | "git"
  const [rightPanelTab, setRightPanelTab] = useState<"agent" | "git">("agent");
  const [isSavingFile, setIsSavingFile] = useState(false);

  const handleSaveFile = async () => {
    if (!activeFilePath || isSavingFile) return;
    setIsSavingFile(true);
    try {
      await fetchClient("/omni/files", {
        method: "POST",
        body: JSON.stringify({
          orgId: activeOrgId,
          path: activeFilePath,
          content: activeFileContent
        })
      });
      toast.success("¡Archivo guardado con éxito!");
    } catch (e: any) {
      toast.error(`Error al guardar: ${e.message}`);
    } finally {
      setIsSavingFile(false);
    }
  };

  const handleProposalSuccess = (branchName: string, prUrl?: string, score?: number, feedback?: string) => {
    toast.success(`🎉 ¡Propuesta enviada con éxito! Auditoría de IA: ${score}/100 — Rama: ${branchName}${prUrl ? ` — PR: ${prUrl}` : ""}`);
  };

  // Fetch files in the current workspace path
  const fetchFiles = async (dirPath: string) => {
    try {
      const data = await fetchClient(
        `/omni/files?orgId=${activeOrgId}&action=list&path=${encodeURIComponent(dirPath)}`
      );
      // Sort directories first, then files
      const sorted = (data.files || []).sort((a: FileItem, b: FileItem) => {
        if (a.isDir && !b.isDir) return -1;
        if (!a.isDir && a.isDir) return 1;
        return a.path.localeCompare(b.path);
      });
      setFilesList(sorted);
    } catch (err) {
      console.error("Failed to fetch workspace files:", err);
    }
  };

  // Fetch past runs & Master Agent details
  const fetchRuns = async () => {
    try {
      const data = await fetchClient(`/omni/master?orgId=${activeOrgId}`);
      setRuns(data.runs || []);
      if (data.runs && data.runs.length > 0 && !selectedRun) {
        setSelectedRun(data.runs[0]);
      }
      if (data.agent) {
        setAgentName(data.agent.name || "Omni Master Controller");
        setAgentModel(data.agent.aiModel || "openai/gpt-4o");
        setAgentPrompt(data.agent.aiSystemPrompt || "");
        setAgentMaxLoops(data.agent.agentConfig?.maxLoops || 8);
      }
    } catch (err) {
      console.error("Failed to fetch master agent runs:", err);
    }
  };

  useEffect(() => {
    fetchFiles(currentPath);
    fetchRuns();
  }, [currentPath]);

  const fetchModels = async () => {
    try {
      const data = await fetchClient("/omni/models");
      setAvailableModels(data.models || []);
    } catch (err) { console.error("Failed to fetch models:", err); }
  };
  useEffect(() => { fetchModels(); }, []);

  // Handle clicking a file or directory
  const handleItemClick = async (item: FileItem) => {
    if (item.isDir) {
      const newPath = currentPath === "." ? item.path : `${currentPath}/${item.path.split("/").pop()}`;
      setCurrentPath(newPath);
    } else {
      try {
        const data = await fetchClient(
          `/omni/files?orgId=${activeOrgId}&action=read&path=${encodeURIComponent(item.path)}`
        );
        setActiveFilePath(item.path);
        setActiveFileContent(data.content || "");
        setIsDiffMode(false);
        setActiveTab("editor");
      } catch (err) {
        console.error("Failed to read file:", err);
      }
    }
  };

  // Navigate back to the parent directory
  const handleGoUp = () => {
    if (currentPath === "." || currentPath === "") return;
    const parts = currentPath.split("/");
    parts.pop();
    const parent = parts.length === 0 ? "." : parts.join("/");
    setCurrentPath(parent);
  };

  // Save Agent Configuration
  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingSettings(true);
    try {
      await fetchClient("/omni/master", {
        method: "PATCH",
        body: JSON.stringify({
          orgId: activeOrgId,
          name: agentName,
          aiModel: agentModel,
          aiSystemPrompt: agentPrompt,
          maxLoops: agentMaxLoops
        })
      });
      toast.success("¡Configuración del Omni Agent guardada con éxito!");
      fetchRuns();
    } catch (err: any) {
      toast.error(`Error al guardar: ${err.message}`);
    } finally {
      setIsSavingSettings(false);
    }
  };

  // Execute a codebase command / delegation
  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isExecuting) return;

    setIsExecuting(true);
    setCompilerLogs("Iniciando ejecución del Omni Master Agent...\nEstableciendo túnel con el sistema de archivos...\n");
    setActiveTab("logs");

    try {
      const data = await fetchClient("/omni/master", {
        method: "POST",
        body: JSON.stringify({ orgId: activeOrgId, prompt })
      });
      
      if (data.success) {
        setPrompt("");
        // Reload history
        await fetchRuns();
        
        // Find compiling/building stdout in trace steps
        const trace = data.trace || [];
        let logsCombined = "";
        trace.forEach((step: TraceStep) => {
          if (step.tool === "codebase_run_build") {
            logsCombined += `[Compilación Paso ${step.step}]:\n${step.arguments?.output || ""}\n\n`;
          }
        });
        
        if (logsCombined) {
          setCompilerLogs(logsCombined);
        } else {
          setCompilerLogs(`Construcción finalizada con éxito.\nRespuesta: ${data.response}`);
        }
        
        // Load latest run as selected
        if (data.trace) {
          const mockRun: RunLog = {
            id: "temp-latest",
            botId: "",
            triggerSource: "OMNI_CONSOLE",
            status: "SUCCESS",
            inputPayload: JSON.stringify({ prompt }),
            outputResult: data.response,
            loopCount: trace.length,
            tokenUsage: trace.length * 1200,
            costUsd: trace.length * 0.005,
            latencyMs: trace.reduce((acc: number, t: any) => acc + (t.latencyMs || 0), 0),
            executionTrace: JSON.stringify(trace),
            createdAt: new Date().toISOString()
          };
          setSelectedRun(mockRun);
        }
        
        // Refresh codebase file view
        fetchFiles(currentPath);
      } else {
        toast.error(`Error al ejecutar directiva: ${data.response || data.error}`);
        setCompilerLogs(`Error de Compilación/Ejecución:\n${data.response || data.error}`);
      }
    } catch (err: any) {
      console.error(err);
      setCompilerLogs(`Error de conexión con la API de ejecución:\n${err.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  // Inspect code modifications in side-by-side diff
  const handleInspectDiff = async (filePath: string, newContent: string) => {
    try {
      // Get the original file content (pre-write)
      const data = await fetchClient(
        `/omni/files?orgId=${activeOrgId}&action=read&path=${encodeURIComponent(filePath)}`
      );
      const originalContent = data.content;
      
      const ext = filePath.split(".").pop() || "";
      let language = "plaintext";
      if (["js", "jsx"].includes(ext)) language = "javascript";
      else if (["ts", "tsx"].includes(ext)) language = "typescript";
      else if (ext === "json") language = "json";
      
      setDiffOriginal(originalContent);
      setDiffModified(newContent);
      setDiffPath(filePath);
      setDiffLanguage(language);
      setIsDiffMode(true);
      setActiveTab("diff");
    } catch (err) {
      console.error("Failed to read original content for diff view:", err);
    }
  };

  // Parse trace items safely
  const parsedTrace: TraceStep[] = selectedRun?.executionTrace
    ? JSON.parse(selectedRun.executionTrace)
    : [];

  const parsedInput = selectedRun?.inputPayload
    ? (typeof selectedRun.inputPayload === "string" ? JSON.parse(selectedRun.inputPayload) : selectedRun.inputPayload)
    : null;

  const filteredFiles = filesList.filter((f) =>
    f.path.toLowerCase().includes(fileSearch.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-[#07071a] text-zinc-100 font-sans">
      
      {/* Glow Backdrop */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-violet-600/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-10 left-1/3 w-[400px] h-[400px] bg-fuchsia-600/5 rounded-full blur-[100px]"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-violet-500/10 bg-slate-950/60 backdrop-blur-xl shadow-md">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl animate-pulse">🌌</span>
            <span className="bg-gradient-to-r from-violet-400 via-indigo-300 to-fuchsia-400 bg-clip-text text-transparent">
              Omni Command Center
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Autónomo. Código en tiempo real, compilación directa y despliegues controlados a ramas de desarrollo.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-violet-500/20 shadow-inner">
            <span className={`w-2.5 h-2.5 rounded-full ${isExecuting ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
            <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
              {isExecuting ? "Looping..." : "Control Activo"}
            </span>
          </div>

          <div className="text-xs text-zinc-400">
            Organización: <span className="text-violet-300 font-semibold">{activeOrg?.name}</span>
          </div>
        </div>
      </header>

      {/* Console Panels Grid */}
      <div className="relative z-10 flex-1 flex overflow-hidden p-6 gap-6 min-h-0">
        
        {/* Left Column: File Tree Browser */}
        <section className="w-1/4 min-w-[250px] max-w-[340px] flex flex-col h-full bg-slate-950/40 backdrop-blur-md border border-violet-500/10 rounded-2xl p-4 shadow-[0_4px_30px_rgba(0,0,0,0.4)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400">Navegador del Código</h3>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowNewFileInput(!showNewFileInput)}
                className="text-[10px] px-2 py-0.5 bg-emerald-950/50 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/20 rounded transition-all"
              >
                + Nuevo
              </button>
              {currentPath !== "." && currentPath !== "" && (
                <button 
                  onClick={handleGoUp}
                  className="text-[10px] px-2 py-0.5 bg-violet-950/50 hover:bg-violet-900/60 text-violet-300 border border-violet-500/20 rounded transition-all"
                >
                  ← Subir
                </button>
              )}
            </div>
          </div>

          {/* Current Path Indicator */}
          <div className="bg-slate-900/80 border border-zinc-800 rounded px-2.5 py-1.5 text-[10px] text-zinc-400 truncate mb-3 select-all">
            📂 {currentPath === "." ? "root" : currentPath}
          </div>

          {/* New File Input */}
          {showNewFileInput && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!newFileName.trim()) return;
                try {
                  const relativePath = currentPath === "." ? newFileName.trim() : `${currentPath}/${newFileName.trim()}`;
                  await fetchClient("/omni/files", {
                    method: "POST",
                    body: JSON.stringify({
                      path: relativePath,
                      content: "// Scaffolded by Omni Command Center\n"
                    })
                  });
                  setNewFileName("");
                  setShowNewFileInput(false);
                  fetchFiles(currentPath);
                } catch (err: any) {
                  toast.error(`Error al crear archivo: ${err.message}`);
                }
              }}
              className="mb-3 flex gap-2"
            >
              <input
                type="text"
                placeholder="nombre_archivo.ts"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                className="flex-1 bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none"
                autoFocus
              />
              <button
                type="submit"
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold"
              >
                Crear
              </button>
            </form>
          )}

          {/* Search bar */}
          <input
            type="text"
            placeholder="Buscar archivos..."
            value={fileSearch}
            onChange={(e) => setFileSearch(e.target.value)}
            className="w-full bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 mb-3 focus:outline-none transition-colors"
          />

          {/* File listing */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
            {filteredFiles.length === 0 ? (
              <div className="text-xs text-zinc-600 text-center py-6">No se encontraron archivos</div>
            ) : (
              filteredFiles.map((file) => {
                const isActive = file.path === activeFilePath;
                return (
                  <div
                    key={file.path}
                    onClick={() => handleItemClick(file)}
                    className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-xs transition-all cursor-pointer group relative ${
                      isActive
                        ? "bg-gradient-to-r from-violet-950/80 to-indigo-950/80 border-l-2 border-violet-500 text-white shadow-md shadow-violet-500/5"
                        : "hover:bg-slate-900/80 text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="shrink-0 text-sm">
                        {file.isDir ? "📁" : "📄"}
                      </span>
                      <span className="truncate">{file.path.split("/").pop()}</span>
                    </div>
                    {file.isDir ? (
                      <span className="text-[9px] text-zinc-600 font-bold uppercase tracking-widest">Entrar</span>
                    ) : (
                      <button
                        type="button"
                        onClick={async (e) => {
                          e.stopPropagation();
                          if (confirm(`¿Estás seguro de que deseas eliminar el archivo: ${file.path.split("/").pop()}?`)) {
                            try {
                              await fetchClient(`/omni/files?path=${encodeURIComponent(file.path)}`, {
                                method: "DELETE"
                              });
                              if (activeFilePath === file.path) {
                                setActiveFilePath("");
                                setActiveFileContent("");
                              }
                              fetchFiles(currentPath);
                            } catch (err: any) {
                              toast.error(`Error al eliminar archivo: ${err.message}`);
                            }
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 text-xs px-1.5 transition-opacity duration-200"
                        title="Eliminar archivo"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* Center Column: Monaco Code Viewer, Diff Inspector, & Output Console */}
        <section className="flex-1 h-full flex flex-col min-w-0 bg-slate-950/30 backdrop-blur-md border border-violet-500/10 rounded-2xl p-5 shadow-[0_4px_30px_rgba(0,0,0,0.3)]">
          {/* Tabs header */}
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab("editor")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                  activeTab === "editor"
                    ? "bg-slate-900 border-violet-500/30 text-violet-300 shadow-md shadow-violet-500/5"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                ✏️ Editor de Código
              </button>
              <button
                onClick={() => setActiveTab("diff")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                  activeTab === "diff"
                    ? "bg-slate-900 border-violet-500/30 text-violet-300 shadow-md shadow-violet-500/5"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                🔎 Inspector de Cambios
              </button>
              <button
                onClick={() => setActiveTab("logs")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                  activeTab === "logs"
                    ? "bg-slate-900 border-violet-500/30 text-violet-300 shadow-md shadow-violet-500/5"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                📟 Log de Compilación
              </button>
              <button
                onClick={() => setActiveTab("settings")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                  activeTab === "settings"
                    ? "bg-slate-900 border-violet-500/30 text-violet-300 shadow-md shadow-violet-500/5"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                ⚙️ Configuración del Agente
              </button>
            </div>
            
            {activeTab === "editor" && activeFilePath && (
              <button
                onClick={handleSaveFile}
                disabled={isSavingFile}
                className="px-4 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-md hover:shadow-emerald-500/20 disabled:opacity-50 transition-all flex items-center gap-1 cursor-pointer"
              >
                {isSavingFile ? "Guardando..." : "💾 Guardar Archivo"}
              </button>
            )}

            {activeTab === "diff" && diffPath && (
              <span className="text-[10px] bg-violet-950/80 border border-violet-500/20 text-violet-300 px-2 py-0.5 rounded uppercase tracking-wider font-mono">
                Diff: {diffPath.split("/").pop()}
              </span>
            )}
          </div>

          {/* Active Tab Panel Container */}
          <div className="flex-1 min-h-0 relative rounded-xl overflow-hidden border border-zinc-800">
            {activeTab === "editor" && (
              activeFilePath ? (
                <MonacoEditor
                  value={activeFileContent}
                  onChange={(val) => setActiveFileContent(val || "")}
                  language={
                    activeFilePath.endsWith(".json")
                      ? "json"
                      : activeFilePath.endsWith(".md")
                      ? "markdown"
                      : "typescript"
                  }
                  readOnly={false}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/30 text-zinc-500 p-6">
                  <span className="text-3xl mb-3">📁</span>
                  <p className="text-xs">Selecciona un archivo en la barra lateral para inspeccionar el código.</p>
                </div>
              )
            )}

            {activeTab === "diff" && (
              diffPath ? (
                <DiffViewer
                  original={diffOriginal}
                  modified={diffModified}
                  language={diffLanguage}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/30 text-zinc-500 p-6">
                  <span className="text-3xl mb-3">🔎</span>
                  <p className="text-xs">No hay cambios cargados en el Inspector de Cambios.</p>
                  <p className="text-[10px] text-zinc-600 mt-1 max-w-[280px] text-center">
                    Ejecuta una directiva y selecciona "Ver Diff" en el historial de trazas de un cambio.
                  </p>
                </div>
              )
            )}

            {activeTab === "logs" && (
              <pre className="absolute inset-0 p-4 font-mono text-[11px] text-indigo-200 bg-black/95 overflow-y-auto leading-relaxed select-text whitespace-pre-wrap selection:bg-violet-500/30">
                {compilerLogs || "Sin actividad de compilación reciente."}
              </pre>
            )}

            {activeTab === "settings" && (
              <form onSubmit={handleSaveConfig} className="absolute inset-0 p-6 bg-slate-950/95 overflow-y-auto space-y-5 leading-relaxed text-sm text-zinc-300">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2">⚙️ Configuración del Master Agent</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Nombre del Agente</label>
                    <input
                      type="text"
                      value={agentName}
                      onChange={(e) => setAgentName(e.target.value)}
                      className="w-full bg-slate-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500/50"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Límite de Iteraciones (Max Loops)</label>
                    <input
                      type="number"
                      value={agentMaxLoops}
                      min={1}
                      max={20}
                      onChange={(e) => setAgentMaxLoops(parseInt(e.target.value, 10))}
                      className="w-full bg-slate-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500/50 font-bold"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Modelo de IA</label>
                    <select
                      value={agentModel}
                      onChange={(e) => setAgentModel(e.target.value)}
                      className="w-full bg-slate-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500/50"
                    >
                      {availableModels.length > 0 ? (
                        <>
                          {["openai","gemini","anthropic","xai","openrouter"].map(provider => {
                            const group = availableModels.filter((m: any) => m.provider === provider);
                            if (group.length === 0) return null;
                            const label = {openai:"OpenAI",gemini:"Google Gemini",anthropic:"Anthropic Claude",xai:"xAI Grok",openrouter:"OpenRouter"}[provider];
                            return (
                              <optgroup key={provider} label={label}>
                                {group.map((m: any) => (
                                  <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                              </optgroup>
                            );
                          })}
                        </>
                      ) : (
                        <>
                          <option value="gpt-4o-mini">OpenAI GPT-4o Mini</option>
                          <option value="gpt-4o">OpenAI GPT-4o</option>
                          <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Instrucciones del Sistema (aiSystemPrompt)</label>
                  <p className="text-[10px] text-zinc-500 mb-2 leading-relaxed">
                    Personaliza la personalidad del Master Agent, las directrices del proyecto o límites específicos. Las reglas de salida JSON y las herramientas se inyectarán automáticamente al final.
                  </p>
                  <textarea
                    value={agentPrompt}
                    onChange={(e) => setAgentPrompt(e.target.value)}
                    rows={6}
                    className="w-full bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded-xl px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none resize-none font-mono"
                  />
                </div>

                <div className="flex justify-end pt-3">
                  <button
                    type="submit"
                    disabled={isSavingSettings}
                    className="px-6 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-xs font-bold text-white shadow-lg hover:shadow-violet-500/20 hover:brightness-110 disabled:opacity-50 transition-all"
                  >
                    {isSavingSettings ? "Guardando..." : "💾 Guardar Configuración"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>

        {/* Right Column: Chat Console, Trace Steps Timeline & Run History */}
        <section className="w-1/3 min-w-[340px] max-w-[460px] flex flex-col h-full gap-5">
          
          {/* Right Panel Tabs */}
          <div className="flex bg-slate-950/40 backdrop-blur-md border border-violet-500/10 rounded-xl p-1 gap-1 shrink-0">
            <button
              type="button"
              onClick={() => setRightPanelTab("agent")}
              className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${
                rightPanelTab === "agent"
                  ? "bg-slate-900 text-violet-300 border border-violet-500/20"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              💬 Omni Agent
            </button>
            <button
              type="button"
              onClick={() => setRightPanelTab("git")}
              className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${
                rightPanelTab === "git"
                  ? "bg-slate-900 text-violet-300 border border-violet-500/20"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              🔌 Control Git
            </button>
          </div>

          {rightPanelTab === "agent" ? (
            <>
              {/* Loop/Thought Execution Monitor */}
              <div className="flex-1 min-h-0 flex flex-col bg-slate-950/40 backdrop-blur-md border border-violet-500/10 rounded-2xl p-4 shadow-[0_4px_30px_rgba(0,0,0,0.3)]">
                
                {/* Top Navigation for Execution History vs Active Trace */}
                <div className="flex border-b border-zinc-800 pb-2 mb-3 items-center justify-between shrink-0">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400">Monitor de Ejecución</h3>
                  <div className="text-[10px] text-zinc-500 font-mono">
                    {selectedRun ? `#${selectedRun.id.substring(0, 8)}` : "Ningún run seleccionado"}
                  </div>
                </div>

                {/* Run Selection Dropdown */}
                {runs.length > 0 && (
                  <div className="mb-3 shrink-0">
                    <select
                      value={selectedRun?.id || ""}
                      onChange={(e) => {
                        const r = runs.find((item) => item.id === e.target.value);
                        if (r) setSelectedRun(r);
                      }}
                      className="w-full bg-slate-900 border border-zinc-800 text-zinc-200 text-xs px-2.5 py-1.5 rounded focus:outline-none focus:border-violet-500"
                    >
                      {runs.map((run) => (
                        <option key={run.id} value={run.id}>
                          {new Date(run.createdAt).toLocaleTimeString()} - {run.status} ({run.loopCount} pasos)
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Active Trace Timeline */}
                <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar min-h-0">
                  {isExecuting ? (
                    <div className="flex flex-col items-center justify-center h-full py-12">
                      
                      {/* Glowing Portal Loading Spinner */}
                      <div className="relative w-24 h-24 mb-6">
                        <div className="absolute inset-0 rounded-full border-4 border-violet-500/20"></div>
                        <div className="absolute inset-0 rounded-full border-4 border-t-violet-400 animate-spin"></div>
                        <div className="absolute inset-2 rounded-full border-2 border-indigo-500/10"></div>
                        <div className="absolute inset-2 rounded-full border-2 border-b-fuchsia-400 animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }}></div>
                        <div className="absolute inset-0 rounded-full bg-violet-500/10 blur-xl animate-pulse"></div>
                      </div>

                      <h4 className="text-sm font-bold text-violet-300 animate-pulse text-center">Ejecutando Directiva de Código</h4>
                      <p className="text-[11px] text-zinc-500 text-center mt-2 max-w-[240px]">
                        El Omni Agent está leyendo, editando archivos, y corriendo tests de compilación de TypeScript...
                      </p>
                    </div>
                  ) : selectedRun ? (
                    <div className="space-y-4">
                      {/* Display Target Request Prompt */}
                      {parsedInput && (
                        <div className="bg-slate-900/60 border border-zinc-800 rounded-xl p-3 text-xs leading-relaxed text-zinc-300">
                          <span className="text-[10px] font-bold text-indigo-400 block mb-1 uppercase tracking-widest">Instrucción:</span>
                          {parsedInput.prompt}
                        </div>
                      )}

                      {/* Timeline steps */}
                      <div className="relative border-l border-zinc-800 ml-3 pl-4 space-y-4">
                        {parsedTrace.map((step, idx) => (
                          <div key={idx} className="relative">
                            
                            {/* Dot on line */}
                            <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-violet-500 bg-zinc-950 shadow-[0_0_8px_rgba(139,92,246,0.8)]" />

                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[10px] text-zinc-500">
                                <span className="font-semibold text-zinc-300 uppercase tracking-widest">Paso {step.step}: {step.tool}</span>
                                <span>{step.latencyMs}ms</span>
                              </div>

                              <p className="text-xs text-zinc-400 leading-relaxed italic bg-zinc-900/30 p-2 rounded-lg border border-zinc-800/40">
                                "{step.thought}"
                              </p>

                              {/* Action Parameters and tool specific triggers */}
                              {step.tool === "codebase_write_file" && step.arguments?.path && (
                                <div className="flex items-center justify-between bg-violet-950/20 border border-violet-500/10 rounded-lg px-2.5 py-1.5">
                                  <span className="text-[10px] font-mono text-violet-300 truncate max-w-[200px]" title={step.arguments.path}>
                                    ✏️ Escribió: {step.arguments.path.split("/").pop()}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleInspectDiff(step.arguments.path, step.arguments.content || "")}
                                    className="text-[10px] font-bold text-fuchsia-400 hover:text-fuchsia-300 cursor-pointer"
                                  >
                                    Ver Diff
                                  </button>
                                </div>
                              )}

                              {step.tool === "codebase_read_file" && step.arguments?.path && (
                                <div className="bg-indigo-950/20 border border-indigo-500/10 rounded-lg px-2.5 py-1.5 text-[10px]">
                                  <span className="font-mono text-indigo-300">📖 Leyó: {step.arguments.path}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Summary Result Box */}
                      <div className="bg-slate-900/60 border border-violet-500/20 rounded-xl p-3.5 mt-2">
                        <span className="text-[10px] font-bold text-fuchsia-400 block mb-1 uppercase tracking-widest">Resumen del Omni Agent:</span>
                        <p className="text-xs text-zinc-300 leading-relaxed leading-5">
                          {selectedRun.outputResult}
                        </p>

                        {/* Stats metrics */}
                        <div className="flex gap-4 mt-3 pt-3 border-t border-zinc-800 text-[10px] text-zinc-500">
                          <div>Uso Tokens: <span className="text-zinc-400 font-semibold">{selectedRun.tokenUsage}</span></div>
                          <div>Costo Aprox: <span className="text-zinc-400 font-semibold">${selectedRun.costUsd.toFixed(4)}</span></div>
                          <div>Latencia: <span className="text-zinc-400 font-semibold">{(selectedRun.latencyMs / 1000).toFixed(2)}s</span></div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-zinc-600 py-12 text-center text-xs">
                      <span className="text-2xl mb-2">🔭</span>
                      No hay ejecuciones registradas.<br />Envía una directiva para iniciar.
                    </div>
                  )}
                </div>
              </div>

              {/* Supervisor Prompt / Chat Input Console */}
              <div className="bg-slate-950/40 backdrop-blur-md border border-violet-500/10 rounded-2xl p-4 shadow-[0_4px_30px_rgba(0,0,0,0.3)] shrink-0">
                <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400 mb-2.5">
                  Instrucciones del Supervisor
                </h3>
                
                <form onSubmit={handleExecute} className="space-y-2">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    disabled={isExecuting}
                    placeholder="Escribe una directiva... ej: 'Crea una ruta en api/test que devuelva un saludo o añade un campo al modelo'"
                    className="w-full h-20 bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded-xl px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none transition-colors resize-none disabled:opacity-50"
                  />

                  <button
                    type="submit"
                    disabled={isExecuting || !prompt.trim()}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-xs font-bold text-white shadow-lg hover:shadow-violet-500/20 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {isExecuting ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-t-white border-white/20 rounded-full animate-spin" />
                        Ejecutando Directiva...
                      </>
                    ) : (
                      <>
                        <span>⚡ Enviar a Omni Agent</span>
                      </>
                    )}
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 min-h-0 bg-slate-950/40 backdrop-blur-md border border-violet-500/10 rounded-2xl p-4">
              <GitPanel botId={botId || ""} onProposalSuccess={handleProposalSuccess} />
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
