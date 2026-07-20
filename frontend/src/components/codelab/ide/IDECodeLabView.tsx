"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { useState, useEffect, useCallback } from "react";
import { Terminal as TerminalIcon, Monitor, Code2, Loader2 } from "lucide-react";

import ActivityBar, { ActivityBarItem } from "@/components/codelab/ide/ActivityBar";
import Sidebar from "@/components/codelab/ide/Sidebar";
import EditorArea from "@/components/codelab/ide/EditorArea";
import AgentPanel from "@/components/codelab/ide/AgentPanel";
import StatusBar, { StatusBarCursor } from "@/components/codelab/ide/StatusBar";
import { TreeNode } from "@/components/codelab/ide/FileExplorerTree";
import { EditorTab } from "@/components/codelab/ide/EditorTabs";
import OmniConsoleView from "@/components/admin/views/OmniConsoleView";

interface FileItem {
  path: string;
  isDir: boolean;
  language: string;
}

function getLanguage(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript",
    js: "javascript", jsx: "javascript",
    json: "json", css: "css", html: "html",
    md: "markdown", py: "python", go: "go",
    rs: "rust", yaml: "yaml", yml: "yaml",
    sh: "shell", bash: "shell", dockerfile: "dockerfile",
  };
  return map[ext] || "plaintext";
}

