"use client";

import React, { useState } from "react";
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Plus, FilePlus, FolderPlus, MoreHorizontal } from "lucide-react";

export interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  language?: string;
  gitStatus?: "M" | "A" | "D" | "??" | null;
  children?: TreeNode[];
}

interface FileExplorerTreeProps {
  tree: TreeNode[];
  activeFilePath: string;
  onSelectFile: (path: string) => void;
  onNewFile: (parentPath: string) => void;
  onNewFolder: (parentPath: string) => void;
  onDeleteFile: (path: string) => void;
  onRenameFile: (path: string) => void;
}

function getIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  switch (ext) {
    case "ts": case "tsx": return "ts";
    case "js": case "jsx": return "js";
    case "json": return "json";
    case "css": return "css";
    case "html": return "html";
    case "md": return "md";
    case "py": return "py";
    case "go": return "go";
    case "rs": return "rs";
    case "yaml": case "yml": return "yaml";
    case "dockerfile": return "docker";
    case "sh": case "bash": return "shell";
    default: return "file";
  }
}

function getGitStatusColor(status: string | null | undefined) {
  if (!status) return "";
  switch (status) {
    case "M": return "text-green-400";
    case "A": return "text-amber-400";
    case "D": return "text-red-400";
    case "??": return "text-amber-300";
    default: return "";
  }
}

function getGitStatusLetter(status: string | null | undefined) {
  if (!status) return "";
  return status;
}

function TreeNodeComp({
  node,
  depth,
  activeFilePath,
  onSelectFile,
  onNewFile,
  onNewFolder,
  onDeleteFile,
  onRenameFile,
}: {
  node: TreeNode;
  depth: number;
  activeFilePath: string;
  onSelectFile: (path: string) => void;
  onNewFile: (parentPath: string) => void;
  onNewFolder: (parentPath: string) => void;
  onDeleteFile: (path: string) => void;
  onRenameFile: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const handleClick = () => {
    if (node.isDir) {
      setExpanded(!expanded);
    } else {
      onSelectFile(node.path);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const closeContextMenu = () => setContextMenu(null);

  const isActive = node.path === activeFilePath;
  const gitStatusLetter = getGitStatusLetter(node.gitStatus);
  const statusColor = getGitStatusColor(node.gitStatus);

  return (
    <div>
      <div
        className={`group flex items-center h-[22px] cursor-pointer text-[13px] ${
          isActive ? "bg-[#37373d]" : "hover:bg-[#2a2d2e]"
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px`, paddingRight: "4px" }}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      >
        {depth > 0 && (
          <div className="absolute" style={{ left: `${depth * 16 + 4}px` }}>
            {/* indent guides would render here */}
          </div>
        )}
        {node.isDir ? (
          expanded ? (
            <ChevronDown size={16} className="shrink-0 text-[#858585]" />
          ) : (
            <ChevronRight size={16} className="shrink-0 text-[#858585]" />
          )
        ) : (
          <span className="w-4 shrink-0" />
        )}
        {node.isDir ? (
          expanded ? (
            <FolderOpen size={16} className="shrink-0 text-[#dcb67a] ml-0.5" />
          ) : (
            <Folder size={16} className="shrink-0 text-[#dcb67a] ml-0.5" />
          )
        ) : (
          <File size={16} className="shrink-0 text-[#858585] ml-0.5" />
        )}
        <span className={`ml-1 truncate select-none ${isActive ? "text-white" : "text-[#cccccc]"}`}>
          {node.name}
        </span>
        {gitStatusLetter && (
          <span className={`ml-1 text-[11px] font-bold ${statusColor}`}>
            {gitStatusLetter}
          </span>
        )}
        <div className="ml-auto opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
          {node.isDir && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onNewFile(node.path); }}
                title="New File"
                className="p-0.5 hover:bg-[#454545] rounded"
              >
                <FilePlus size={14} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onNewFolder(node.path); }}
                title="New Folder"
                className="p-0.5 hover:bg-[#454545] rounded"
              >
                <FolderPlus size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {contextMenu && (
        <div
          className="fixed z-50 bg-[#252526] border border-[#454545] rounded shadow-lg py-1 min-w-[160px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={closeContextMenu}
        >
          <button
            className="w-full text-left px-3 py-1 text-[13px] text-[#cccccc] hover:bg-[#094771]"
            onClick={() => { onSelectFile(node.path); closeContextMenu(); }}
          >
            Open
          </button>
          {!node.isDir && (
            <>
              <button
                className="w-full text-left px-3 py-1 text-[13px] text-[#cccccc] hover:bg-[#094771]"
                onClick={() => { onRenameFile(node.path); closeContextMenu(); }}
              >
                Rename
              </button>
              <button
                className="w-full text-left px-3 py-1 text-[13px] text-[#cccccc] hover:bg-[#094771]"
                onClick={() => { onDeleteFile(node.path); closeContextMenu(); }}
              >
                Delete
              </button>
            </>
          )}
          <div className="border-t border-[#454545] my-1" />
          <button
            className="w-full text-left px-3 py-1 text-[13px] text-[#cccccc] hover:bg-[#094771]"
            onClick={() => { navigator.clipboard.writeText(node.path); closeContextMenu(); }}
          >
            Copy Path
          </button>
        </div>
      )}

      {node.isDir && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNodeComp
              key={child.path}
              node={child}
              depth={depth + 1}
              activeFilePath={activeFilePath}
              onSelectFile={onSelectFile}
              onNewFile={onNewFile}
              onNewFolder={onNewFolder}
              onDeleteFile={onDeleteFile}
              onRenameFile={onRenameFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileExplorerTree({
  tree,
  activeFilePath,
  onSelectFile,
  onNewFile,
  onNewFolder,
  onDeleteFile,
  onRenameFile,
}: FileExplorerTreeProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="h-9 flex items-center px-3 border-b border-[#252526] bg-[#252526]">
        <span className="text-xs font-semibold text-[#bbbbbb] uppercase tracking-wider">
          Explorer
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => onNewFile(tree.length > 0 ? tree[0].path : ".")}
            title="New File"
            className="p-1 hover:bg-[#454545] rounded text-[#858585] hover:text-[#cccccc]"
          >
            <FilePlus size={16} />
          </button>
          <button
            onClick={() => onNewFolder(tree.length > 0 ? tree[0].path : ".")}
            title="New Folder"
            className="p-1 hover:bg-[#454545] rounded text-[#858585] hover:text-[#cccccc]"
          >
            <FolderPlus size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto py-1 min-h-0">
        {tree.length === 0 ? (
          <div className="text-[13px] text-[#858585] text-center py-6">No files found</div>
        ) : (
          tree.map((node) => (
            <TreeNodeComp
              key={node.path}
              node={node}
              depth={0}
              activeFilePath={activeFilePath}
              onSelectFile={onSelectFile}
              onNewFile={onNewFile}
              onNewFolder={onNewFolder}
              onDeleteFile={onDeleteFile}
              onRenameFile={onRenameFile}
            />
          ))
        )}
      </div>
    </div>
  );
}
