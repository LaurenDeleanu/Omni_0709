// src/lib/api/documents.ts — Document Templates & Generation API
import { fetchClient } from './client';

export const DocumentsAPI = {
  getTemplates: () => fetchClient("/documents/templates"),
  previewDocument: (templateType: string, employeeId: string, variables?: any) => fetchClient("/documents/preview", { method: "POST", body: JSON.stringify({ template_type: templateType, variables: variables ?? {}, employee_id: employeeId }) }),
  generateDocument: (templateType: string, employeeId: string, variables?: any) => fetchClient("/documents/generate", { method: "POST", body: JSON.stringify({ template_type: templateType, variables: variables ?? {}, employee_id: employeeId }) }),
};
