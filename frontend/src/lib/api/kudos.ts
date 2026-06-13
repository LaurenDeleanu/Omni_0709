import { fetchClient } from './client';

export interface UserMini {
  id: string;
  full_name: string | null;
  email: string;
}

export interface Kudos {
  id: string;
  sender_id: string;
  sender?: UserMini;
  receiver_id: string;
  receiver?: UserMini;
  message: string;
  badge: string;
  created_at: string;
}

export const KudosAPI = {
  getFeed: (): Promise<Kudos[]> => fetchClient('/kudos'),
  sendKudos: (data: { receiver_id: string; message: string; badge: string }): Promise<Kudos> => 
    fetchClient('/kudos', { method: 'POST', body: JSON.stringify(data) })
};
