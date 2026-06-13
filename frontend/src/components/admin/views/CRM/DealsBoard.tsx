"use client";

import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { fetchClient } from "@/lib/api";
import { 
  X, Plus, Edit2, Trash2, Calendar, Target, DollarSign, 
  ArrowRight, AlertCircle, Eye, User, Briefcase, PlusCircle, MessageSquare
} from "lucide-react";

const PRESET_COLORS = [
  "#6366f1", // Indigo
  "#3b82f6", // Blue
  "#06b6d4", // Cyan
  "#10b981", // Emerald
  "#eab308", // Yellow
  "#f97316", // Orange
  "#ef4444", // Red
  "#ec4899", // Pink
  "#a855f7", // Purple
  "#71717a", // Zinc
];

interface Deal {
  id: string;
  orgId: string;
  contactId: string;
  title: string;
  value: number;
  currency: string;
  stage: string;
  probability: number;
  closeDate: string | null;
  assignedTo: string | null;
  customFields: string;
  createdAt: string;
  contact?: {
    id: string;
    firstName: string | null;
    lastName: string | null;
    company: string | null;
    email: string | null;
  };
}

interface Stage {
  id: string;
  name: string;
  color: string;
}

interface DealsBoardProps {
  orgId: string;
  refreshTrigger: number;
  refreshContactsTrigger: number;
  isAddOpen: boolean;
  onCloseAdd: () => void;
  onDealAdded: () => void;
}

