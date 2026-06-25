// src/lib/api/checklists.ts — Onboarding Checklists API
import { fetchClient } from './client';

export interface ChecklistTemplate {
  id: string;
  name: string;
  description?: string;
  tasks?: Array<{ title: string; description?: string; role_assignee?: string }>;
  [key: string]: any;
}

export const ChecklistsAPI = {
  getTemplates: () => fetchClient("/checklists/checklist-templates"),
  createTemplate: (data: any) => fetchClient("/checklists/checklist-templates", { method: "POST", body: JSON.stringify(data) }),
  getTemplate: (templateId: string) => fetchClient(`/checklists/checklist-templates/${templateId}`),
  deleteTemplate: (templateId: string) => fetchClient(`/checklists/checklist-templates/${templateId}`, { method: "DELETE" }),
  
  assignChecklist: (employeeId: string, templateId: string) => fetchClient("/checklists/assign-checklist", { method: "POST", body: JSON.stringify({ employee_id: employeeId, template_id: templateId }) }),
  getMyChecklists: () => fetchClient("/checklists/my-checklists"),
  updateTaskStatus: (taskId: string, isCompleted: boolean) => fetchClient(`/checklists/checklist-tasks/${taskId}`, { method: "PATCH", body: JSON.stringify({ is_completed: isCompleted }) }),
  getEmployeeHubData: () => fetchClient("/checklists/employee-hub"),
};
