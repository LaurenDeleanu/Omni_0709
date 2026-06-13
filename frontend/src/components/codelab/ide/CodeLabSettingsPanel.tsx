"use client";

import React from "react";

interface CodeLabSettingsPanelProps {
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

export default function CodeLabSettingsPanel({
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
}: CodeLabSettingsPanelProps) {
  return (
    <div className="p-3 space-y-4">
      <div>
        <label className="block text-[11px] font-semibold text-[#858585] uppercase mb-1.5">
          Edit Mode
        </label>
        <div className="flex rounded bg-[#3c3c3c] border border-[#454545] overflow-hidden">
          <button
            onClick={() => onEditModeChange("direct")}
            className={`flex-1 py-1.5 text-[12px] font-semibold transition-colors ${
              editMode === "direct"
                ? "bg-[#0e639c] text-white"
                : "text-[#858585] hover:text-[#cccccc]"
            }`}
          >
            Direct
          </button>
          <button
            onClick={() => onEditModeChange("proposal")}
            className={`flex-1 py-1.5 text-[12px] font-semibold transition-colors ${
              editMode === "proposal"
                ? "bg-[#0e639c] text-white"
                : "text-[#858585] hover:text-[#cccccc]"
            }`}
          >
            Proposal (Branch)
          </button>
        </div>
      </div>

      {editMode === "proposal" && (
        <div className="space-y-3 p-3 bg-[#1e1e1e] border border-[#333333] rounded">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoBranch}
              onChange={(e) => onAutoBranchChange(e.target.checked)}
              className="rounded bg-[#3c3c3c] border-[#454545] text-[#007acc] focus:ring-0"
            />
            <span className="text-[13px] text-[#cccccc]">Auto-create branch on agent run</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={requireApproval}
              onChange={(e) => onRequireApprovalChange(e.target.checked)}
              className="rounded bg-[#3c3c3c] border-[#454545] text-[#007acc] focus:ring-0"
            />
            <span className="text-[13px] text-[#cccccc]">Require approval for each change</span>
          </label>
        </div>
      )}

      <div>
        <label className="block text-[11px] font-semibold text-[#858585] uppercase mb-1.5">
          AI Model
        </label>
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="w-full bg-[#3c3c3c] border border-[#454545] rounded px-2 py-1.5 text-[13px] text-[#cccccc] outline-none focus:border-[#007acc]"
        >
          {availableModels.length > 0 ? (
            ["openai", "gemini", "anthropic", "xai", "openrouter"].map((provider) => {
              const group = availableModels.filter((m) => m.provider === provider);
              if (group.length === 0) return null;
              const labels: Record<string, string> = {
                openai: "OpenAI",
                gemini: "Google Gemini",
                anthropic: "Anthropic Claude",
                xai: "xAI Grok",
                openrouter: "OpenRouter",
              };
              return (
                <optgroup key={provider} label={labels[provider] || provider}>
                  {group.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              );
            })
          ) : (
            <>
              <option value="openai/gpt-4o">OpenAI GPT-4o</option>
              <option value="openai/gpt-4o-mini">OpenAI GPT-4o Mini</option>
              <option value="gemini/gemini-2.0-flash">Gemini 2.0 Flash</option>
            </>
          )}
        </select>
      </div>

      <div>
        <label className="block text-[11px] font-semibold text-[#858585] uppercase mb-1.5">
          Max Loops
        </label>
        <input
          type="number"
          value={maxLoops}
          onChange={(e) => onMaxLoopsChange(parseInt(e.target.value, 10))}
          min={1}
          max={50}
          className="w-full bg-[#3c3c3c] border border-[#454545] rounded px-2 py-1.5 text-[13px] text-[#cccccc] outline-none focus:border-[#007acc]"
        />
      </div>

      <div>
        <label className="block text-[11px] font-semibold text-[#858585] uppercase mb-1.5">
          Git Repo URL
        </label>
        <input
          type="text"
          value={gitRepoUrl}
          onChange={(e) => onGitRepoUrlChange(e.target.value)}
          placeholder="https://github.com/user/repo"
          className="w-full bg-[#3c3c3c] border border-[#454545] rounded px-2 py-1.5 text-[13px] text-[#cccccc] placeholder-[#858585] outline-none focus:border-[#007acc]"
        />
      </div>
    </div>
  );
}
