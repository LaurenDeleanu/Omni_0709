// src/lib/api/documents.ts — Document Templates & Generation API
import { fetchClient } from './client';

export const DocumentsAPI = {
  getTemplates: () => fetchClient("/documents/templates"),
  previewDocument: (templateId: string, employeeId: string, customData?: any) => fetchClient("/documents/preview", { method: "POST", body: JSON.stringify({ template_id: templateId, employee_id: employeeId, custom_data: customData }) }),
  generateDocument: (templateId: string, employeeId: string, customData?: any) => fetchClient("/documents/generate", { method: "POST", body: JSON.stringify({ template_id: templateId, employee_id: employeeId, custom_data: customData }) }),
};