export default function IDECodeLabView() {
  const [viewMode, setViewMode] = useState<"ide" | "classic">("ide");
  const [activeSidebarPanel, setActiveSidebarPanel] = useState<ActivityBarItem>("explorer");
  const [activeFilePath, setActiveFilePath] = useState("");
  const [activeFileContent, setActiveFileContent] = useState("");
  const [openTabs, setOpenTabs] = useState<EditorTab[]>([]);
  const [fileCache, setFileCache] = useState<Record<string, string>>({});
  const [cursor, setCursor] = useState<StatusBarCursor>({ line: 1, col: 1 });
  const [terminalOutput, setTerminalOutput] = useState("");
  const [terminalTab, setTerminalTab] = useState<"terminal" | "problems" | "output" | "debug">("terminal");
  const [isExecuting, setIsExecuting] = useState(false);
  const [filesList, setFilesList] = useState<FileItem[]>([]);
  const [gitStatusFiles, setGitStatusFiles] = useState<{ path: string; status: string }[]>([]);
  const [gitBranch, setGitBranch] = useState("main");
  const [editMode, setEditMode] = useState<"direct" | "proposal">("direct");
  const [autoBranch, setAutoBranch] = useState(true);
  const [requireApproval, setRequireApproval] = useState(false);
  const [model, setModel] = useState("openai/gpt-4o");
  const [maxLoops, setMaxLoops] = useState(8);
  const [gitRepoUrl, setGitRepoUrl] = useState("");
  const [traces, setTraces] = useState<any[]>([]);
  const [proposals, setProposals] = useState<any[]>([]);
  const [availableModels, setAvailableModels] = useState<{ id: string; name: string; provider: string }[]>([]);
  const [agentId, setAgentId] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: agents, isLoading } = useQuery({
    queryKey: ["agentsList"],
    queryFn: async () => { const res = await fetchClient("/agents"); return res.items ?? res; },
  });

  useEffect(() => {
    if (agents && agents.length > 0 && !agentId) {
      setAgentId(agents[0]?.id || "");
    }
  }, [agents, agentId]);

  const buildTree = useCallback((files: FileItem[], gitFiles: { path: string; status: string }[]): TreeNode[] => {
    const gitMap = new Map<string, string>();
    gitFiles.forEach((f) => gitMap.set(f.path, f.status));

    const result: TreeNode[] = [];
    const dirMap = new Map<string, TreeNode>();

    files.forEach((file) => {
      const parts = file.path.split("/");

      for (let i = 0; i < parts.length; i++) {
        const subPath = parts.slice(0, i + 1).join("/");
        const isLast = i === parts.length - 1;

        if (!dirMap.has(subPath)) {
          const node: TreeNode = {
            name: parts[i],
            path: subPath,
            isDir: !isLast || file.isDir,
            language: isLast ? file.language : undefined,
            gitStatus: (gitMap.get(subPath) as any) || null,
            children: [],
          };
          dirMap.set(subPath, node);

          if (i === 0) {
            result.push(node);
          } else {
            const parentPath = parts.slice(0, i).join("/");
            const parent = dirMap.get(parentPath);
            if (parent && parent.children) {
              parent.children.push(node);
            }
          }
        } else if (isLast && !file.isDir) {
          const node = dirMap.get(subPath)!;
          node.language = file.language;
          node.gitStatus = (gitMap.get(subPath) as any) || null;
        }
      }
    });

    function sortChildren(node: TreeNode) {
      if (node.children) {
        node.children.sort((a, b) => {
          if (a.isDir && !b.isDir) return -1;
          if (!a.isDir && b.isDir) return 1;
          return a.name.localeCompare(b.name);
        });
        node.children.forEach(sortChildren);
      }
    }
    result.forEach(sortChildren);

    return result;
  }, []);

  const tree = buildTree(filesList, gitStatusFiles);

  const fetchFiles = useCallback(async () => {
    try {
      const data = await fetchClient(`/omni/files?action=list&path=.`);
      const sorted = (data.files || []).sort((a: FileItem, b: FileItem) => {
        if (a.isDir && !b.isDir) return -1;
        if (!a.isDir && a.isDir) return 1;
        return a.path.localeCompare(b.path);
      });
      setFilesList(sorted);
    } catch (err) {
      console.error("Failed to fetch files:", err);
    }
  }, []);

  const fetchGitStatus = useCallback(async () => {
    try {
      const data = await fetchClient("/omni/git-status");
      setGitStatusFiles(data.files || []);
      if (data.branch) setGitBranch(data.branch);
    } catch (err) {
      console.error("Failed to fetch git status:", err);
    }
  }, []);

  const fetchModels = useCallback(async () => {
    try {
      const data = await fetchClient("/omni/models");
      setAvailableModels(data.models || []);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
    fetchGitStatus();
    fetchModels();
  }, [fetchFiles, fetchGitStatus, fetchModels]);

  const handleSelectFile = useCallback(async (path: string) => {
    if (activeFilePath === path) return;

    if (!openTabs.find((t) => t.path === path)) {
      setOpenTabs((prev) => [...prev, { path, name: path.split("/").pop() || path, isDirty: false }]);
    }

    setActiveFilePath(path);

    if (fileCache[path]) {
      setActiveFileContent(fileCache[path]);
      return;
    }

    try {
      const data = await fetchClient(`/omni/files?action=read&path=${encodeURIComponent(path)}`);
      const content = data.content || "";
      setActiveFileContent(content);
      setFileCache((prev) => ({ ...prev, [path]: content }));
    } catch (err) {
      console.error("Failed to read file:", err);
    }
  }, [activeFilePath, openTabs, fileCache]);

  const handleContentChange = useCallback((value: string | undefined) => {
    if (value === undefined) return;
    setActiveFileContent(value);
    setFileCache((prev) => ({ ...prev, [activeFilePath]: value }));
    setOpenTabs((prev) =>
      prev.map((t) => (t.path === activeFilePath ? { ...t, isDirty: true } : t))
    );
  }, [activeFilePath]);

  const handleCloseTab = useCallback((path: string) => {
    setOpenTabs((prev) => {
      const filtered = prev.filter((t) => t.path !== path);
      if (path === activeFilePath && filtered.length > 0) {
        const idx = prev.findIndex((t) => t.path === path);
        const newActive = filtered[Math.min(idx, filtered.length - 1)];
        setTimeout(() => handleSelectFile(newActive.path), 0);
      }
      if (filtered.length === 0) {
        setActiveFilePath("");
        setActiveFileContent("");
      }
      return filtered;
    });
  }, [activeFilePath, handleSelectFile]);

  const handleExecute = useCallback(async (prompt: string) => {
    setIsExecuting(true);
    setTerminalTab("terminal");
    setTerminalOutput("$ npx tsc --noEmit\nInitiating Omni Master Agent execution...\n");

    try {
      const data = await fetchClient("/omni/master", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      });

      if (data.success) {
        const trace = data.trace || [];
        setTraces(trace);
        setTerminalOutput((prev) => prev + `\nExecution complete. ${trace.length} steps processed.\nResult: ${data.response}`);

        if (data.response) {
          setTraces((prev) => [...prev, {
            step: trace.length + 1,
            thought: "Execution finished",
            tool: "complete",
            arguments: { response: data.response },
            timestamp: new Date().toISOString(),
            latencyMs: 0,
          }]);
        }

        fetchFiles();
        fetchGitStatus();
        queryClient.invalidateQueries({ queryKey: ["agentsList"] });
      } else {
        setTerminalOutput((prev) => prev + `\nError: ${data.response || data.error || "Unknown error"}`);
      }
    } catch (err: any) {
      setTerminalOutput((prev) => prev + `\nError: ${err.message || "Connection error"}`);
    } finally {
      setIsExecuting(false);
    }
  }, [fetchFiles, fetchGitStatus, queryClient]);

  const handleRenameFile = useCallback(async (path: string) => {
    const newName = prompt("New name:", path.split("/").pop());
    if (!newName) return;
    try {
      const dir = path.split("/").slice(0, -1).join("/");
      const newPath = dir ? `${dir}/${newName}` : newName;
      const content = fileCache[path] || "";
      await fetchClient("/omni/files", {
        method: "POST",
        body: JSON.stringify({ path: newPath, content }),
      });
      await fetchClient(`/omni/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });
      setFileCache((prev) => { const n = { ...prev }; delete n[path]; n[newPath] = content; return n; });
      setOpenTabs((prev) => prev.map((t) => t.path === path ? { ...t, path: newPath, name: newName } : t));
      if (activeFilePath === path) setActiveFilePath(newPath);
      fetchFiles();
    } catch (err: any) {
      console.error("Failed to rename:", err);
    }
  }, [fileCache, activeFilePath, fetchFiles]);

  const handleDeleteFile = useCallback(async (path: string) => {
    if (!confirm(`Delete ${path.split("/").pop()}?`)) return;
    try {
      await fetchClient(`/omni/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });
      setFileCache((prev) => { const n = { ...prev }; delete n[path]; return n; });
      handleCloseTab(path);
      fetchFiles();
      fetchGitStatus();
    } catch (err: any) {
      console.error("Failed to delete:", err);
    }
  }, [fetchFiles, fetchGitStatus, handleCloseTab]);

  const handleNewFile = useCallback(async (parentPath: string) => {
    const name = prompt("File name:", "new.ts");
    if (!name) return;
    const dirPath = parentPath === "." ? "" : parentPath;
    const fullPath = dirPath ? `${dirPath}/${name}` : name;
    try {
      await fetchClient("/omni/files", {
        method: "POST",
        body: JSON.stringify({ path: fullPath, content: "// Created by CodeLab\n" }),
      });
      fetchFiles();
      handleSelectFile(fullPath);
    } catch (err: any) {
      console.error("Failed to create file:", err);
    }
  }, [fetchFiles, handleSelectFile]);

  const handleNewFolder = useCallback(async (parentPath: string) => {
    const name = prompt("Folder name:", "new-folder");
    if (!name) return;
    const dirPath = parentPath === "." ? "" : parentPath;
    const fullPath = dirPath ? `${dirPath}/${name}` : name;
    try {
      await fetchClient("/omni/files", {
        method: "POST",
        body: JSON.stringify({ path: fullPath, content: "" }),
      });
      fetchFiles();
    } catch (err: any) {
      console.error("Failed to create folder:", err);
    }
  }, [fetchFiles]);

  const handleApplyProposal = useCallback(async (id: string) => {
    try {
      await fetchClient(`/omni/proposals/${id}/apply`, { method: "POST" });
      setProposals((prev) => prev.filter((p) => p.id !== id));
      fetchFiles();
      fetchGitStatus();
    } catch (err) { console.error("Failed to apply proposal:", err); }
  }, [fetchFiles, fetchGitStatus]);

  const handleRejectProposal = useCallback(async (id: string) => {
    try {
      await fetchClient(`/omni/proposals/${id}/reject`, { method: "POST" });
      setProposals((prev) => prev.filter((p) => p.id !== id));
    } catch (err) { console.error("Failed to reject proposal:", err); }
  }, []);

  const handleApplyAllProposals = useCallback(async () => {
    try {
      // Backend "apply all" is scoped to a branch session (POST /omni/branches/{id}/apply-all),
      // which this view doesn't track — apply each listed proposal via the per-proposal route.
      await Promise.all(
        proposals.map((p) => fetchClient(`/omni/proposals/${p.id}/apply`, { method: "POST" }))
      );
      setProposals([]);
      fetchFiles();
      fetchGitStatus();
    } catch (err) { console.error("Failed to apply all proposals:", err); }
  }, [proposals, fetchFiles, fetchGitStatus]);

  const activeLanguage = activeFilePath ? getLanguage(activeFilePath) : "plaintext";

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3rem)] gap-3 bg-[#1e1e1e]">
        <Loader2 className="w-8 h-8 animate-spin text-[#007acc]" />
        <p className="text-[13px] text-[#858585]">Loading CodeLab...</p>
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3rem)] bg-[#1e1e1e] text-center gap-4">
        <TerminalIcon size={48} className="text-[#858585]" />
        <h2 className="text-lg font-bold text-[#cccccc]">Code Lab & DevOps</h2>
        <p className="text-[13px] text-[#858585] max-w-md">
          Create an agent in the Agent Studio to use code generation.
        </p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col bg-[#1e1e1e] text-white overflow-hidden">
      <div className="flex items-center justify-between bg-[#323233] border-b border-[#1e1e1e] px-3 py-1 shrink-0">
        <div className="flex items-center gap-2">
          <Code2 size={16} className="text-[#007acc]" />
          <span className="text-[13px] font-semibold text-[#cccccc]">CodeLab IDE</span>
        </div>
        <div className="flex items-center gap-1">
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="bg-[#3c3c3c] border border-[#454545] text-[#cccccc] text-[12px] rounded px-2 py-0.5 outline-none focus:border-[#007acc]"
          >
            {agents.map((a: any) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setViewMode("ide")}
            className={`px-2 py-0.5 text-[11px] rounded ${viewMode === "ide" ? "bg-[#007acc] text-white" : "text-[#858585] hover:text-[#cccccc]"}`}
          >
            <Monitor size={14} className="inline mr-1" />
            IDE
          </button>
          <button
            onClick={() => setViewMode("classic")}
            className={`px-2 py-0.5 text-[11px] rounded ${viewMode === "classic" ? "bg-[#007acc] text-white" : "text-[#858585] hover:text-[#cccccc]"}`}
          >
            <TerminalIcon size={14} className="inline mr-1" />
            Classic Console
          </button>
        </div>
      </div>

      {viewMode === "classic" ? (
        <div className="flex-1 overflow-hidden p-4 bg-[#07071a]">
          <div className="border border-zinc-800 rounded-xl overflow-hidden h-full">
            <OmniConsoleView botId={agentId} />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          <ActivityBar
            active={activeSidebarPanel}
            onChange={setActiveSidebarPanel}
          />
          <Sidebar
            activePanel={activeSidebarPanel}
            tree={tree}
            activeFilePath={activeFilePath}
            onSelectFile={handleSelectFile}
            onNewFile={handleNewFile}
            onNewFolder={handleNewFolder}
            onDeleteFile={handleDeleteFile}
            onRenameFile={handleRenameFile}
            gitStatusFiles={gitStatusFiles}
            branch={gitBranch}
            editMode={editMode}
            onEditModeChange={setEditMode}
            model={model}
            onModelChange={setModel}
            maxLoops={maxLoops}
            onMaxLoopsChange={setMaxLoops}
            gitRepoUrl={gitRepoUrl}
            onGitRepoUrlChange={setGitRepoUrl}
            autoBranch={autoBranch}
            onAutoBranchChange={setAutoBranch}
            requireApproval={requireApproval}
            onRequireApprovalChange={setRequireApproval}
            availableModels={availableModels}
          />
          <EditorArea
            tabs={openTabs}
            activeFilePath={activeFilePath}
            onSelectTab={handleSelectFile}
            onCloseTab={handleCloseTab}
            fileContent={activeFileContent}
            onContentChange={handleContentChange}
            language={activeLanguage}
            terminalOutput={terminalOutput}
            problems={[]}
            terminalTab={terminalTab}
            onTerminalTabChange={setTerminalTab}
            onClearTerminal={() => setTerminalOutput("")}
            onCursorChange={(line, col) => setCursor({ line, col })}
          />
          <AgentPanel
            executing={isExecuting}
            onExecute={handleExecute}
            traces={traces}
            proposals={proposals}
            onApplyProposal={handleApplyProposal}
            onRejectProposal={handleRejectProposal}
            onApplyAllProposals={handleApplyAllProposals}
          />
        </div>
      )}
      <StatusBar
        branch={gitBranch}
        cursor={cursor}
        language={activeLanguage.charAt(0).toUpperCase() + activeLanguage.slice(1)}
        editMode={editMode}
        errorCount={0}
        warningCount={0}
      />
    </div>
  );
}
