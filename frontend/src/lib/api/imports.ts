// src/lib/api/imports.ts — Bulk import API
import { fetchClient, downloadBlob } from './client';

export interface ImportStatus {
  state?: string;
  progress_percent?: number;
  inserted?: number;
  duplicates?: number;
  info?: string;
}

export interface EntityDefinition {
  type: string;
  label: string;
  description: string;
  required_columns: string[];
  optional_columns: string[];
  template_url: string;
}

export interface EntityList {
  entities: EntityDefinition[];
}

export const ImportAPI = {
  getStatus: (id: string) => fetchClient(`/imports/status/${id}`),

  getEntities: (): Promise<EntityList> => fetchClient("/imports/entities"),

  uploadFile: async (entityType: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchClient(`/imports/upload/${entityType}`, { method: "POST", body: formData });
  },

  downloadTemplate: (entityType?: string) =>
    downloadBlob(
      entityType ? `/imports/template/${entityType}` : "/imports/template",
      "template.csv"
    ),

  previewCSV: (csvContent: string, entityType: string) =>
    fetchClient("/imports/csv/preview", {
      method: "POST",
      body: JSON.stringify({ csv_content: csvContent, entity_type: entityType }),
    }),

  importCSV: (csvContent: string, entityType: string, dryRun: boolean = false) =>
    fetchClient("/imports/csv/import", {
      method: "POST",
      body: JSON.stringify({ csv_content: csvContent, entity_type: entityType, dry_run: dryRun }),
    }),
};

export const getEntities = ImportAPI.getEntities;
export const getStatus = ImportAPI.getStatus;
export const uploadFile = ImportAPI.uploadFile;
export const downloadTemplate = ImportAPI.downloadTemplate;
