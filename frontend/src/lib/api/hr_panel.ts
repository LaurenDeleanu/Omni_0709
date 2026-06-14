import { fetchClient } from './client';

export interface HROverview {
  total_employees: number;
  active_employees: number;
  new_hires_month: number;
  open_jobs: number;
  pipeline_candidates: number;
  pending_time_off: number;
  open_it_tickets: number;
  upcoming_reviews: number;
  recent_activity: {
    id: string;
    full_name: string;
    email: string;
    department: string;
    role: string;
    hire_date: string | null;
    is_active: boolean;
    created_at: string | null;
  }[];
  history_events: {
    id: string;
    employee_id: string;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
    changed_by: string | null;
    change_reason: string | null;
    created_at: string | null;
  }[];
}

export interface HRTicket {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  requester_id: string;
  requester_name: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  created_at: string | null;
  updated_at: string | null;
  resolved_at: string | null;
}

export interface HREmployeeRequest {
  id: string;
  type: string;
  subtype?: string;
  employee_id: string;
  employee_name: string | null;
  start_date: string | null;
  end_date: string | null;
  reason: string | null;
  status: string;
  created_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface RecruitingOverview {
  jobs_by_stage: Record<string, number>;
  candidates_by_stage: Record<string, number>;
  sources: { source: string; count: number }[];
  avg_time_to_hire_days: number;
  hires_this_month: number;
  open_positions: {
    id: string;
    title: string;
    department: string;
    location: string;
    employment_type: string;
    candidate_count: number;
    created_at: string | null;
  }[];
}

export interface ComplianceOverview {
  missing_contracts: number;
  missing_department: number;
  total_employees: number;
  training_completion_rate: number;
  enrolled_users: number;
  total_enrollments: number;
  completed_enrollments: number;
  users_without_training: number;
  upcoming_audits: {
    id: string;
    title: string;
    audit_type: string;
    status: string;
    frequency: string;
    scheduled_at: string | null;
  }[];
}

export const HRPanelAPI = {
  getOverview: (): Promise<HROverview> => fetchClient("/hr-panel/overview"),

  getTickets: (params?: { status?: string; priority?: string; assignee_id?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.priority) qs.set("priority", params.priority);
    if (params?.assignee_id) qs.set("assignee_id", params.assignee_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return fetchClient(`/hr-panel/tickets${query ? `?${query}` : ""}`);
  },

  getRequests: (params?: { request_type?: string; status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.request_type) qs.set("request_type", params.request_type);
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return fetchClient(`/hr-panel/requests${query ? `?${query}` : ""}`);
  },

  getRecruiting: (): Promise<RecruitingOverview> => fetchClient("/hr-panel/recruiting"),

  getCompliance: (): Promise<ComplianceOverview> => fetchClient("/hr-panel/compliance"),

  approveRequest: (requestId: string, reviewerNote?: string) =>
    fetchClient(`/hr-panel/requests/${requestId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reviewer_note: reviewerNote || "" }),
    }),

  rejectRequest: (requestId: string, reviewerNote?: string) =>
    fetchClient(`/hr-panel/requests/${requestId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reviewer_note: reviewerNote || "" }),
    }),
};
