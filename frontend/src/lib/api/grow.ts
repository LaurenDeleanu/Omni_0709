// src/lib/api/grow.ts — Performance & culture API (OKRs, reviews)
import { fetchClient } from './client';

export interface KeyResult {
  id: string;
  objective_id: string;
  title: string;
  target_value: number;
  current_value: number;
  unit: string;
}

export interface Objective {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  status: string;
  created_at: string;
  key_results: KeyResult[];
}

export interface PerformanceReview {
  id: string;
  employee_id: string;
  manager_id: string;
  cycle_name: string;
  status: string;
  self_evaluation?: any;
  manager_evaluation?: any;
  created_at: string;
}

export const GrowAPI = {
  getObjectives: (ownerId?: string) => fetchClient(`/grow/okrs${ownerId ? `?owner_id=${ownerId}` : ""}`),
  createObjective: (data: any) => fetchClient("/grow/okrs", { method: "POST", body: JSON.stringify(data) }),
  updateObjective: (id: string, data: any) => fetchClient(`/grow/okrs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteObjective: (id: string) => fetchClient(`/grow/okrs/${id}`, { method: "DELETE" }),
  addKeyResult: (objectiveId: string, data: any) => fetchClient(`/grow/okrs/${objectiveId}/key-results`, { method: "POST", body: JSON.stringify(data) }),
  updateKeyResult: (id: string, data: any) => fetchClient(`/grow/key-results/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteKeyResult: (id: string) => fetchClient(`/grow/key-results/${id}`, { method: "DELETE" }),

  getReviews: (employeeId?: string, managerId?: string) => {
    let query = "";
    const params = [];
    if (employeeId) params.push(`employee_id=${employeeId}`);
    if (managerId) params.push(`manager_id=${managerId}`);
    if (params.length) query = `?${params.join("&")}`;
    return fetchClient(`/grow/reviews${query}`);
  },
  createReview: (data: any) => fetchClient("/grow/reviews", { method: "POST", body: JSON.stringify(data) }),
  updateReview: (id: string, data: any) => fetchClient(`/grow/reviews/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteReview: (id: string) => fetchClient(`/grow/reviews/${id}`, { method: "DELETE" })
};
