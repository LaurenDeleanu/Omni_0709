export interface FileItem {
  path: string;
  content: string;
  language: string;
}

export interface GitProposalInput {
  repoUrl: string;
  accessToken: string;
  defaultBranch: string;
  devBranch: string;
  branchName: string;
  title: string;
  description: string;
  files: FileItem[];
}

export interface GitProposalResult {
  success: boolean;
  branchName: string;
  prUrl?: string;
  error?: string;
}
