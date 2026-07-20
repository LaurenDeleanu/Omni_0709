// src/lib/api/metadata.ts — Page metadata API
import { fetchClient } from './client';

export interface PageMetadata {
  schema_data?: any;
  [key: string]: any;
}

export const MetadataAPI = {
  getPage: (moduleName: string, pageName: string) => fetchClient(`/metadata/${moduleName}/${pageName}`),
  create: (data: any) => fetchClient("/metadata/", { method: "POST", body: JSON.stringify(data) }),
  update: (moduleName: string, pageName: string, data: any) => fetchClient(`/metadata/${moduleName}/${pageName}`, { method: "PUT", body: JSON.stringify(data) })
};
