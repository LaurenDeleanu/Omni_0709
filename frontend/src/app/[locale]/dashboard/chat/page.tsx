"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { 
  MessageSquare, Send, Paperclip, X, FileText, Image as ImageIcon,
  Users, Hash, ShieldAlert, Plus, Search, Loader2, Award, ChevronRight, User,
  Reply, XCircle
} from "lucide-react";
import { ChatAPI, ChatRoom, ChatMessage, SearchResult } from "@/lib/api/chat";
import { API_BASE } from "@/lib/api/client";
import { UserAPI, Employee } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "👏"];

export default function ChatDashboardPage() {
  const { user } = useUser();
  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [activeRoom, setActiveRoom] = useState<ChatRoom | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  
  const [messageText, setMessageText] = useState("");
  const [attachment, setAttachment] = useState<{ url: string; name: string } | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const [showDmModal, setShowDmModal] = useState(false);
  const [dmSearch, setDmSearch] = useState("");
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Record<string, string>>({});

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  const [threadMessage, setThreadMessage] = useState<ChatMessage | null>(null);
  const [threadMessages, setThreadMessages] = useState<ChatMessage[]>([]);
  const [threadReply, setThreadReply] = useState("");

  const [hoveredMsgId, setHoveredMsgId] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  const loadRooms = async (selectFirst = false) => {
    try {
      const data = await ChatAPI.getRooms();
      setRooms(data);
      if (selectFirst && data.length > 0 && !activeRoom) {
        setActiveRoom(data[0]);
      }
    } catch (err) {
      console.error("Error loading chat rooms:", err);
      toast.error("No se pudieron cargar las salas de chat");
    } finally {
      setLoadingRooms(false);
    }
  };

  useEffect(() => {
    loadRooms(true);
    UserAPI.getEmployees()
      .then((data: any) => setEmployees(data))
      .catch((err) => console.error("Error loading employees:", err));
  }, []);

  useEffect(() => {
    if (!activeRoom) return;
    setLoadingMessages(true);
    setMessages([]);
    setTypingUsers({});
    isTypingRef.current = false;
    setThreadMessage(null);
    setThreadMessages([]);
    
    ChatAPI.getMessages(activeRoom.id)
      .then((data) => {
        setMessages(data.items);
        setRooms(prev => prev.map(r => r.id === activeRoom.id ? { ...r, unread_count: 0 } : r));
      })
      .catch((err) => {
        console.error("Error loading messages:", err);
        toast.error("Error al cargar el historial de mensajes");
      })
      .finally(() => {
        setLoadingMessages(false);
      });
  }, [activeRoom]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingUsers]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threadMessages]);

  useEffect(() => {
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const baseUrl = API_BASE.startsWith("http") ? API_BASE : `${window.location.protocol}//${window.location.host}${API_BASE}`;
    const wsUrl = baseUrl.replace(/^http/, "ws") + "/chat/ws";

    const connectWs = () => {
      fetch(`${API_BASE}/chat/ws-token`, { credentials: "include" })
        .then(r => r.ok ? r.json() : Promise.reject("ws-token failed"))
        .then(d => { openWs(`${wsUrl}?token=${d.ws_token}`); })
        .catch(() => { openWs(`${wsUrl}`); });
    };

    const openWs = (url: string) => {
      if (wsRef.current) wsRef.current.close();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => console.log("Chat WebSocket connected");
      ws.onerror = () => {};
      ws.onclose = () => { console.log("Chat WebSocket closed, reconnecting..."); setTimeout(connectWs, 3000); };

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        const { action, data } = payload;
        if (action === "message") {
          setMessages((prev) => [...prev, data]);
          setTypingUsers((prev) => { const next = { ...prev }; delete next[data.sender_id]; return next; });
          setRooms((prev) => prev.map(r => {
            const newUnread = r.id === data.room_id
              ? (r.id === activeRoom?.id ? 0 : r.unread_count + 1)
              : r.unread_count;
            return r.id === data.room_id
              ? { ...r, unread_count: newUnread, last_message: data.content, last_message_time: data.created_at }
              : r;
          }));
        }
        if (action === "thread_reply") {
          const newMsg: ChatMessage = { ...data, attachment_url: undefined, attachment_name: undefined };
          if (data.parent_id === threadMessage?.id) {
            setThreadMessages((prev) => [...prev, newMsg]);
          }
          setMessages((prev) => prev.map(m =>
            m.id === data.parent_id ? { ...m, reply_count: data.reply_count ?? (m.reply_count + 1) } : m
          ));
        }
        if (action === "reaction") {
          setMessages((prev) => prev.map(m =>
            m.id === data.message_id ? { ...m, reactions: data.reactions } : m
          ));
          if (threadMessage?.id === data.message_id) {
            setThreadMessage((prev) => prev ? { ...prev, reactions: data.reactions } : null);
          }
        }
      };
    };

    connectWs();
    return () => { wsRef.current?.close(); };
  }, [activeRoom, threadMessage]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if ((!messageText.trim() && !attachment) || !activeRoom || !wsRef.current) return;

    const payload = {
      action: "message",
      room_id: activeRoom.id,
      content: messageText.trim(),
      attachment_url: attachment?.url || null,
      attachment_name: attachment?.name || null
    };

    wsRef.current.send(JSON.stringify(payload));
    setMessageText("");
    setAttachment(null);
    sendTypingStatus(false);
  };

  const sendTypingStatus = (isTyping: boolean) => {
    if (!activeRoom || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      action: "typing",
      room_id: activeRoom.id,
      is_typing: isTyping
    }));
    isTypingRef.current = isTyping;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMessageText(e.target.value);
    if (!isTypingRef.current) {
      sendTypingStatus(true);
    }
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = setTimeout(() => {
      sendTypingStatus(false);
    }, 2000);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeRoom) return;
    setIsUploading(true);
    try {
      const res = await ChatAPI.uploadFile(activeRoom.id, file);
      setAttachment({ url: res.url, name: res.name });
      toast.success("Archivo subido correctamente");
    } catch (err) {
      console.error(err);
      toast.error("Error al subir archivo");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await ChatAPI.searchMessages(q);
        setSearchResults(res.items);
        setShowSearchDropdown(true);
      } catch (err) {
        console.error("Search error:", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);
  }, []);

  const handleSearchResultClick = (result: SearchResult) => {
    const room = rooms.find(r => r.id === result.room_id);
    if (room) {
      setActiveRoom(room);
      setSearchQuery("");
      setSearchResults([]);
      setShowSearchDropdown(false);
    }
  };

  const openThread = async (message: ChatMessage) => {
    setThreadMessage(message);
    try {
      const replies = await ChatAPI.getThreadMessages(message.room_id, message.id);
      setThreadMessages(replies);
    } catch (err) {
      console.error("Error loading thread:", err);
      setThreadMessages([]);
    }
  };

  const closeThread = () => {
    setThreadMessage(null);
    setThreadMessages([]);
    setThreadReply("");
  };

  const handleThreadReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!threadReply.trim() || !activeRoom || !threadMessage) return;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: "message",
        room_id: activeRoom.id,
        content: threadReply.trim(),
        parent_id: threadMessage.id
      }));
      setThreadReply("");
    } else {
      try {
        await ChatAPI.replyToMessage(activeRoom.id, threadMessage.id, threadReply.trim());
        const replies = await ChatAPI.getThreadMessages(activeRoom.id, threadMessage.id);
        setThreadMessages(replies);
        setThreadReply("");
        setMessages(prev => prev.map(m =>
          m.id === threadMessage.id ? { ...m, reply_count: m.reply_count + 1 } : m
        ));
      } catch (err) {
        toast.error("Error al enviar respuesta");
      }
    }
  };

  const handleReaction = async (message: ChatMessage, emoji: string) => {
    try {
      await ChatAPI.reactToMessage(message.room_id, message.id, emoji);
    } catch (err) {
      toast.error("Error al reaccionar");
    }
  };

  const filteredEmployees = employees.filter(emp => {
    if (!user || emp.id === user.id) return false;
    const isSameDept = user.department && emp.department === user.department;
    const isReport = user.manager_id === emp.id || emp.manager_id === user.id;
    const matchesSearch = 
      emp.full_name?.toLowerCase().includes(dmSearch.toLowerCase()) ||
      emp.email.toLowerCase().includes(dmSearch.toLowerCase());
    return (isSameDept || isReport) && matchesSearch;
  });

  const handleStartDm = async (employeeId: string) => {
    try {
      const room = await ChatAPI.createDirectRoom(employeeId);
      await loadRooms();
      setActiveRoom(room);
      setShowDmModal(false);
      setDmSearch("");
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || "No se pudo abrir el chat directo");
    }
  };

  const departmentRooms = rooms.filter(r => r.room_type === "DEPARTMENT");
  const teamRooms = rooms.filter(r => r.room_type === "TEAM");
  const hierarchyRooms = rooms.filter(r => r.room_type === "HIERARCHY");
  const dmRooms = rooms.filter(r => r.room_type === "DIRECT");

  return (
    <div className="flex h-[80vh] border border-border/40 rounded-2xl overflow-hidden bg-card/40 backdrop-blur-xl">
      {/* Sidebar */}
      <div className="w-80 border-r border-border/30 flex flex-col bg-muted/30">
        <div className="p-4 border-b border-border/20 flex justify-between items-center">
          <div>
            <h2 className="font-extrabold text-sm tracking-tight text-foreground flex items-center gap-1.5">
              💬 SAS Chat Interno
            </h2>
            <p className="text-[10px] text-muted-foreground">Estructurado por Organización</p>
          </div>
          <Button 
            onClick={() => setShowDmModal(true)} 
            size="icon" 
            variant="ghost" 
            className="h-8 w-8 text-indigo-400 hover:text-foreground hover:bg-white/5"
            title="Nuevo Chat Directo"
          >
            <Plus size={18} />
          </Button>
        </div>

        {/* Search Bar */}
        <div className="px-3 py-2 relative" ref={sidebarRef}>
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-zinc-500" />
            <input
              type="text"
              placeholder="Buscar mensajes..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              onFocus={() => { if (searchResults.length > 0) setShowSearchDropdown(true); }}
              onBlur={() => setTimeout(() => setShowSearchDropdown(false), 200)}
              className="w-full bg-slate-900 border border-zinc-800 focus:border-indigo-500/50 rounded-lg pl-8 pr-7 py-1.5 text-[11px] text-foreground placeholder-zinc-600 focus:outline-none transition-colors"
            />
            {isSearching && <Loader2 size={12} className="absolute right-2.5 top-2 animate-spin text-zinc-500" />}
            {!isSearching && searchQuery && (
              <button onClick={() => { setSearchQuery(""); setSearchResults([]); setShowSearchDropdown(false); }} className="absolute right-2.5 top-2">
                <X size={12} className="text-zinc-500 hover:text-foreground" />
              </button>
            )}
          </div>

          {showSearchDropdown && searchResults.length > 0 && (
            <div className="absolute left-3 right-3 top-12 z-40 bg-slate-900 border border-border/30 rounded-xl shadow-2xl max-h-64 overflow-y-auto custom-scrollbar">
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onMouseDown={() => handleSearchResultClick(r)}
                  className="w-full text-left px-3 py-2.5 hover:bg-white/5 border-b border-border/10 last:border-b-0 transition-colors"
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-[10px] font-bold text-indigo-400">{r.sender_name}</span>
                    <span className="text-[9px] text-zinc-600">{r.room_name}</span>
                  </div>
                  <p className="text-[10px] text-zinc-400 truncate">{r.content_snippet}</p>
                </button>
              ))}
            </div>
          )}

          {showSearchDropdown && searchQuery && searchResults.length === 0 && !isSearching && (
            <div className="absolute left-3 right-3 top-12 z-40 bg-slate-900 border border-border/30 rounded-xl shadow-2xl p-4 text-center">
              <p className="text-[10px] text-zinc-500">Sin resultados para &quot;{searchQuery}&quot;</p>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-4 custom-scrollbar text-xs">
          <div className="space-y-1">
            <h3 className="px-2.5 py-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1">
              🏢 Departamentos
            </h3>
            {departmentRooms.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room)}
                className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center justify-between transition-colors ${
                  activeRoom?.id === room.id 
                    ? "bg-indigo-600 text-foreground font-bold" 
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <Hash size={14} className="shrink-0" />
                  <span className="truncate">{room.name}</span>
                </div>
                {room.unread_count > 0 && (
                  <span className="bg-rose-500 text-foreground text-[9px] rounded-full px-1.5 py-0.5 font-bold">
                    {room.unread_count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="space-y-1">
            <h3 className="px-2.5 py-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1">
              👥 Equipos
            </h3>
            {teamRooms.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room)}
                className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center justify-between transition-colors ${
                  activeRoom?.id === room.id 
                    ? "bg-indigo-600 text-foreground font-bold" 
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <Users size={14} className="shrink-0" />
                  <span className="truncate">{room.name}</span>
                </div>
                {room.unread_count > 0 && (
                  <span className="bg-rose-500 text-foreground text-[9px] rounded-full px-1.5 py-0.5 font-bold">
                    {room.unread_count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="space-y-1">
            <h3 className="px-2.5 py-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1">
              👑 Jerarquía
            </h3>
            {hierarchyRooms.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room)}
                className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center justify-between transition-colors ${
                  activeRoom?.id === room.id 
                    ? "bg-indigo-600 text-foreground font-bold" 
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <User size={14} className="shrink-0" />
                  <span className="truncate">{room.name}</span>
                </div>
                {room.unread_count > 0 && (
                  <span className="bg-rose-500 text-foreground text-[9px] rounded-full px-1.5 py-0.5 font-bold">
                    {room.unread_count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="space-y-1">
            <h3 className="px-2.5 py-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1">
              💬 Mensajes Directos
            </h3>
            {dmRooms.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room)}
                className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center justify-between transition-colors ${
                  activeRoom?.id === room.id 
                    ? "bg-indigo-600 text-foreground font-bold" 
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <div className="h-4.5 w-4.5 rounded-md bg-white/10 flex items-center justify-center text-[10px] font-bold shrink-0">
                    {room.name ? room.name[0].toUpperCase() : "U"}
                  </div>
                  <span className="truncate">{room.name}</span>
                </div>
                {room.unread_count > 0 && (
                  <span className="bg-rose-500 text-foreground text-[9px] rounded-full px-1.5 py-0.5 font-bold">
                    {room.unread_count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="p-3.5 border-t border-border/20 bg-slate-950/20 flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-xs text-indigo-400 font-bold">
            {user?.full_name ? user.full_name.split(" ").map((n: any) => n[0]).slice(0,2).join("").toUpperCase() : "U"}
          </div>
          <div className="flex-1 truncate">
            <p className="font-bold text-xs text-foreground truncate leading-tight">{user?.full_name}</p>
            <p className="text-[9px] text-zinc-500 truncate leading-tight">{user?.department || "SAS Employee"}</p>
          </div>
        </div>
      </div>

      {/* Main Conversation Feed */}
      <div className="flex-1 flex flex-col bg-slate-950/15">
        {activeRoom ? (
          <>
            <div className="px-5 py-4 border-b border-border/20 bg-slate-900/10 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-lg">
                  {activeRoom.room_type === "DEPARTMENT" ? "🏢" : 
                   activeRoom.room_type === "TEAM" ? "👥" : 
                   activeRoom.room_type === "HIERARCHY" ? "👑" : "💬"}
                </span>
                <div>
                  <h3 className="font-bold text-sm text-foreground">{activeRoom.name}</h3>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
                    Canal {activeRoom.room_type} • Retención 90 días
                  </p>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
              {loadingMessages ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center space-y-2">
                    <Loader2 size={24} className="animate-spin text-indigo-500 mx-auto" />
                    <p className="text-xs text-muted-foreground">Cargando conversación...</p>
                  </div>
                </div>
              ) : messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-2">
                  <MessageSquare size={32} className="text-zinc-700" />
                  <h4 className="font-bold text-xs text-zinc-400">Canal vacío</h4>
                  <p className="text-[10px] text-zinc-500 max-w-xs leading-normal">
                    Los mensajes se encriptan al enviarse y se borrarán automáticamente pasados 90 días por directiva GDPR.
                  </p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isMine = msg.sender_id === user?.id;
                  return (
                    <div 
                      key={msg.id} 
                      className={`relative flex ${isMine ? "justify-end" : "justify-start"} animate-fade-in group`}
                      onMouseEnter={() => setHoveredMsgId(msg.id)}
                      onMouseLeave={() => setHoveredMsgId(null)}
                    >
                      <div className="max-w-[70%] space-y-1">
                        {!isMine && (
                          <span className="text-[9px] text-zinc-500 font-semibold pl-2">
                            {msg.sender_name}
                          </span>
                        )}
                        <div className={`p-3 rounded-2xl text-xs leading-relaxed border ${
                          isMine 
                            ? "bg-indigo-600 border-indigo-500 text-foreground rounded-tr-none" 
                            : "bg-muted border border-border text-zinc-200 rounded-tl-none"
                        }`}>
                          {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
                          
                          {msg.attachment_url && (
                            <div className={`mt-2 flex items-center gap-2 p-2 rounded-lg border text-[10px] ${
                              isMine 
                                ? "bg-indigo-700/50 border-indigo-400/25" 
                                : "bg-black/30 border-zinc-800"
                            }`}>
                              {msg.attachment_name?.match(/\.(jpeg|jpg|gif|png)$/i) ? (
                                <ImageIcon size={14} className="text-zinc-400 shrink-0" />
                              ) : (
                                <FileText size={14} className="text-zinc-400 shrink-0" />
                              )}
                              <a 
                                href={msg.attachment_url} 
                                target="_blank" 
                                rel="noreferrer" 
                                className="underline truncate font-semibold text-zinc-300 hover:text-foreground"
                              >
                                {msg.attachment_name}
                              </a>
                            </div>
                          )}

                          <span className={`block text-[8px] text-right mt-1.5 font-bold tracking-wider ${
                            isMine ? "text-indigo-200" : "text-zinc-500"
                          }`}>
                            {new Date(msg.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        {/* Reactions Bar */}
                        {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                          <div className="flex flex-wrap gap-1 px-1">
                            {Object.entries(msg.reactions).map(([emoji, users]) => (
                              <button
                                key={emoji}
                                onClick={() => handleReaction(msg, emoji)}
                                className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[11px] border transition-colors ${
                                  user?.id && (users as string[]).includes(user.id)
                                    ? "bg-indigo-600/30 border-indigo-500/40 text-indigo-300"
                                    : "bg-white/5 border-white/10 text-zinc-400 hover:bg-white/10"
                                }`}
                              >
                                <span>{emoji}</span>
                                <span className="text-[9px] font-bold">{(users as string[]).length}</span>
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Reply count badge */}
                        {msg.reply_count > 0 && (
                          <button
                            onClick={() => openThread(msg)}
                            className="text-[9px] text-indigo-400 hover:text-indigo-300 font-semibold pl-2 transition-colors"
                          >
                            {msg.reply_count} {msg.reply_count === 1 ? "respuesta" : "respuestas"}
                          </button>
                        )}
                      </div>

                      {/* Hover reaction picker + reply button */}
                      {hoveredMsgId === msg.id && (
                        <div className={`absolute ${isMine ? "right-2 -top-7" : "left-2 -top-7"} flex items-center gap-0.5 bg-slate-900 border border-border/40 rounded-lg px-1.5 py-1 shadow-xl z-10`}>
                          {REACTIONS.map((emoji) => (
                            <button
                              key={emoji}
                              onClick={() => handleReaction(msg, emoji)}
                              className="p-0.5 hover:bg-white/10 rounded transition-colors text-sm"
                            >
                              {emoji}
                            </button>
                          ))}
                          <div className="w-px h-4 bg-border/40 mx-0.5" />
                          <button
                            onClick={() => openThread(msg)}
                            className="p-0.5 hover:bg-white/10 rounded text-zinc-400 hover:text-foreground"
                            title="Responder en hilo"
                          >
                            <Reply size={13} />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {Object.keys(typingUsers).map((typingUid) => (
                <div key={typingUid} className="flex justify-start items-center gap-1.5 text-[10px] text-zinc-500 italic pl-2">
                  <span className="font-semibold">{typingUsers[typingUid]}</span> está escribiendo
                  <span className="flex gap-0.5">
                    <span className="h-1 w-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-1 w-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-1 w-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                </div>
              ))}

              <div ref={messagesEndRef} />
            </div>

            {attachment && (
              <div className="px-5 py-2.5 border-t border-border/20 bg-muted/30 flex items-center justify-between gap-3 text-xs shrink-0">
                <div className="flex items-center gap-2 text-indigo-400 truncate">
                  <FileText size={14} />
                  <span className="truncate font-semibold">{attachment.name}</span>
                </div>
                <Button 
                  onClick={() => setAttachment(null)} 
                  variant="ghost" 
                  size="icon" 
                  className="h-6 w-6 text-zinc-500 hover:text-foreground hover:bg-white/5"
                >
                  <X size={14} />
                </Button>
              </div>
            )}

            <form onSubmit={handleSendMessage} className="p-4 border-t border-border/20 bg-slate-950/20 shrink-0 flex gap-2 items-center">
              <label className="cursor-pointer p-2.5 bg-slate-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-foreground rounded-xl transition-colors shrink-0">
                <Paperclip size={14} />
                <input type="file" onChange={handleFileUpload} disabled={isUploading} className="hidden" />
              </label>
              <input
                type="text"
                value={messageText}
                onChange={handleInputChange}
                placeholder={isUploading ? "Subiendo archivo..." : "Escribe un mensaje aquí..."}
                disabled={isUploading}
                className="flex-1 bg-slate-900 border border-zinc-800 focus:border-indigo-500/50 rounded-xl px-4 py-2.5 text-xs text-foreground placeholder-zinc-600 focus:outline-none transition-colors disabled:opacity-50"
              />
              <Button
                type="submit"
                disabled={isUploading || (!messageText.trim() && !attachment)}
                className="bg-indigo-600 hover:bg-indigo-700 text-foreground p-2.5 h-auto rounded-xl shadow-md cursor-pointer shrink-0"
              >
                <Send size={14} />
              </Button>
            </form>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-6">
            <MessageSquare size={48} className="text-zinc-800 mb-2" />
            <h3 className="font-extrabold text-sm text-zinc-400">Mensajería SAS</h3>
            <p className="text-xs text-zinc-500 max-w-sm mt-1 leading-relaxed">
              Selecciona un canal del panel lateral o abre un chat directo para comunicarte con tus compañeros elegibles en base a departamentos y jerarquía.
            </p>
          </div>
        )}
      </div>

      {/* Thread Panel */}
      {threadMessage && (
        <div className="w-80 border-l border-border/30 flex flex-col bg-slate-900/50 shrink-0">
          <div className="p-3 border-b border-border/20 flex justify-between items-center shrink-0">
            <div>
              <h3 className="font-bold text-[11px] text-foreground">Hilo</h3>
              <p className="text-[9px] text-zinc-500 truncate max-w-[180px]">{threadMessage.content}</p>
            </div>
            <Button onClick={closeThread} variant="ghost" size="icon" className="h-6 w-6 text-zinc-400 hover:text-foreground">
              <X size={14} />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
            {/* Original message */}
            <div className="p-2.5 rounded-xl bg-slate-900 border border-zinc-800">
              <span className="text-[9px] text-zinc-500 font-semibold">{threadMessage.sender_name}</span>
              <p className="text-[10px] text-zinc-200 whitespace-pre-wrap mt-0.5">{threadMessage.content}</p>
              <span className="block text-[7px] text-right mt-1 text-zinc-600">
                {new Date(threadMessage.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {threadMessages.map((tmsg) => (
              <div key={tmsg.id} className="p-2.5 rounded-xl bg-slate-900 border border-zinc-800">
                <span className="text-[9px] text-zinc-500 font-semibold">{tmsg.sender_name}</span>
                <p className="text-[10px] text-zinc-200 whitespace-pre-wrap mt-0.5">{tmsg.content}</p>
                <span className="block text-[7px] text-right mt-1 text-zinc-600">
                  {new Date(tmsg.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}

            {threadMessages.length === 0 && (
              <p className="text-[9px] text-zinc-600 text-center py-6">Sin respuestas aún</p>
            )}

            <div ref={threadEndRef} />
          </div>

          <form onSubmit={handleThreadReply} className="p-3 border-t border-border/20 bg-slate-950/20 shrink-0 flex gap-2 items-center">
            <input
              type="text"
              value={threadReply}
              onChange={(e) => setThreadReply(e.target.value)}
              placeholder="Responder en hilo..."
              className="flex-1 bg-slate-900 border border-zinc-800 focus:border-indigo-500/50 rounded-lg px-3 py-1.5 text-[10px] text-foreground placeholder-zinc-600 focus:outline-none"
            />
            <Button type="submit" disabled={!threadReply.trim()} className="bg-indigo-600 hover:bg-indigo-700 text-foreground p-1.5 h-auto rounded-lg shrink-0">
              <Send size={11} />
            </Button>
          </form>
        </div>
      )}

      {/* Direct Message Starter Modal */}
      {showDmModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <Card className="w-full max-w-md shadow-2xl glass border border-border/40 animate-in zoom-in-95 duration-200">
            <CardHeader className="p-4 border-b border-border/20 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                  💬 Iniciar Chat Directo
                </CardTitle>
                <CardDescription className="text-[10px]">
                  Bajo directiva, solo se permiten DMs en tu mismo departamento o reporte jerárquico.
                </CardDescription>
              </div>
              <Button 
                onClick={() => { setShowDmModal(false); setDmSearch(""); }} 
                variant="ghost" 
                size="icon" 
                className="h-7 w-7 text-zinc-400 hover:text-foreground"
              >
                <X size={16} />
              </Button>
            </CardHeader>

            <CardContent className="p-4 space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Buscar colega por nombre o email..."
                  value={dmSearch}
                  onChange={(e) => setDmSearch(e.target.value)}
                  className="w-full bg-slate-900 border border-zinc-800 focus:border-indigo-500/50 rounded-lg pl-9 pr-3 py-2 text-xs text-foreground focus:outline-none transition-colors"
                />
              </div>

              <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
                {filteredEmployees.length === 0 ? (
                  <p className="text-[10px] text-center text-zinc-500 py-6">
                    No se encontraron compañeros disponibles para chatear bajo tus restricciones.
                  </p>
                ) : (
                  filteredEmployees.map((emp) => (
                    <button
                      key={emp.id}
                      onClick={() => handleStartDm(emp.id)}
                      className="w-full text-left p-2 hover:bg-white/5 border border-transparent hover:border-border/20 rounded-xl flex items-center justify-between transition-all group"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <div className="h-7 w-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-[10px] font-bold text-indigo-400 border border-indigo-500/20">
                          {emp.full_name ? emp.full_name.split(" ").map((n) => n[0]).slice(0,2).join("").toUpperCase() : "U"}
                        </div>
                        <div className="truncate leading-tight">
                          <p className="font-bold text-xs text-foreground truncate">{emp.full_name}</p>
                          <p className="text-[9px] text-zinc-500 truncate">{emp.department || "SAS Employee"}</p>
                        </div>
                      </div>
                      <ChevronRight size={14} className="text-zinc-500 group-hover:text-foreground transition-colors" />
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
