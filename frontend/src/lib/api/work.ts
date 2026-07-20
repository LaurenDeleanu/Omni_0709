// src/lib/api/work.ts — Project management API
import { fetchClient } from './client';

export interface Project {
  id: string;
  name: string;
  description?: string;
  client_id?: string;
  status: string;
  due_date?: string;
  budget: number;
  created_at: string;
}

export interface BoardColumn {
  id: string;
  board_id: string;
  name: string;
  order_index: number;
}

export interface KanbanBoard {
  id: string;
  project_id: string;
  name: string;
  columns: BoardColumn[];
}

export interface WikiPage {
  id: string;
  title: string;
  content?: string;
  author_id?: string;
  project_id?: string;
  created_at: string;
}

export const WorkAPI = {
  getProjects: () => fetchClient("/work/projects"),
  createProject: (data: Partial<Project>) => fetchClient("/work/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (projectId: string, data: Partial<Project>) => fetchClient(`/work/projects/${projectId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (projectId: string) => fetchClient(`/work/projects/${projectId}`, { method: "DELETE" }),
  getTasks: (projectId: string) => fetchClient(`/work/projects/${projectId}/tasks`),
  createTask: (data: any) => fetchClient("/work/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (taskId: string, data: any) => fetchClient(`/work/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (taskId: string) => fetchClient(`/work/tasks/${taskId}`, { method: "DELETE" }),
  updateTaskStatus: (taskId: string, status: string) => fetchClient(`/work/tasks/${taskId}/move`, { method: "PUT", body: JSON.stringify({ status }) }),
  moveTask: (taskId: string, data: { column_id?: string, order_index?: number, status?: string }) => fetchClient(`/work/tasks/${taskId}/move`, { method: "PUT", body: JSON.stringify(data) }),
  getBoards: (projectId: string) => fetchClient(`/work/projects/${projectId}/boards`),
  createBoard: (data: { project_id: string, name: string }) => fetchClient("/work/boards", { method: "POST", body: JSON.stringify(data) }),
  createBoardColumn: (boardId: string, data: { name: string, order_index?: number }) => fetchClient(`/work/boards/${boardId}/columns`, { method: "POST", body: JSON.stringify(data) }),
  getWikiPages: (projectId?: string) => fetchClient(`/work/wiki${projectId ? `?project_id=${projectId}` : ""}`),
  createWikiPage: (data: Partial<WikiPage>) => fetchClient("/work/wiki", { method: "POST", body: JSON.stringify(data) }),
  updateWikiPage: (pageId: string, data: Partial<WikiPage>) => fetchClient(`/work/wiki/${pageId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteWikiPage: (pageId: string) => fetchClient(`/work/wiki/${pageId}`, { method: "DELETE" }),
};
