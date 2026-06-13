// src/lib/api/calendar.ts — Calendar API
import { fetchClient } from './client';

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end?: string;
  type: string;
  status?: string;
  priority?: string;
  extra?: Record<string, any>;
  [key: string]: any;
}

export interface VacationRequest {
  id: string;
  user_id: string;
  start_date: string;
  end_date: string;
  status: string;
  reason?: string;
  [key: string]: any;
}

export interface Meeting {
  id: string;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  location?: string;
  attendees?: string[];
  [key: string]: any;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  assigned_to: string;
  due_date?: string;
  priority: string;
  status: string;
  [key: string]: any;
}

export const CalendarAPI = {
  getEvents: (monthStr: string) => fetchClient(`/calendar/events?month=${monthStr}`),
  getVacations: () => fetchClient("/calendar/vacations"),
  createVacation: (data: any) => fetchClient("/calendar/vacations", { method: "POST", body: JSON.stringify(data) }),
  createMeeting: (data: any) => fetchClient("/calendar/meetings", { method: "POST", body: JSON.stringify(data) }),
  createTask: (data: any) => fetchClient("/calendar/tasks", { method: "POST", body: JSON.stringify(data) }),
  reviewVacation: (id: string, status: string) => fetchClient(`/calendar/vacations/${id}/review`, { method: "PATCH", body: JSON.stringify({ status }) }),
  deleteMeeting: (id: string) => fetchClient(`/calendar/meetings/${id}`, { method: "DELETE" }),
  updateTask: (id: string, data: any) => fetchClient(`/calendar/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (id: string) => fetchClient(`/calendar/tasks/${id}`, { method: "DELETE" })
};
