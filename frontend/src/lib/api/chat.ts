import { fetchClient } from './client';

export interface ChatRoom {
  id: string;
  name?: string;
  room_type: "DIRECT" | "DEPARTMENT" | "TEAM" | "HIERARCHY";
  department?: string;
  team_id?: string;
  manager_id?: string;
  unread_count: number;
  last_message?: string;
  last_message_time?: string;
}

export interface ChatMessage {
  id: string;
  room_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  attachment_url?: string;
  attachment_name?: string;
  parent_id?: string;
  reactions: Record<string, string[]>;
  reply_count: number;
  created_at: string;
}

export interface SearchResult {
  id: string;
  room_id: string;
  room_name?: string;
  sender_id: string;
  sender_name: string;
  content_snippet: string;
  created_at: string;
}

export interface MessagesPage {
  items: ChatMessage[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface SearchPage {
  items: SearchResult[];
  next_cursor: string | null;
  has_more: boolean;
}

export const ChatAPI = {
  getRooms: (): Promise<ChatRoom[]> => fetchClient("/chat/rooms"),
  getMessages: (roomId: string, cursor?: string, size?: number): Promise<MessagesPage> => {
    const params = new URLSearchParams();
    if (cursor) params.set("cursor", cursor);
    if (size) params.set("size", String(size));
    const qs = params.toString();
    return fetchClient(`/chat/rooms/${roomId}/messages${qs ? `?${qs}` : ""}`);
  },
  createDirectRoom: (targetUserId: string): Promise<ChatRoom> =>
    fetchClient("/chat/rooms/direct", {
      method: "POST",
      body: JSON.stringify({ target_user_id: targetUserId }),
    }),
  uploadFile: async (
    roomId: string,
    file: File
  ): Promise<{ success: boolean; url: string; name: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchClient(`/chat/rooms/${roomId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  searchMessages: (q: string, roomId?: string, page?: number, limit?: number): Promise<SearchPage> => {
    const params = new URLSearchParams();
    params.set("q", q);
    if (roomId) params.set("room_id", roomId);
    if (page) params.set("page", String(page));
    if (limit) params.set("limit", String(limit));
    return fetchClient(`/chat/messages/search?${params.toString()}`);
  },

  getThreadMessages: (roomId: string, messageId: string): Promise<ChatMessage[]> =>
    fetchClient(`/chat/rooms/${roomId}/messages/${messageId}/thread`),

  replyToMessage: (roomId: string, messageId: string, content: string): Promise<ChatMessage> =>
    fetchClient(`/chat/rooms/${roomId}/messages/${messageId}/reply`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  reactToMessage: (roomId: string, messageId: string, emoji: string): Promise<ChatMessage> =>
    fetchClient(`/chat/rooms/${roomId}/messages/${messageId}/react`, {
      method: "POST",
      body: JSON.stringify({ emoji }),
    }),
};
