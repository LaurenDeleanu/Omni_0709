"use client";

import React from "react";
import { ActivityBarItem } from "./ActivityBar";
import FileExplorerTree, { TreeNode } from "./FileExplorerTree";
import SearchPanel from "./SearchPanel";
import GitChangesPanel from "./GitChangesPanel";
import CodeLabSettingsPanel from "./CodeLabSettingsPanel";

interface SidebarProps {
  activePanel: ActivityBarItem;
  tree: TreeNode[];
  activeFilePath: string;
  onSelectFile: (path: string) => void;
  onNewFile: (parentPath: string) => void;
  onNewFolder: (parentPath: string) => void;
  onDeleteFile: (path: string) => void;
  onRenameFile: (path: string) => void;
  gitStatusFiles: { path: string; status: string }[];
  branch: string;
  editMode: "direct" | "proposal";
  onEditModeChange: (mode: "direct" | "proposal") => void;
  model: string;
  onModelChange: (model: string) => void;
  maxLoops: number;
  onMaxLoopsChange: (loops: number) => void;
  gitRepoUrl: string;
  onGitRepoUrlChange: (url: string) => void;
  autoBranch: boolean;
  onAutoBranchChange: (v: boolean) => void;
  requireApproval: boolean;
  onRequireApprovalChange: (v: boolean) => void;
  availableModels: { id: string; name: string; provider: string }[];
}

const panelTitles: Record<ActivityBarItem, string> = {
  explorer: "Explorer",
  search: "Search",
  "source-control": "Source Control",
  settings: "Settings",
};

export default function Sidebar({
  activePanel,
  tree,
  activeFilePath,
  onSelectFile,
  onNewFile,
  onNewFolder,
  onDeleteFile,
  onRenameFile,
  gitStatusFiles,
  branch,
  editMode,
  onEditModeChange,
  model,
  onModelChange,
  maxLoops,
  onMaxLoopsChange,
  gitRepoUrl,
  onGitRepoUrlChange,
  autoBranch,
  onAutoBranchChange,
  requireApproval,
  onRequireApprovalChange,
  availableModels,
}: SidebarProps) {
  return (
    <div className="w-[260px] bg-[#252526] border-r border-[#1e1e1e] flex flex-col shrink-0">
      <div className="h-9 flex items-center px-3 border-b border-[#333333]">
        <span className="text-xs font-semibold text-[#bbbbbb] uppercase tracking-wider">
          {panelTitles[activePanel]}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {activePanel === "explorer" && (
          <FileExplorerTree
            tree={tree}
            activeFilePath={activeFilePath}
            onSelectFile={onSelectFile}
            onNewFile={onNewFile}
            onNewFolder={onNewFolder}
            onDeleteFile={onDeleteFile}
            onRenameFile={onRenameFile}
          />
        )}

        {activePanel === "search" && (
          <SearchPanel
            onSelectFile={onSelectFile}
          />
        )}

        {activePanel === "source-control" && (
          <GitChangesPanel
            files={gitStatusFiles}
            branch={branch}
          />
        )}

        {activePanel === "settings" && (
          <CodeLabSettingsPanel
            editMode={editMode}
            onEditModeChange={onEditModeChange}
            model={model}
            onModelChange={onModelChange}
            maxLoops={maxLoops}
            onMaxLoopsChange={onMaxLoopsChange}
            gitRepoUrl={gitRepoUrl}
            onGitRepoUrlChange={onGitRepoUrlChange}
            autoBranch={autoBranch}
            onAutoBranchChange={onAutoBranchChange}
            requireApproval={requireApproval}
            onRequireApprovalChange={onRequireApprovalChange}
            availableModels={availableModels}
          />
        )}
      </div>
    </div>
  );
}
