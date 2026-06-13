import React, { useState } from "react";
import { FileItem } from "@/lib/git/types";

interface FileTreeProps {
  files: FileItem[];
  activeFilePath: string;
  onSelectFile: (path: string) => void;
  onAddFile: (path: string) => void;
  onDeleteFile: (path: string) => void;
}

export default function FileTree({
  files,
  activeFilePath,
  onSelectFile,
  onAddFile,
  onDeleteFile,
}: FileTreeProps) {
  const [search, setSearch] = useState("");
  const [newFileName, setNewFileName] = useState("");
  const [showAddInput, setShowAddInput] = useState(false);

  const filteredFiles = files.filter((f) =>
    f.path.toLowerCase().includes(search.toLowerCase())
  );

  const getIcon = (language: string) => {
    switch (language) {
      case "javascript":
        return "🟨 JS";
      case "typescript":
        return "🟦 TS";
      case "json":
        return "⚙️ JSON";
      case "markdown":
        return "📝 MD";
      case "css":
        return "🎨 CSS";
      case "html":
        return "🌐 HTML";
      default:
        return "📄 TXT";
    }
  };

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) return;
    onAddFile(newFileName.trim());
    setNewFileName("");
    setShowAddInput(false);
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-lg p-4 text-zinc-300">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">Archivos</h3>
        <button
          onClick={() => setShowAddInput(!showAddInput)}
          className="text-xs px-2 py-1 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 rounded border border-indigo-500/20"
        >
          {showAddInput ? "Cancelar" : "+ Nuevo"}
        </button>
      </div>

      {showAddInput && (
        <form onSubmit={handleAddSubmit} className="mb-3">
          <input
            type="text"
            placeholder="ej: index.js, schema.json"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
            autoFocus
          />
        </form>
      )}

      <input
        type="text"
        placeholder="Buscar archivo..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-400 placeholder-zinc-600 mb-3 focus:outline-none focus:border-zinc-700"
      />

      <div className="flex-1 overflow-y-auto min-h-0 space-y-1">
        {filteredFiles.length === 0 ? (
          <div className="text-xs text-zinc-600 text-center py-4">No hay archivos</div>
        ) : (
          filteredFiles.map((file) => {
            const isActive = file.path === activeFilePath;
            return (
              <div
                key={file.path}
                className={`flex items-center justify-between group rounded px-2.5 py-2 text-xs transition-colors cursor-pointer ${
                  isActive
                    ? "bg-zinc-800/80 text-white border-l-2 border-indigo-500"
                    : "hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200"
                }`}
                onClick={() => onSelectFile(file.path)}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="font-semibold text-[10px] uppercase text-zinc-500 shrink-0 select-none">
                    {getIcon(file.language)}
                  </span>
                  <span className="truncate">{file.path}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`¿Eliminar ${file.path}?`)) {
                      onDeleteFile(file.path);
                    }
                  }}
                  className="text-zinc-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity text-xs"
                  title="Eliminar archivo"
                >
                  ✕
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