export default function DealsBoard({
  orgId,
  refreshTrigger,
  refreshContactsTrigger,
  isAddOpen,
  onCloseAdd,
  onDealAdded,
}: DealsBoardProps) {
  const [stages, setStages] = useState<Stage[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [selectedDealId, setSelectedDealId] = useState<string | null>(null);
  const [detailedDeal, setDetailedDeal] = useState<any | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [draggedDealId, setDraggedDealId] = useState<string | null>(null);

  // New Deal form state
  const [newDealTitle, setNewDealTitle] = useState("");
  const [newDealValue, setNewDealValue] = useState("");
  const [newDealContactId, setNewDealContactId] = useState("");
  const [newDealStage, setNewDealStage] = useState("");
  const [newDealProbability, setNewDealProbability] = useState("50");
  const [newDealCloseDate, setNewDealCloseDate] = useState("");
  const [isCreatingDeal, setIsCreatingDeal] = useState(false);

  // Deal Edit Form state
  const [editDealValue, setEditDealValue] = useState("");
  const [editDealStage, setEditDealStage] = useState("");
  const [editDealProbability, setEditDealProbability] = useState("");
  const [editDealCloseDate, setEditDealCloseDate] = useState("");
  const [isUpdatingDeal, setIsUpdatingDeal] = useState(false);

  // Deal Activity state
  const [newActivityType, setNewActivityType] = useState<"note" | "email" | "call">("note");
  const [newActivityTitle, setNewActivityTitle] = useState("");
  const [newActivityContent, setNewActivityContent] = useState("");
  const [isSubmittingActivity, setIsSubmittingActivity] = useState(false);

  const fetchPipelineAndDeals = useCallback(async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Stages
      const d = await fetchClient("/crm/stages");
      let currentStages: Stage[] = [];
      if (Array.isArray(d)) {
        currentStages = d.map((name: string, index: number) => ({
          id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
          name: name.charAt(0).toUpperCase() + name.slice(1),
          color: PRESET_COLORS[index % PRESET_COLORS.length]
        }));
        setStages(currentStages);
      }

      // 2. Fetch Deals
      const dd = await fetchClient("/crm/leads");
      const rawLeads = Array.isArray(dd) ? dd : (dd.deals || []);
      const enrichedLeads = rawLeads.map((l: any) => ({
        ...l,
        value: l.estimated_value || l.value || 0,
        contact: l.contact || {
          id: l.client_id,
          firstName: l.contact_name || "",
          lastName: "",
          company: l.company_name || ""
        }
      }));
      setDeals(enrichedLeads);
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to fetch deals board.");
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  const fetchContacts = useCallback(async () => {
    try {
      const d = await fetchClient("/crm/contacts");
      const list = Array.isArray(d) ? d : (d.contacts || []);
      const mappedList = list.map((c: any) => ({
        id: c.id,
        firstName: c.primary_contact_name || c.firstName || "",
        lastName: c.lastName || "",
        company: c.company_name || c.company || ""
      }));
      setContacts(mappedList);
      if (mappedList.length > 0 && !newDealContactId) {
        setNewDealContactId(mappedList[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [orgId, newDealContactId]);

  useEffect(() => {
    fetchPipelineAndDeals();
  }, [fetchPipelineAndDeals, refreshTrigger]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts, refreshContactsTrigger]);

  const fetchDealDetails = useCallback(async (id: string) => {
    setIsDetailLoading(true);
    try {
      const d = await fetchClient(`/crm/leads/${id}`);
      const dealData = d.deal || d;
      const enriched = {
        ...dealData,
        value: dealData.estimated_value || dealData.value || 0,
        contact: dealData.contact || {
          id: dealData.client_id,
          firstName: dealData.contact_name || "",
          lastName: "",
          company: dealData.company_name || ""
        }
      };
      setDetailedDeal(enriched);
      setEditDealValue(enriched.value.toString());
      setEditDealStage(enriched.stage);
      setEditDealProbability(enriched.probability.toString());
      setEditDealCloseDate(enriched.expected_close_date ? enriched.expected_close_date.substring(0, 10) : (enriched.closeDate ? enriched.closeDate.substring(0, 10) : ""));
    } catch (err) {
      console.error(err);
      toast.error("Failed to load deal details.");
    } finally {
      setIsDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDealId) {
      fetchDealDetails(selectedDealId);
    } else {
      setDetailedDeal(null);
    }
  }, [selectedDealId, fetchDealDetails]);

  // Native HTML5 Drag and Drop Handlers
  const handleDragStart = (e: React.DragEvent, dealId: string) => {
    setDraggedDealId(dealId);
    e.dataTransfer.setData("text/plain", dealId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, targetStage: string) => {
    e.preventDefault();
    const dealId = e.dataTransfer.getData("text/plain") || draggedDealId;
    if (!dealId) return;

    const originalDeals = [...deals];
    const targetDeal = deals.find(d => d.id === dealId);
    if (!targetDeal) return;

    if (targetDeal.stage === targetStage) return;

    setDeals(prevDeals => 
      prevDeals.map(d => d.id === dealId ? { ...d, stage: targetStage } : d)
    );

    try {
      await fetchClient(`/crm/leads/${dealId}/stage`, {
        method: "PATCH",
        body: JSON.stringify({ stage: targetStage }),
      });
      toast.success(`Deal stage changed successfully.`);
      if (selectedDealId === dealId) {
        fetchDealDetails(dealId); // reload activities
      }
    } catch (err) {
      console.error(err);
      setDeals(originalDeals);
      toast.error("Failed to update deal stage.");
    } finally {
      setDraggedDealId(null);
    }
  };

  // Create Deal Submit
  const handleCreateDeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDealTitle.trim() || !newDealContactId) {
      toast.error("Title and Contact are required");
      return;
    }
    setIsCreatingDeal(true);
    try {
      const activeStage = newDealStage || (stages[0]?.id || "lead");
      await fetchClient("/crm/leads", {
        method: "POST",
        body: JSON.stringify({
          title: newDealTitle,
          client_id: newDealContactId,
          estimated_value: parseFloat(newDealValue || "0"),
          stage: activeStage,
          probability: parseInt(newDealProbability || "50"),
          closeDate: newDealCloseDate || undefined,
        }),
      });
      toast.success("Deal successfully created!");
      setNewDealTitle("");
      setNewDealValue("");
      setNewDealProbability("50");
      setNewDealCloseDate("");
      onCloseAdd();
      onDealAdded();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Error creating deal");
    } finally {
      setIsCreatingDeal(false);
    }
  };

  // Update Deal details from Details panel
  const handleUpdateDealDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDealId) return;
    setIsUpdatingDeal(true);
    try {
      await fetchClient(`/crm/leads/${selectedDealId}`, {
        method: "PATCH",
        body: JSON.stringify({
          estimated_value: parseFloat(editDealValue || "0"),
          stage: editDealStage,
          probability: parseInt(editDealProbability || "50"),
          closeDate: editDealCloseDate || null,
        }),
      });
      toast.success("Deal updated successfully.");
      fetchDealDetails(selectedDealId);
      fetchPipelineAndDeals(); // reload Kanban board
    } catch (err) {
      console.error(err);
      toast.error("Failed to update deal.");
    } finally {
      setIsUpdatingDeal(false);
    }
  };

  // Add Deal Timeline Activity
  const handleAddDealActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDealId || !newActivityTitle.trim()) return;
    setIsSubmittingActivity(true);
    try {
      await fetchClient(`/crm/leads/${selectedDealId}`, {
        method: "POST",
        body: JSON.stringify({
          type: newActivityType,
          title: newActivityTitle,
          content: newActivityContent,
        }),
      });
      toast.success("Deal activity logged.");
      setNewActivityTitle("");
      setNewActivityContent("");
      fetchDealDetails(selectedDealId); // reload timeline
    } catch (err) {
      console.error(err);
      toast.error("Failed to log activity.");
    } finally {
      setIsSubmittingActivity(false);
    }
  };

  // Delete Deal Action
  const handleDeleteDeal = async (id: string) => {
    if (!confirm("Are you sure you want to delete this deal? All related deal activity logs will be permanently deleted.")) return;
    try {
      await fetchClient(`/crm/leads/${id}`, { method: "DELETE" });
      toast.success("Deal deleted.");
      setSelectedDealId(null);
      fetchPipelineAndDeals();
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete deal.");
    }
  };

  // Render Helpers
  const getDealsInStage = (stageId: string) => {
    return deals.filter(d => d.stage === stageId);
  };

  const getStageTotalValue = (stageId: string) => {
    const stageDeals = getDealsInStage(stageId);
    const sum = stageDeals.reduce((acc, d) => acc + d.value, 0);
    return sum.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  };

  const getProbabilityBadgeColor = (prob: number) => {
    if (prob >= 80) return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    if (prob >= 40) return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
  };

  return (
    <div className="relative">
      <div className={`grid grid-cols-1 gap-6 transition-all duration-300 ${selectedDealId ? "lg:grid-cols-4" : "grid-cols-1"}`}>
        
        {/* Kanban Columns Grid wrapper */}
        <div className={`flex gap-4 overflow-x-auto pb-4 custom-scrollbar ${selectedDealId ? "lg:col-span-3" : ""}`} style={{ minHeight: "65vh" }}>
          {isLoading ? (
            <div className="w-full py-24 text-center text-zinc-500">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-3" />
              Loading deal flow pipeline...
            </div>
          ) : stages.length === 0 ? (
            <div className="w-full text-center py-24 text-zinc-500 space-y-2">
              <AlertCircle className="w-8 h-8 text-zinc-600 mx-auto" />
              <p>No pipeline stage definitions configured.</p>
              <p className="text-[10px]">Head over to the Pipelines settings tab to create one.</p>
            </div>
          ) : (
            stages.map((stage) => {
              const stageDeals = getDealsInStage(stage.id);

              return (
                <div 
                  key={stage.id} 
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, stage.id)}
                  className="flex-1 min-w-[280px] max-w-[320px] flex flex-col bg-zinc-950/40 border border-white/5 rounded-2xl p-4 space-y-4"
                >
                  {/* Column Header */}
                  <div className="flex flex-col gap-1 pb-2 border-b border-white/5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: stage.color }} />
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">{stage.name}</h4>
                      </div>
                      <span className="text-[10px] bg-zinc-900 border border-white/5 text-zinc-400 font-mono font-bold px-2 py-0.5 rounded-full">
                        {stageDeals.length}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                      <span>Total Value:</span>
                      <span className="text-white font-bold">$ {getStageTotalValue(stage.id)}</span>
                    </div>
                  </div>

                  {/* Deals cards List */}
                  <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[55vh] pr-1 custom-scrollbar">
                    {stageDeals.length === 0 ? (
                      <div className="flex-1 border-2 border-dashed border-white/[0.02] rounded-xl flex items-center justify-center p-8 text-center text-[10px] text-zinc-600 italic">
                        Drag deals here
                      </div>
                    ) : (
                      stageDeals.map((deal) => (
                        <div
                          key={deal.id}
                          draggable
                          onDragStart={(e) => handleDragStart(e, deal.id)}
                          onClick={() => setSelectedDealId(deal.id)}
                          className={`glass-card p-4 border border-white/5 rounded-xl cursor-grab active:cursor-grabbing hover:border-white/10 hover:bg-white/[0.01] transition-all relative group shadow-md space-y-3 ${
                            selectedDealId === deal.id ? "border-[var(--accent-primary)]/50 bg-[var(--accent-primary)]/[0.01]" : ""
                          }`}
                        >
                          <div className="space-y-1">
                            <h5 className="text-xs font-bold text-white group-hover:text-[var(--accent-primary)] transition-colors line-clamp-2">
                              {deal.title}
                            </h5>
                            
                            {deal.contact && (
                              <div className="flex items-center gap-1.5 text-[10px] text-zinc-500 font-medium">
                                <User className="w-3 h-3 text-zinc-600" />
                                <span className="truncate">
                                  {deal.contact.firstName || ""} {deal.contact.lastName || ""}
                                </span>
                              </div>
                            )}

                            {deal.contact?.company && (
                              <div className="flex items-center gap-1.5 text-[10px] text-zinc-600">
                                <Briefcase className="w-3 h-3 text-zinc-700" />
                                <span className="truncate">{deal.contact.company}</span>
                              </div>
                            )}
                          </div>

                          <div className="flex justify-between items-end border-t border-white/5 pt-2.5">
                            <div className="text-xs font-mono font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)]">
                              $ {deal.value.toLocaleString()}
                            </div>
                            <div className={`px-1.5 py-0.5 rounded font-mono text-[9px] font-bold ${getProbabilityBadgeColor(deal.probability)}`}>
                              {deal.probability}%
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Slide-over Deal Details Editor Panel */}
        {selectedDealId && (
          <div className="lg:col-span-1 glass-card border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl relative animate-slide-in bg-zinc-900/60 backdrop-blur-xl h-fit">
            <button 
              onClick={() => setSelectedDealId(null)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>

            {isDetailLoading ? (
              <div className="py-24 text-center text-zinc-500">
                <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-2" />
                Loading deal records...
              </div>
            ) : detailedDeal ? (
              <div className="space-y-6">
                
                {/* Details Header */}
                <div className="border-b border-white/5 pb-4 space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/20 flex items-center justify-center text-[var(--accent-primary)]">
                    <DollarSign className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white leading-tight">
                    {detailedDeal.title}
                  </h3>
                  
                  {detailedDeal.contact && (
                    <div className="text-xs text-zinc-400 font-light flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Linked Lead: <b>{detailedDeal.contact.firstName} {detailedDeal.contact.lastName}</b></span>
                    </div>
                  )}
                </div>

                {/* Edit Form Fields */}
                <form onSubmit={handleUpdateDealDetails} className="space-y-4 text-xs">
                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Deal Value ($)</label>
                    <input
                      type="number"
                      className="input"
                      value={editDealValue}
                      onChange={e => setEditDealValue(e.target.value)}
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Stage</label>
                      <select
                        className="input"
                        value={editDealStage}
                        onChange={e => setEditDealStage(e.target.value)}
                      >
                        {stages.map(st => (
                          <option key={st.id} value={st.id}>{st.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Probability (%)</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        className="input"
                        value={editDealProbability}
                        onChange={e => setEditDealProbability(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Expected Close Date</label>
                    <input
                      type="date"
                      className="input"
                      value={editDealCloseDate}
                      onChange={e => setEditDealCloseDate(e.target.value)}
                    />
                  </div>

                  <div className="flex gap-2">
                    <button 
                      type="submit" 
                      disabled={isUpdatingDeal}
                      className="btn-primary flex-1 py-2 text-[10px] font-bold shadow-lg shadow-[var(--accent-primary)]/10"
                    >
                      {isUpdatingDeal ? "Updating..." : "Save Edits"}
                    </button>
                    <button 
                      type="button"
                      onClick={() => handleDeleteDeal(detailedDeal.id)}
                      className="btn-ghost p-2 border border-rose-500/20 text-rose-400 hover:text-white hover:bg-rose-500/10 rounded-xl"
                      title="Delete deal"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </form>

                {/* Log Deal Activity Form */}
                <div className="border-t border-white/5 pt-4 space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Log Deal Note</h4>
                  <form onSubmit={handleAddDealActivity} className="space-y-3">
                    <div className="flex gap-2">
                      {["note", "email", "call"].map((type) => (
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
                          {type === "email" ? "✉️" : type === "call" ? "📞" : "📝"} {type}
                        </button>
                      ))}
                    </div>
                    
                    <input
                      className="input py-2 text-xs"
                      placeholder="Title (e.g. Discussed contract terms)"
                      value={newActivityTitle}
                      onChange={e => setNewActivityTitle(e.target.value)}
                      required
                    />

                    <textarea
                      className="input py-2 text-xs"
                      placeholder="Summary..."
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
                      {isSubmittingActivity ? "Logging..." : "Log Note"}
                    </button>
                  </form>
                </div>

                {/* Timeline */}
                <div className="border-t border-white/5 pt-4 space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Deal Timeline</h4>
                  <div className="relative pl-4 border-l border-white/10 space-y-4 text-xs">
                    {detailedDeal.activities && detailedDeal.activities.length > 0 ? (
                      detailedDeal.activities.map((act: any) => (
                        <div key={act.id} className="relative group">
                          {/* dot */}
                          <div className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border border-zinc-900 ${
                            act.type === "system" ? "bg-zinc-500" :
                            act.type === "email" ? "bg-blue-400" :
                            act.type === "call" ? "bg-orange-400" :
                            "bg-[var(--accent-primary)]"
                          }`} />
                          
                          <div className="space-y-0.5">
                            <div className="flex justify-between items-center text-[10px]">
                              <span className="font-semibold text-white">{act.title}</span>
                              <span className="text-[9px] text-zinc-500">{new Date(act.createdAt).toLocaleDateString()}</span>
                            </div>
                            {act.content && (
                              <p className="text-[10px] text-zinc-400 bg-black/25 p-2 rounded-lg border border-white/5 mt-1 font-light whitespace-pre-wrap">
                                {act.content}
                              </p>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-[10px] text-zinc-500 italic pl-2">No activities logged for this deal.</p>
                    )}
                  </div>
                </div>

              </div>
            ) : (
              <div className="text-center text-zinc-500 py-12">Deal not found.</div>
            )}
          </div>
        )}
      </div>

      {/* Add Deal Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
          onClick={e => { if (e.target === e.currentTarget) onCloseAdd(); }}>
          <div className="glass-card p-8 w-full max-w-md animate-slide-up relative bg-zinc-900/90 border border-white/5 shadow-2xl rounded-3xl">
            <button 
              onClick={onCloseAdd}
              className="absolute top-4 right-4 text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>
            
            <h2 className="text-xl font-bold text-white mb-6">Create New Deal</h2>

            {contacts.length === 0 ? (
              <div className="text-center py-6 text-xs text-zinc-400 space-y-2">
                <AlertCircle className="w-6 h-6 text-zinc-500 mx-auto" />
                <p>You need at least one Contact created in this organization before creating a deal.</p>
                <button 
                  type="button" 
                  onClick={onCloseAdd}
                  className="btn-secondary px-4 py-2 mt-2 font-bold"
                >
                  Go Back
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateDeal} className="space-y-4 text-xs">
                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Deal Title</label>
                  <input
                    className="input"
                    placeholder="e.g. Acme Corp Enterprise Subscription"
                    value={newDealTitle}
                    onChange={e => setNewDealTitle(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Associate Contact</label>
                  <select
                    className="input"
                    value={newDealContactId}
                    onChange={e => setNewDealContactId(e.target.value)}
                    required
                  >
                    {contacts.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.firstName || ""} {c.lastName || ""} {c.company ? `(${c.company})` : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Deal Value ($)</label>
                    <input
                      type="number"
                      className="input"
                      placeholder="e.g. 5000"
                      value={newDealValue}
                      onChange={e => setNewDealValue(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Pipeline Stage</label>
                    <select
                      className="input"
                      value={newDealStage}
                      onChange={e => setNewDealStage(e.target.value)}
                    >
                      {stages.map(st => (
                        <option key={st.id} value={st.id}>{st.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Win Probability (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      className="input"
                      value={newDealProbability}
                      onChange={e => setNewDealProbability(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Expected Close Date</label>
                    <input
                      type="date"
                      className="input"
                      value={newDealCloseDate}
                      onChange={e => setNewDealCloseDate(e.target.value)}
                    />
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={onCloseAdd} disabled={isCreatingDeal} className="btn-secondary flex-1 py-3 font-bold rounded-xl">
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary flex-1 py-3 font-bold rounded-xl shadow-lg shadow-[var(--accent-primary)]/10" disabled={isCreatingDeal}>
                    {isCreatingDeal ? "Creating..." : "Create Deal"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
