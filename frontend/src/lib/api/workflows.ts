import { fetchClient } from './client';

export interface WorkflowStep {
  id: string;
  title: string;
  role: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  type: 'onboarding' | 'offboarding';
  steps: WorkflowStep[];
}

export interface StepStatus {
  completed: boolean;
  completed_at: string | null;
  completed_by: string | null;
}

export interface UserWorkflow {
  id: string;
  user_id: string;
  template_id: string;
  status: 'in_progress' | 'completed';
  steps_status: Record<string, StepStatus>;
  created_at: string;
  template?: WorkflowTemplate;
}

export const WorkflowAPI = {
  getTemplates: (): Promise<WorkflowTemplate[]> => fetchClient('/workflows/templates'),
  createTemplate: (data: { name: string; type: string; steps: WorkflowStep[] }): Promise<WorkflowTemplate> => 
    fetchClient('/workflows/templates', { method: 'POST', body: JSON.stringify(data) }),
  getUserWorkflows: (userId: string): Promise<UserWorkflow[]> => fetchClient(`/workflows/user/${userId}`),
  assignWorkflow: (userId: string, templateId: string): Promise<UserWorkflow> => 
    fetchClient(`/workflows/user/${userId}/assign`, { method: 'POST', body: JSON.stringify({ template_id: templateId }) }),
  toggleStep: (userId: string, stepId: string): Promise<UserWorkflow> => 
    fetchClient(`/workflows/user/${userId}/steps/${stepId}/toggle`, { method: 'POST' })
};
