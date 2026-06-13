"use client";

import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { fetchClient } from "@/lib/api";
import { 
  Search, Eye, Trash2, Edit2, Calendar, Mail, Phone, Briefcase, 
  Tag, Clock, Plus, X, PlusCircle, MessageSquare, AlertCircle
} from "lucide-react";

interface Contact {
  id: string;
  orgId: string;
  email: string | null;
  phone: string | null;
  firstName: string | null;
  lastName: string | null;
  company: string | null;
  title: string | null;
  source: string | null;
  tags: string; // JSON array
  customFields: string; // JSON obj
  score: number;
  lastActivity: string | null;
  createdAt: string;
}

interface ContactsTableProps {
  orgId: string;
  refreshTrigger: number;
  isAddOpen: boolean;
  onCloseAdd: () => void;
  onContactAdded: () => void;
}

export default function ContactsTable({
  orgId,
  refreshTrigger,
  isAddOpen,
  onCloseAdd,
  onContactAdded,
}: ContactsTableProps) {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedContactId, setSelectedContactId] = useState<string | null>(null);
  const [detailedContact, setDetailedContact] = useState<any | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  
  // Note form state
  const [newActivityType, setNewActivityType] = useState<"note" | "email" | "call" | "meeting">("note");
  const [newActivityTitle, setNewActivityTitle] = useState("");
  const [newActivityContent, setNewActivityContent] = useState("");
  const [isSubmittingActivity, setIsSubmittingActivity] = useState(false);

  // Add Contact Form State
  const [newContactEmail, setNewContactEmail] = useState("");
  const [newContactPhone, setNewContactPhone] = useState("");
  const [newContactFirstName, setNewContactFirstName] = useState("");
  const [newContactLastName, setNewContactLastName] = useState("");
  const [newContactCompany, setNewContactCompany] = useState("");
  const [newContactTitle, setNewContactTitle] = useState("");
  const [newContactSource, setNewContactSource] = useState("manual");
  const [newContactTags, setNewContactTags] = useState("");
  const [isCreatingContact, setIsCreatingContact] = useState(false);

  const fetchContacts = useCallback(async () => {
    setIsLoading(true);
    try {
      const url = `/crm/contacts?orgId=${orgId}` + (searchQuery ? `&query=${encodeURIComponent(searchQuery)}` : "");
      const d = await fetchClient(url);
      setContacts(Array.isArray(d) ? d : (d.contacts || []));
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to load contacts.");
    } finally {
      setIsLoading(false);
    }
  }, [orgId, searchQuery]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts, refreshTrigger]);

  const fetchContactDetails = useCallback(async (id: string) => {
    setIsDetailLoading(true);
    try {
      const d = await fetchClient(`/crm/contacts/${id}`);
      setDetailedContact(d.contact || d);
    } catch (err: any) {
      console.error(err);
      toast.error("Failed to fetch contact details.");
    } finally {
      setIsDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedContactId) {
      fetchContactDetails(selectedContactId);
    } else {
      setDetailedContact(null);
    }
  }, [selectedContactId, fetchContactDetails]);

  // Handle Search Input Debounce / Action
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchContacts();
  };

  // Add Activity Submit
  const handleAddActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedContactId || !newActivityTitle.trim()) return;
    setIsSubmittingActivity(true);
    try {
      await fetchClient(`/crm/contacts/${selectedContactId}`, {
        method: "POST",
        body: JSON.stringify({
          type: newActivityType,
          title: newActivityTitle,
          content: newActivityContent,
        }),
      });
      toast.success("Activity logged successfully.");
      setNewActivityTitle("");
      setNewActivityContent("");
      fetchContactDetails(selectedContactId); // reload timeline
      fetchContacts(); // reload list (updates last activity)
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to save activity.");
    } finally {
      setIsSubmittingActivity(false);
    }
  };

  // Delete Contact Action
  const handleDeleteContact = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this contact? All related activities and deal associations will be removed.")) return;
    try {
      await fetchClient(`/crm/contacts/${id}`, { method: "DELETE" });
      toast.success("Contact deleted successfully.");
      if (selectedContactId === id) setSelectedContactId(null);
      fetchContacts();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to delete contact.");
    }
  };

  // Create Contact Submit
  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContactFirstName.trim() && !newContactLastName.trim()) {
      toast.error("Name is required");
      return;
    }
    setIsCreatingContact(true);
    try {
      const formattedTags = JSON.stringify(
        newContactTags.split(",").map(t => t.trim()).filter(t => t.length > 0)
      );
      await fetchClient("/crm/contacts", {
        method: "POST",
        body: JSON.stringify({
          company_name: newContactCompany || "Independent",
          industry: newContactTitle || undefined,
          website: undefined,
          primary_contact_name: `${newContactFirstName} ${newContactLastName}`.trim(),
          primary_contact_email: newContactEmail || undefined,
          primary_contact_phone: newContactPhone || undefined,
        }),
      });
      toast.success("Contact successfully created!");
      setNewContactEmail("");
      setNewContactPhone("");
      setNewContactFirstName("");
      setNewContactLastName("");
      setNewContactCompany("");
      setNewContactTitle("");
      setNewContactSource("manual");
      setNewContactTags("");
      onCloseAdd();
      onContactAdded();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to create contact");
    } finally {
      setIsCreatingContact(false);
    }
  };

  const getSourceBadgeColor = (src: string | null) => {
    switch (src?.toLowerCase()) {
      case "agent": return "bg-purple-500/10 border-purple-500/30 text-purple-400";
      case "api": return "bg-orange-500/10 border-orange-500/30 text-orange-400";
      case "import": return "bg-blue-500/10 border-blue-500/30 text-blue-400";
      default: return "bg-zinc-500/10 border-zinc-500/30 text-zinc-400";
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "email": return "✉️";
      case "call": return "📞";
      case "meeting": return "🤝";
      case "system": return "⚙️";
      default: return "📝";
    }
  };

  return (
    <div className="relative">
      {/* Grid view containing search bar and Table list */}
      <div className={`grid grid-cols-1 gap-6 transition-all duration-300 ${selectedContactId ? "lg:grid-cols-3" : "grid-cols-1"}`}>
        
        {/* Main List Table */}
        <div className={selectedContactId ? "lg:col-span-2 space-y-4" : "space-y-4"}>
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                className="input pl-10 text-xs py-2.5 bg-zinc-900/60 border-zinc-800 focus:border-[var(--accent-primary)] text-white w-full rounded-xl"
                placeholder="Search contacts by name, email, or company..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
            <button type="submit" className="btn-secondary px-5 text-xs font-bold rounded-xl border border-white/5 hover:bg-zinc-800">
              Search
            </button>
          </form>

          {/* Table Container */}
          <div className="glass-card overflow-hidden border border-white/5 rounded-2xl shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5 bg-white/[0.01] text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
                    <th className="px-6 py-4">Name</th>
                    <th className="px-6 py-4">Company / Title</th>
                    <th className="px-6 py-4">Contact Info</th>
                    <th className="px-6 py-4 text-center">Score</th>
                    <th className="px-6 py-4">Source</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs text-zinc-300">
                  {isLoading ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500 font-light">
                        <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-2" />
                        Loading contacts list...
                      </td>
                    </tr>
                  ) : contacts.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500 font-light space-y-1">
                        <AlertCircle className="w-6 h-6 text-zinc-600 mx-auto mb-2" />
                        <p>No contacts found in this organization.</p>
                        <p className="text-[10px] text-zinc-600">Try creating one or modifying your search filter.</p>
                      </td>
                    </tr>
                  ) : (
                    contacts.map((contact) => {
                      const tagsArr = (() => {
                        try { return JSON.parse(contact.tags || "[]"); } catch { return []; }
                      })();

                      return (
                        <tr 
                          key={contact.id} 
                          onClick={() => setSelectedContactId(contact.id)}
                          className={`hover:bg-white/[0.02] cursor-pointer transition-colors ${selectedContactId === contact.id ? "bg-white/[0.03]" : ""}`}
                        >
                          <td className="px-6 py-4">
                            <div className="font-semibold text-white">
                              {contact.firstName || ""} {contact.lastName || ""}
                              {(!contact.firstName && !contact.lastName) && (
                                <span className="text-zinc-500 italic">Unnamed</span>
                              )}
                            </div>
                            {tagsArr.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {tagsArr.slice(0, 3).map((t: string, idx: number) => (
                                  <span key={idx} className="bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono text-[9px] px-1.5 py-0.5 rounded">
                                    {t}
                                  </span>
                                ))}
                                {tagsArr.length > 3 && (
                                  <span className="text-[9px] text-zinc-500 px-1 py-0.5">+{tagsArr.length - 3}</span>
                                )}
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <div className="font-medium text-white">{contact.company || <span className="text-zinc-500 italic">—</span>}</div>
                            <div className="text-[10px] text-zinc-500">{contact.title || ""}</div>
                          </td>
                          <td className="px-6 py-4 space-y-1">
                            {contact.email && (
                              <div className="flex items-center gap-1.5 text-zinc-400 font-mono text-[10px]">
                                <Mail className="w-3 h-3 text-zinc-500" />
                                <span className="select-all">{contact.email}</span>
                              </div>
                            )}
                            {contact.phone && (
                              <div className="flex items-center gap-1.5 text-zinc-400 font-mono text-[10px]">
                                <Phone className="w-3 h-3 text-zinc-500" />
                                <span className="select-all">{contact.phone}</span>
                              </div>
                            )}
                            {!contact.email && !contact.phone && <span className="text-zinc-600 italic">—</span>}
                          </td>
                          <td className="px-6 py-4 text-center">
                            <span className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold ${
                              contact.score >= 70 ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                              contact.score >= 30 ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                              "bg-zinc-500/10 text-zinc-400 border border-zinc-600/20"
                            }`}>
                              {contact.score}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 border text-[9px] font-bold uppercase rounded-full tracking-wider ${getSourceBadgeColor(contact.source)}`}>
                              {contact.source || "manual"}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <div className="flex gap-2 justify-end">
                              <button 
                                onClick={(e) => { e.stopPropagation(); setSelectedContactId(contact.id); }}
                                className="btn-ghost p-1 text-zinc-400 hover:text-white"
                                title="View details"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={(e) => handleDeleteContact(contact.id, e)}
                                className="btn-ghost p-1 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                                title="Delete contact"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Slide-over Profile Detail Sidebar Panel */}
        {selectedContactId && (
          <div className="lg:col-span-1 glass-card border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl relative animate-slide-in bg-zinc-900/60 backdrop-blur-xl h-fit">
            <button 
              onClick={() => setSelectedContactId(null)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>

            {isDetailLoading ? (
              <div className="py-24 text-center text-zinc-500">
                <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-2" />
                Loading contact timeline...
              </div>
            ) : detailedContact ? (
              <div className="space-y-6">
                {/* Profile Header */}
                <div className="border-b border-white/5 pb-4">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center text-white font-extrabold text-lg mb-3">
                    {detailedContact.firstName?.[0] || detailedContact.lastName?.[0] || "?"}
                  </div>
                  <h3 className="text-base font-bold text-white leading-tight">
                    {detailedContact.firstName || ""} {detailedContact.lastName || ""}
                  </h3>
                  <p className="text-xs text-zinc-400 font-light mt-0.5">
                    {detailedContact.title ? `${detailedContact.title} at ` : ""}{detailedContact.company || "Independent"}
                  </p>
                </div>

                {/* Contact Data Details */}
                <div className="space-y-2.5 text-xs">
                  {detailedContact.email && (
                    <div className="flex items-center gap-2.5 text-zinc-300">
                      <Mail className="w-4 h-4 text-zinc-500 shrink-0" />
                      <span className="font-mono text-[10px] select-all">{detailedContact.email}</span>
                    </div>
                  )}
                  {detailedContact.phone && (
                    <div className="flex items-center gap-2.5 text-zinc-300">
                      <Phone className="w-4 h-4 text-zinc-500 shrink-0" />
                      <span className="font-mono text-[10px] select-all">{detailedContact.phone}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2.5 text-zinc-300">
                    <Clock className="w-4 h-4 text-zinc-500 shrink-0" />
                    <span>Last active: {detailedContact.lastActivity ? new Date(detailedContact.lastActivity).toLocaleDateString() : "Never"}</span>
                  </div>
                </div>

                {/* Linked Deals List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Linked Deals</h4>
                  {detailedContact.deals && detailedContact.deals.length > 0 ? (
                    <div className="space-y-2">
                      {detailedContact.deals.map((deal: any) => (
                        <div key={deal.id} className="p-2.5 bg-black/30 border border-white/5 rounded-xl text-xs space-y-1">
                          <div className="flex justify-between items-center font-semibold text-white">
                            <span className="truncate pr-2">{deal.title}</span>
                            <span className="text-[10px] text-[var(--accent-primary)] shrink-0">{deal.currency} {deal.value.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between items-center text-[10px] text-zinc-500">
                            <span className="capitalize">{deal.stage}</span>
                            <span>{deal.probability}% probability</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-zinc-500 italic">No deals linked to this contact.</p>
                  )}
                </div>

                {/* Log Activity Form */}
                <div className="border-t border-white/5 pt-4 space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Log Activity</h4>
                  <form onSubmit={handleAddActivity} className="space-y-3">
                    <div className="flex gap-2">
                      {["note", "email", "call", "meeting"].map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setNewActivityType(type as any)}
                          className={`capitalize px-2.5 py-1 text-[10px] font-bold rounded-lg border transition-all ${
                            newActivityType === type 
                              ? "bg-[var(--accent-primary)]/10 border-[var(--accent-primary)]/30 text-[var(--accent-primary)]"
                              : "bg-transparent border-white/5 text-zinc-400 hover:text-white"
                          }`}
                        >
                          {getActivityIcon(type)} {type}
                        </button>
                      ))}
                    </div>
                    
                    <input
                      className="input py-2 text-xs"
                      placeholder="Activity title (e.g., Follow up call)"
                      value={newActivityTitle}
                      onChange={e => setNewActivityTitle(e.target.value)}
                      required
                    />

                    <textarea
                      className="input py-2 text-xs"
                      placeholder="Add summary notes..."
                      rows={3}
                      value={newActivityContent}
                      onChange={e => setNewActivityContent(e.target.value)}
                    />

                    <button 
                      type="submit" 
                      disabled={isSubmittingActivity || !newActivityTitle.trim()}
                      className="btn-primary w-full py-2 text-[10px] font-bold flex items-center justify-center gap-1.5"
                    >
                      <PlusCircle className="w-3.5 h-3.5" />
                      {isSubmittingActivity ? "Logging..." : "Log Activity"}
                    </button>
                  </form>
                </div>

                {/* History Timeline */}
                <div className="border-t border-white/5 pt-4 space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Timeline</h4>
                  <div className="relative pl-4 border-l border-white/10 space-y-4 text-xs">
                    {detailedContact.activities && detailedContact.activities.length > 0 ? (
                      detailedContact.activities.map((act: any) => (
                        <div key={act.id} className="relative group">
                          {/* Timeline dot */}
                          <div className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border border-zinc-900 ${
                            act.type === "system" ? "bg-zinc-500" :
                            act.type === "email" ? "bg-blue-400" :
                            act.type === "call" ? "bg-orange-400" :
                            act.type === "meeting" ? "bg-purple-400" :
                            "bg-[var(--accent-primary)]"
                          }`} />
                          
                          <div className="space-y-0.5">
                            <div className="flex justify-between items-center text-[10px]">
                              <span className="font-semibold text-white">{act.title}</span>
                              <span className="text-[9px] text-zinc-500">{new Date(act.createdAt).toLocaleDateString()}</span>
                            </div>
                            <span className="text-[10px] text-zinc-500 block uppercase font-mono tracking-wide">{act.type}</span>
                            {act.content && (
                              <p className="text-[10px] text-zinc-400 bg-black/25 p-2 rounded-lg border border-white/5 mt-1 font-light whitespace-pre-wrap">
                                {act.content}
                              </p>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-[10px] text-zinc-500 italic pl-2">No timeline activity logged.</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center text-zinc-500 py-12">Contact details not found.</div>
            )}
          </div>
        )}
      </div>

      {/* Add Contact Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
          onClick={e => { if (e.target === e.currentTarget) onCloseAdd(); }}>
          <div className="glass-card p-8 w-full max-w-lg animate-slide-up relative bg-zinc-900/90 border border-white/5 shadow-2xl rounded-3xl">
            <button 
              onClick={onCloseAdd}
              className="absolute top-4 right-4 text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>
            
            <h2 className="text-xl font-bold text-white mb-6">Create New Contact</h2>

            <form onSubmit={handleCreateContact} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">First Name</label>
                  <input
                    className="input"
                    placeholder="e.g. John"
                    value={newContactFirstName}
                    onChange={e => setNewContactFirstName(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Last Name</label>
                  <input
                    className="input"
                    placeholder="e.g. Doe"
                    value={newContactLastName}
                    onChange={e => setNewContactLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Email Address</label>
                <input
                  type="email"
                  className="input"
                  placeholder="e.g. john@company.com"
                  value={newContactEmail}
                  onChange={e => setNewContactEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Phone Number</label>
                <input
                  className="input"
                  placeholder="e.g. +1 (555) 019-2834"
                  value={newContactPhone}
                  onChange={e => setNewContactPhone(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Company</label>
                  <input
                    className="input"
                    placeholder="e.g. Acme Corp"
                    value={newContactCompany}
                    onChange={e => setNewContactCompany(e.target.value)}
                  />
                </div>
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Title</label>
                  <input
                    className="input"
                    placeholder="e.g. Engineering Lead"
                    value={newContactTitle}
                    onChange={e => setNewContactTitle(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Lead Source</label>
                  <select 
                    className="input"
                    value={newContactSource}
                    onChange={e => setNewContactSource(e.target.value)}
                  >
                    <option value="manual">Manual Entry</option>
                    <option value="agent">AI Agent Chat</option>
                    <option value="api">External REST API</option>
                    <option value="import">CSV Import</option>
                  </select>
                </div>
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Tags (comma-separated)</label>
                  <input
                    className="input"
                    placeholder="e.g. VIP, Warm Lead, SaaS"
                    value={newContactTags}
                    onChange={e => setNewContactTags(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button type="button" onClick={onCloseAdd} disabled={isCreatingContact} className="btn-secondary flex-1 py-3 font-bold rounded-xl">
                  Cancel
                </button>
                <button type="submit" className="btn-primary flex-1 py-3 font-bold rounded-xl shadow-lg shadow-[var(--accent-primary)]/10" disabled={isCreatingContact}>
                  {isCreatingContact ? "Creating Contact..." : "Create Contact"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
