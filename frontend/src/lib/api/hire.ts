// src/lib/api/hire.ts — Recruitment ATS API
import { fetchClient } from './client';

export interface JobPosting {
  id: string;
  title: string;
  department?: string;
  location?: string;
  employment_type?: string;
  description?: string;
  status: string;
  created_at: string;
  candidate_count?: number;
}

export interface Candidate {
  id: string;
  job_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  resume_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  stage: string;
  source?: string;
  notes?: string;
  tags?: string;
  engagement_score?: number;
  last_contacted_at?: string;
  source_detail?: string;
  created_at: string;
}

export interface CandidatePool {
  id: string;
  name: string;
  description?: string;
  created_by_id: string;
  created_at: string;
  candidate_count: number;
}

export interface PoolCandidate {
  entry_id: string;
  pool_id: string;
  candidate_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  stage: string;
  source?: string;
  tags?: string;
  engagement_score: number;
  last_contacted_at?: string;
  source_detail?: string;
  notes?: string;
  added_at: string;
}

export interface CrmCandidate extends Candidate {
  pools: { id: string; name: string }[];
}

export interface PromoteOptions {
  role?: string;
  password: string;
  phone_number?: string;
  address?: string;
  contract_type?: string;
  hire_date?: string;
  base_salary?: number;
  social_security_number?: string;
  iban?: string;
  country?: string;
  assign_onboarding_plan?: boolean;
  enroll_in_training?: boolean;
  request_it_equipment?: boolean;
  it_equipment_type?: string;
  it_equipment_quantity?: number;
}

export const HireAPI = {
  getJobs: () => fetchClient("/hire/jobs"),
  createJob: (data: Partial<JobPosting>) => fetchClient("/hire/jobs", { method: "POST", body: JSON.stringify(data) }),
  getJob: (jobId: string) => fetchClient(`/hire/jobs/${jobId}`),
  updateJob: (jobId: string, data: Partial<JobPosting>) => fetchClient(`/hire/jobs/${jobId}`, { method: "PUT", body: JSON.stringify(data) }),
  getCandidates: (jobId?: string) => {
    const query = jobId ? `?job_id=${jobId}` : "";
    return fetchClient(`/hire/candidates${query}`);
  },
  addCandidate: (data: Partial<Candidate>) => fetchClient("/hire/candidates", { method: "POST", body: JSON.stringify(data) }),
  updateCandidate: (candidateId: string, data: Partial<Candidate>) => fetchClient(`/hire/candidates/${candidateId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateCandidateStage: (candidateId: string, stage: string) => fetchClient(`/hire/candidates/${candidateId}/stage`, { method: "PATCH", body: JSON.stringify({ stage }) }),
  getInterviews: (candidateId: string) => fetchClient(`/hire/candidates/${candidateId}/interviews`),
  createInterview: (candidateId: string, data: any) => fetchClient(`/hire/candidates/${candidateId}/interviews`, { method: "POST", body: JSON.stringify(data) }),
  deleteInterview: (candidateId: string, interviewId: string) => fetchClient(`/hire/candidates/${candidateId}/interviews/${interviewId}`, { method: "DELETE" }),
  promoteCandidate: (candidateId: string, data: any) => fetchClient(`/hire/candidates/${candidateId}/promote`, { method: "POST", body: JSON.stringify(data) }),

  getPools: () => fetchClient("/hire/pools"),
  createPool: (data: { name: string; description?: string }) => fetchClient("/hire/pools", { method: "POST", body: JSON.stringify(data) }),
  updatePool: (poolId: string, data: { name?: string; description?: string }) => fetchClient(`/hire/pools/${poolId}`, { method: "PUT", body: JSON.stringify(data) }),
  deletePool: (poolId: string) => fetchClient(`/hire/pools/${poolId}`, { method: "DELETE" }),
  getPoolCandidates: (poolId: string) => fetchClient(`/hire/pools/${poolId}/candidates`),
  addToPool: (poolId: string, candidateId: string) => fetchClient(`/hire/pools/${poolId}/candidates`, { method: "POST", body: JSON.stringify({ candidate_id: candidateId }) }),
  removeFromPool: (poolId: string, candidateId: string) => fetchClient(`/hire/pools/${poolId}/candidates/${candidateId}`, { method: "DELETE" }),
  addByStage: (poolId: string, stage: string) => fetchClient(`/hire/pools/${poolId}/add-by-stage`, { method: "POST", body: JSON.stringify({ stage }) }),

  getCrmCandidates: () => fetchClient("/hire/candidates/crm"),
  updateCrmData: (candidateId: string, data: { tags?: string; engagement_score?: number; last_contacted_at?: string; source_detail?: string }) => fetchClient(`/hire/candidates/${candidateId}/crm`, { method: "PUT", body: JSON.stringify(data) }),
  generateOutreach: (candidateId: string) => fetchClient(`/hire/candidates/${candidateId}/generate-outreach`, { method: "POST" }),
  logContact: (candidateId: string) => fetchClient(`/hire/candidates/${candidateId}/log-contact`, { method: "POST" }),
};
