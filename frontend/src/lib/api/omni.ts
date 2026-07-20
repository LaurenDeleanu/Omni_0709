import { fetchClient } from "./client";

export interface OmniFileItem {
  path: string;
  isDir: boolean;
  language: string;
}

export interface OmniGitStatusFile {
  path: string;
  status: "M" | "A" | "D" | "R" | "??" | "staged" | "unstaged";
  additions?: number;
  deletions?: number;
}

export interface OmniGitStatus {
  branch: string;
  files: OmniGitStatusFile[];
}

export interface OmniBranch {
  name: string;
  current: boolean;
  remote: boolean;
}

export interface OmniAgentSettings {
  editingMode: "direct" | "branch_proposal" | "review_only";
  targetBranch: string;
  showDiffPreview: boolean;
  autoCommit: boolean;
}

export interface OmniRunResult {
  id: string;
  success: boolean;
  response: string;
  trace: OmniTraceStep[];
}

export interface OmniTraceStep {
  step: number;
  thought: string;
  tool: string;
  arguments: Record<string, unknown>;
  timestamp: string;
  latencyMs: number;
}

export interface OmniProposal {
  id: string;
  title: string;
  description: string;
  branchName: string;
  status: string;
  fileCount: number;
  createdAt?: string;
}

export interface OmniCreateBranchResult {
  branchName: string;
  success: boolean;
}

export interface OmniProposalDiff {
  file: string;
  original: string;
  modified: string;
  language: string;
}

export interface OmniEditMode {
  mode: "direct" | "branch_proposal" | "review_only";
}

export const OmniAPI = {
  async getFiles(path: string = "."): Promise<{ files: OmniFileItem[] }> {
    return fetchClient(`/omni/files?action=list&path=${encodeURIComponent(path)}`);
  },

  async readFile(path: string): Promise<{ content: string }> {
    return fetchClient(`/omni/files?action=read&path=${encodeURIComponent(path)}`);
  },

  async writeFile(path: string, content: string): Promise<{ success: boolean }> {
    return fetchClient("/omni/files", {
      method: "POST",
      body: JSON.stringify({ path, content }),
    });
  },

  async deleteFile(path: string): Promise<{ success: boolean }> {
    return fetchClient(`/omni/files?path=${encodeURIComponent(path)}`, {
      method: "DELETE",
    });
  },

  async getGitStatus(): Promise<OmniGitStatus> {
    return fetchClient("/omni/git-status");
  },

  async updateSettings(agentId: string, settings: OmniAgentSettings): Promise<{ success: boolean }> {
    return fetchClient(`/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify({ agent_settings: settings }),
    });
  },

  async runOmniMaster(message: string): Promise<OmniRunResult> {
    return fetchClient("/omni/master", {
      method: "POST",
      body: JSON.stringify({ prompt: message }),
    });
  },

  async getModels(): Promise<{ models: { id: string; name: string; provider: string }[] }> {
    return fetchClient("/omni/models");
  },

  async getMasterAgent(): Promise<{
    runs: unknown[];
    agent: { name: string; aiModel: string; aiSystemPrompt: string; agentConfig: { maxLoops: number } };
  }> {
    return fetchClient(`/omni/master`);
  },

  async getEditMode(): Promise<OmniEditMode> {
    return fetchClient("/omni/edit-mode");
  },

  async setEditMode(mode: string): Promise<{ success: boolean }> {
    return fetchClient("/omni/edit-mode", {
      method: "PATCH",
      body: JSON.stringify({ mode }),
    });
  },

  async createBranch(name: string): Promise<OmniCreateBranchResult> {
    return fetchClient("/omni/branches", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  async getProposals(branchId: string): Promise<{ proposals: OmniProposal[] }> {
    return fetchClient(`/omni/branches/${branchId}/proposals`);
  },

  async getProposalDiff(proposalId: string): Promise<{ diffs: OmniProposalDiff[] }> {
    return fetchClient(`/omni/proposals/${proposalId}/diff`);
  },

  async applyProposal(proposalId: string): Promise<{ success: boolean; message: string }> {
    return fetchClient(`/omni/proposals/${proposalId}/apply`, {
      method: "POST",
    });
  },

  async rejectProposal(proposalId: string): Promise<{ success: boolean }> {
    return fetchClient(`/omni/proposals/${proposalId}/reject`, {
      method: "POST",
    });
  },

  async applyAllProposals(branchId: string): Promise<{ applied: number; total: number; errors: string[]; branch_status: string }> {
    return fetchClient(`/omni/branches/${branchId}/apply-all`, {
      method: "POST",
    });
  },

  async createPR(branchId: string, title: string, body: string = ""): Promise<{ commit_hash: string; branch: string; files_committed: number }> {
    return fetchClient(`/omni/branches/${branchId}/pr`, {
      method: "POST",
      body: JSON.stringify({ title, body }),
    });
  },
};

export default OmniAPI;
