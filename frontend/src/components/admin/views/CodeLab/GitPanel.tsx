import React, { useState, useEffect } from "react";
import { FileItem } from "@/lib/git/types";
import { fetchClient } from "@/lib/api/client";

interface RepoItem {
  id: string;
  provider: string;
  repoUrl: string;
  defaultBranch: string;
  devBranch: string;
}

interface GitPanelProps {
  botId: string;
  files?: FileItem[];
  onProposalSuccess: (branchName: string, prUrl?: string, score?: number, feedback?: string) => void;
}

export default function GitPanel({ botId, files: propFiles, onProposalSuccess }: GitPanelProps) {
  const [repos, setRepos] = useState<RepoItem[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState("");
  const [modules, setModules] = useState<any[]>([]);

  // Modified files from local git status
  const [modifiedFiles, setModifiedFiles] = useState<FileItem[]>([]);
  const [selectedFilePaths, setSelectedFilePaths] = useState<Record<string, boolean>>({});
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  
  // Repo Registration Form
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [provider, setProvider] = useState("github");
  const [accessToken, setAccessToken] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [devBranch, setDevBranch] = useState("dev");
  const [isRegistering, setIsRegistering] = useState(false);

  // Proposal Submission Form
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState("");

  const fetchModifiedFiles = async () => {
    setIsLoadingFiles(true);
    try {
      const data = await fetchClient("/omni/git-status");
      const filesList = data.files || [];
      setModifiedFiles(filesList);
      const selection: Record<string, boolean> = {};
      filesList.forEach((f: any) => {
        selection[f.path] = true;
      });
      setSelectedFilePaths(selection);
    } catch (e) {
      console.error("Failed to fetch modified files:", e);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  const handleToggleFileSelection = (path: string) => {
    setSelectedFilePaths(prev => ({ ...prev, [path]: !prev[path] }));
  };

  // Load repositories and previous modules
  const loadData = async () => {
    try {
      const reposData = await fetchClient("/git/repositories");
      const mappedRepos = (reposData || []).map((r: any) => ({
        id: r.id,
        provider: r.provider,
        repoUrl: r.repo_url || r.repoUrl,
        defaultBranch: r.default_branch || r.defaultBranch,
        devBranch: r.dev_branch || r.devBranch,
      }));
      setRepos(mappedRepos);
      if (mappedRepos.length > 0 && !selectedRepoId) {
        setSelectedRepoId(mappedRepos[0].id);
      }

      await fetchModifiedFiles();

      const modData = await fetchClient(`/git/modules?agent_id=${botId}`);
      setModules(modData.modules || []);
    } catch (e) {
      console.error("Failed to load git workspace data:", e);
    }
  };

  useEffect(() => {
    loadData();
  }, [botId]);

  const handleConnectRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl || !accessToken) return;
    setIsRegistering(true);

    try {
      await fetchClient("/git/repositories", {
        method: "POST",
        body: JSON.stringify({
          provider,
          repo_url: repoUrl,
          access_token: accessToken,
          default_branch: defaultBranch,
          dev_branch: devBranch
        })
      });

      setRepoUrl("");
      setAccessToken("");
      setShowConnectForm(false);
      await loadData();
    } catch (err: any) {
      alert(`Error al conectar: ${err.message || "Error desconocido"}`);
    } finally {
      setIsRegistering(false);
    }
  };

  const handleSubmitProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    const filesToSubmit = modifiedFiles.filter(f => selectedFilePaths[f.path]);
    if (!selectedRepoId || !title.trim() || filesToSubmit.length === 0) {
      if (filesToSubmit.length === 0) {
        setSubmissionError("Selecciona al menos un archivo modificado.");
      }
      return;
    }

    setIsSubmitting(true);
    setSubmissionError("");

    try {
      const data = await fetchClient("/git/modules", {
        method: "POST",
        body: JSON.stringify({
          repoId: selectedRepoId,
          agentId: botId,
          title: title.trim(),
          description: description.trim(),
          files: filesToSubmit
        })
      });

      setTitle("");
      setDescription("");
      onProposalSuccess(
        data.branchName,
        data.prUrl,
        data.reviewScore,
        data.reviewFeedback
      );
      await fetchModifiedFiles();
      await loadData();
    } catch (err: any) {
      setSubmissionError(err.message || "Error de conexión al enviar propuesta");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "merged":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      case "approved":
        return "bg-indigo-500/20 text-indigo-400 border-indigo-500/30";
      case "review":
        return "bg-amber-500/20 text-amber-400 border-amber-500/30";
      default:
        return "bg-zinc-800/80 text-zinc-400 border-zinc-700/50";
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-lg p-4 text-zinc-300 overflow-y-auto">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">Git Integración</h3>
        {!showConnectForm && (
          <button
            onClick={() => setShowConnectForm(true)}
            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2 py-1 rounded border border-zinc-700"
          >
            🔌 Conectar Repo
          </button>
        )}
      </div>

      {showConnectForm && (
        <form onSubmit={handleConnectRepo} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 mb-4 space-y-3">
          <h4 className="text-xs font-bold text-white">Conectar Repositorio</h4>
          
          <div>
            <label className="block text-[10px] text-zinc-500 mb-1">PROVEEDOR</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
            >
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] text-zinc-500 mb-1">REPO URL</label>
            <input
              type="text"
              placeholder="ej: https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-white"
              required
            />
          </div>

          <div>
            <label className="block text-[10px] text-zinc-500 mb-1">ACCESS TOKEN (PAT)</label>
            <input
              type="password"
              placeholder="Token de acceso personal"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-white"
              required
            />
          </div>

          <div className="flex gap-2">
            <div className="w-1/2">
              <label className="block text-[10px] text-zinc-500 mb-1">RAMA PRINCIPAL</label>
              <input
                type="text"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-white"
              />
            </div>
            <div className="w-1/2">
              <label className="block text-[10px] text-zinc-500 mb-1">RAMA DEV</label>
              <input
                type="text"
                value={devBranch}
                onChange={(e) => setDevBranch(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-white"
              />
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-1">
            <button
              type="button"
              onClick={() => setShowConnectForm(false)}
              className="px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded text-xs"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isRegistering}
              className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold"
            >
              {isRegistering ? "Conectando..." : "Conectar"}
            </button>
          </div>
        </form>
      )}

      {repos.length === 0 ? (
        <div className="bg-zinc-900/20 border border-dashed border-zinc-800 rounded-lg p-6 text-center text-xs text-zinc-500 mb-4">
          No hay repositorios configurados para esta organización.
        </div>
      ) : (
        <div className="mb-4">
          <label className="block text-[10px] text-zinc-500 mb-1">REPOSITORIO ACTIVO</label>
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-2 text-xs text-white font-medium focus:outline-none"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.provider.toUpperCase()} : {r.repoUrl.split("/").slice(-2).join("/")}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedRepoId && (
        <form onSubmit={handleSubmitProposal} className="border-t border-zinc-800 pt-4 space-y-3">
          <div className="flex justify-between items-center mb-1">
            <h4 className="text-xs font-bold text-white">Archivos Modificados</h4>
            <button 
              type="button" 
              onClick={() => fetchModifiedFiles()} 
              className="text-[9px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
            >
              🔄 Refrescar
            </button>
          </div>

          {isLoadingFiles ? (
            <div className="text-[10px] text-zinc-500 italic py-2">Detectando cambios...</div>
          ) : modifiedFiles.length === 0 ? (
            <div className="text-[10px] text-zinc-500 italic bg-zinc-900/30 border border-zinc-800/40 rounded p-3 text-center mb-2">
              No se detectaron cambios locales (Git limpio).
            </div>
          ) : (
            <div className="max-h-28 overflow-y-auto border border-zinc-800/80 rounded bg-zinc-900/40 p-2 space-y-1.5 custom-scrollbar mb-2">
              {modifiedFiles.map(f => (
                <label key={f.path} className="flex items-center gap-2 text-[10px] text-zinc-400 hover:text-white cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={!!selectedFilePaths[f.path]}
                    onChange={() => handleToggleFileSelection(f.path)}
                    className="rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-0 focus:ring-offset-0"
                  />
                  <span className="truncate" title={f.path}>{f.path}</span>
                </label>
              ))}
            </div>
          )}

          <div className="border-t border-zinc-800/60 pt-3">
            <label className="block text-[10px] text-zinc-500 mb-1">TÍTULO DEL PR</label>
            <input
              type="text"
              placeholder="ej: Feat: Agregar calificador de leads"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-2 text-xs text-white"
              required
            />
          </div>

          <div>
            <label className="block text-[10px] text-zinc-500 mb-1">DESCRIPCIÓN</label>
            <textarea
              placeholder="Detalla qué cambios realiza esta propuesta..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full h-16 bg-zinc-900 border border-zinc-800 rounded px-2.5 py-2 text-xs text-white focus:outline-none resize-none"
            />
          </div>

          {submissionError && (
            <div className="text-[10px] text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded p-2">
              {submissionError}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || modifiedFiles.filter(f => selectedFilePaths[f.path]).length === 0}
            className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-semibold rounded text-xs flex justify-center items-center gap-1.5 transition-colors cursor-pointer"
          >
            {isSubmitting ? "Enviando PR & Auditoría..." : "🚀 Proponer Cambios y Auditar"}
          </button>
        </form>
      )}

      {/* Code Modules History List */}
      <div className="border-t border-zinc-800 mt-6 pt-4">
        <h4 className="text-xs font-bold text-white mb-3">Historial de Propuestas</h4>
        <div className="space-y-3.5">
          {modules.length === 0 ? (
            <div className="text-[11px] text-zinc-600 text-center py-4">No hay propuestas enviadas aún.</div>
          ) : (
            modules.map((mod) => (
              <div key={mod.id} className="bg-zinc-900/40 border border-zinc-800/80 rounded p-3 space-y-2">
                <div className="flex justify-between items-start">
                  <span className="text-xs font-semibold text-white line-clamp-1 flex-1 pr-2">{mod.title}</span>
                  <span className={`text-[9px] px-2 py-0.5 rounded border ${getStatusColor(mod.status)}`}>
                    {mod.status.toUpperCase()}
                  </span>
                </div>
                {mod.description && <p className="text-[10px] text-zinc-500 line-clamp-2">{mod.description}</p>}
                
                <div className="flex items-center justify-between text-[10px] border-t border-zinc-800/60 pt-2 text-zinc-400">
                  <span>Rama: {mod.branchName || "N/A"}</span>
                  {mod.prUrl ? (
                    <a
                      href={mod.prUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:underline flex items-center gap-0.5"
                    >
                      Ver PR 🔗
                    </a>
                  ) : (
                    <span className="text-zinc-600">No PR</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
