import { fetchClient } from './client';

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: 'vacation' | 'payroll' | 'task' | 'kudos' | 'system';
  is_read: boolean;
  link?: string;
  created_at: string;
}

export const NotificationAPI = {
  getMyNotifications: async (): Promise<Notification[]> => {
    const res = await fetchClient('/notifications');
    return res.items ?? res;
  },
  readAll: (): Promise<{ message: string }> => fetchClient('/notifications/read-all', { method: 'POST' }),
  readNotification: (id: string): Promise<Notification> => fetchClient(`/notifications/${id}/read`, { method: 'POST' })
};
