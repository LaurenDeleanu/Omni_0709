"use client";

import React, { useState, useEffect } from "react";
import { ITAPI, UserAPI } from "@/lib/api";
import { Laptop, Ticket, Key, Database, ShieldAlert, Cpu, HardDrive, Plus, CheckCircle2, AlertTriangle, ArrowRight, FileText, Edit, Trash, BookOpen, Search, Lightbulb, ChevronDown, ChevronUp, Sparkles, RefreshCw, TrendingUp } from "lucide-react";
import { useUser } from "@/hooks/use-user";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { ITKBBrowser } from "@/components/it/ITKBBrowser";
import { ITSLADashboard } from "@/components/it/ITSLADashboard";

export default function ITDashboard() {
  const [activeTab, setActiveTab] = useState<"assets" | "tickets" | "licenses" | "requisitions" | "kb" | "sla">("tickets");
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "super_admin";

  const [assets, setAssets] = useState<any[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);
  const [licenses, setLicenses] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [requisitions, setRequisitions] = useState<any[]>([]);

  const [kbArticles, setKbArticles] = useState<any[]>([]);
  const [kbTotalArticles, setKbTotalArticles] = useState(0);
  const [kbPage, setKbPage] = useState(1);
  const [kbSearchQuery, setKbSearchQuery] = useState("");
  const [kbSearchResults, setKbSearchResults] = useState<any[] | null>(null);
  const [kbSearching, setKbSearching] = useState(false);
  const [kbRecurringIssues, setKbRecurringIssues] = useState<any[]>([]);
  const [kbPreventiveActions, setKbPreventiveActions] = useState<any | null>(null);
  const [kbLoadingRecurring, setKbLoadingRecurring] = useState(false);
  const [kbLoadingPreventive, setKbLoadingPreventive] = useState(false);
  const [kbIndexing, setKbIndexing] = useState(false);
  const [kbIndexResult, setKbIndexResult] = useState<any>(null);
  const [kbExpandedArticles, setKbExpandedArticles] = useState<Set<string>>(new Set());
  
  const [slaSummary, setSlaSummary] = useState<any>(null);
  const [slaLoading, setSlaLoading] = useState(false);
  
  // SUPPORT TICKET FORM STATES
  const [showNewTicket, setShowNewTicket] = useState(false);
  const [newTicketTitle, setNewTicketTitle] = useState("");
  const [newTicketDesc, setNewTicketDesc] = useState("");
  const [newTicketPriority, setNewTicketPriority] = useState("medium");
  const [newTicketCategory, setNewTicketCategory] = useState("hardware");
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);
  
  // REQUISITION FORM STATES
  const [showNewRequisition, setShowNewRequisition] = useState(false);
  const [newReqType, setNewReqType] = useState("hardware");
  const [newReqName, setNewReqName] = useState("");
  const [newReqReason, setNewReqReason] = useState("");
  const [isSubmittingRequisition, setIsSubmittingRequisition] = useState(false);

  // DIRECT HARDWARE ASSETS CRUD STATES
  const [showNewAsset, setShowNewAsset] = useState(false);
  const [newAssetName, setNewAssetName] = useState("");
  const [newAssetSerial, setNewAssetSerial] = useState("");
  const [newAssetCategory, setNewAssetCategory] = useState("laptop");
  const [newAssetStatus, setNewAssetStatus] = useState("available");
  const [newAssetCost, setNewAssetCost] = useState("");
  const [newAssetAssigned, setNewAssetAssigned] = useState("");
  const [isSubmittingAsset, setIsSubmittingAsset] = useState(false);

  const [showEditAsset, setShowEditAsset] = useState(false);
  const [selectedAssetForEdit, setSelectedAssetForEdit] = useState<any>(null);
  const [editAssetName, setEditAssetName] = useState("");
  const [editAssetSerial, setEditAssetSerial] = useState("");
  const [editAssetCategory, setEditAssetCategory] = useState("laptop");
  const [editAssetStatus, setEditAssetStatus] = useState("available");
  const [editAssetCost, setEditAssetCost] = useState("");
  const [editAssetAssigned, setEditAssetAssigned] = useState("");
  const [isUpdatingAsset, setIsUpdatingAsset] = useState(false);

  // DIRECT SOFTWARE LICENSES CRUD STATES
  const [showNewLicense, setShowNewLicense] = useState(false);
  const [newLicSoftware, setNewLicSoftware] = useState("");
  const [newLicCost, setNewLicCost] = useState("");
  const [newLicStatus, setNewLicStatus] = useState("active");
  const [newLicAssigned, setNewLicAssigned] = useState("");
  const [isSubmittingLicense, setIsSubmittingLicense] = useState(false);

  const [showEditLicense, setShowEditLicense] = useState(false);
  const [selectedLicenseForEdit, setSelectedLicenseForEdit] = useState<any>(null);
  const [editLicSoftware, setEditLicSoftware] = useState("");
  const [editLicCost, setEditLicCost] = useState("");
  const [editLicStatus, setEditLicStatus] = useState("active");
  const [editLicAssigned, setEditLicAssigned] = useState("");
  const [isUpdatingLicense, setIsUpdatingLicense] = useState(false);

  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [assetsData, ticketsData, licensesData, empData, requisitionsData, kbData] = await Promise.all([
        ITAPI.getAssets(),
        ITAPI.getTickets(),
        ITAPI.getLicenses(),
        UserAPI.getEmployees(),
        ITAPI.getRequisitions(),
        ITAPI.listKBArticles(1, 20)
      ]);
      setAssets(assetsData);
      setTickets(ticketsData);
      setLicenses(licensesData);
      setEmployees(empData);
      setRequisitions(requisitionsData);
      setKbArticles(kbData.items || []);
      setKbTotalArticles(kbData.total || 0);
    } catch (err) {
      console.error("Error cargando datos de IT:", err);
    }
  };

  // KB: load recurring issues & preventive actions on tab switch
  useEffect(() => {
    if (activeTab === "kb") {
      if (kbRecurringIssues.length === 0 && !kbLoadingRecurring) fetchKbRecurring();
      if (!kbPreventiveActions && !kbLoadingPreventive) fetchKbPreventive();
    }
    if (activeTab === "sla") {
      if (!slaSummary && !slaLoading) fetchSlaData();
    }
  }, [activeTab]);

  const fetchKbRecurring = async () => {
    setKbLoadingRecurring(true);
    try {
      const data = await ITAPI.getRecurringIssues();
      setKbRecurringIssues(data.recurring_issues || []);
    } catch (err) { console.error("Error loading recurring issues:", err); }
    finally { setKbLoadingRecurring(false); }
  };

  const fetchKbPreventive = async () => {
    setKbLoadingPreventive(true);
    try {
      const data = await ITAPI.getPreventiveActions();
      setKbPreventiveActions(data);
    } catch (err) { console.error("Error loading preventive actions:", err); }
    finally { setKbLoadingPreventive(false); }
  };

  const fetchSlaData = async () => {
    setSlaLoading(true);
    try {
      const data = await ITAPI.getSlaSummary();
      setSlaSummary(data);
    } catch (err) { console.error("Error loading SLA data:", err); }
    finally { setSlaLoading(false); }
  };

  const handleKbSearch = async () => {
    if (!kbSearchQuery.trim()) return;
    setKbSearching(true);
    setKbSearchResults(null);
    try {
      const data = await ITAPI.searchKB(kbSearchQuery, 10);
      setKbSearchResults(data.results || []);
    } catch (err) { console.error("Error searching KB:", err); }
    finally { setKbSearching(false); }
  };

  const handleKbPageChange = async (page: number) => {
    setKbPage(page);
    try {
      const data = await ITAPI.listKBArticles(page, 20);
      setKbArticles(data.items || []);
      setKbTotalArticles(data.total || 0);
    } catch (err) { console.error("Error loading KB articles:", err); }
  };

  const handleIndexTickets = async () => {
    setKbIndexing(true);
    setKbIndexResult(null);
    try {
      const data = await ITAPI.indexKBTickets();
      setKbIndexResult(data);
    } catch (err) { console.error("Error indexing tickets:", err); }
    finally { setKbIndexing(false); }
  };

  const toggleKbArticleExpand = (id: string) => {
    setKbExpandedArticles(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const getAssigneeName = (userId: string) => {
    const emp = employees.find(e => e.id === userId);
    return emp ? emp.full_name : "Sin asignar";
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicketTitle || !newTicketDesc) return;
    
    setIsSubmittingTicket(true);
    try {
      const adminUser = employees.find(e => e.email === "lauren.deleanu@gmail.com") || employees[0];
      await ITAPI.createTicket({
        title: newTicketTitle,
        description: newTicketDesc,
        category: newTicketCategory,
        priority: newTicketPriority,
        requester_id: adminUser?.id || "temp-user"
      });
      setNewTicketTitle("");
      setNewTicketDesc("");
      setShowNewTicket(false);
      fetchData();
    } catch (err) {
      console.error("Error al crear ticket:", err);
    } finally {
      setIsSubmittingTicket(false);
    }
  };

  const handleCreateRequisition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReqName) return;
    
    setIsSubmittingRequisition(true);
    try {
      await ITAPI.createRequisition({
        item_type: newReqType,
        item_name: newReqName,
        reason: newReqReason
      });
      setNewReqName("");
      setNewReqReason("");
      setShowNewRequisition(false);
      fetchData();
    } catch (err) {
      console.error("Error al crear solicitud de IT:", err);
    } finally {
      setIsSubmittingRequisition(false);
    }
  };

  const handleReviewRequisition = async (id: string, approve: boolean) => {
    try {
      await ITAPI.updateRequisitionStatus(id, approve ? "approved" : "rejected");
      fetchData();
    } catch (err) {
      console.error("Error al actualizar estado de solicitud de IT:", err);
    }
  };

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAssetName || !newAssetSerial) return;
    setIsSubmittingAsset(true);
    try {
      await ITAPI.createAsset({
        name: newAssetName,
        serial_number: newAssetSerial,
        category: newAssetCategory,
        status: newAssetStatus,
        cost: parseFloat(newAssetCost) || 0.0,
        assigned_to_id: newAssetAssigned || null
      });
      setNewAssetName("");
      setNewAssetSerial("");
      setNewAssetCost("");
      setNewAssetAssigned("");
      setShowNewAsset(false);
      fetchData();
    } catch (err) {
      console.error("Error al crear activo:", err);
    } finally {
      setIsSubmittingAsset(false);
    }
  };

  const handleUpdateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssetForEdit) return;
    setIsUpdatingAsset(true);
    try {
      await ITAPI.updateAsset(selectedAssetForEdit.id, {
        name: editAssetName,
        serial_number: editAssetSerial,
        category: editAssetCategory,
        status: editAssetStatus,
        cost: parseFloat(editAssetCost) || 0.0,
        assigned_to_id: editAssetAssigned || null
      });
      setShowEditAsset(false);
      setSelectedAssetForEdit(null);
      fetchData();
    } catch (err) {
      console.error("Error al actualizar activo:", err);
    } finally {
      setIsUpdatingAsset(false);
    }
  };

  const handleCreateLicense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLicSoftware) return;
    setIsSubmittingLicense(true);
    try {
      await ITAPI.createLicense({
        software_name: newLicSoftware,
        seat_cost: parseFloat(newLicCost) || 0.0,
        status: newLicStatus,
        assigned_to_id: newLicAssigned || null,
        renewal_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] // 1 year renewal by default
      });
      setNewLicSoftware("");
      setNewLicCost("");
      setNewLicAssigned("");
      setShowNewLicense(false);
      fetchData();
    } catch (err) {
      console.error("Error al crear licencia:", err);
    } finally {
      setIsSubmittingLicense(false);
    }
  };

  const handleUpdateLicense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLicenseForEdit) return;
    setIsUpdatingLicense(true);
    try {
      await ITAPI.updateLicense(selectedLicenseForEdit.id, {
        software_name: editLicSoftware,
        seat_cost: parseFloat(editLicCost) || 0.0,
        status: editLicStatus,
        assigned_to_id: editLicAssigned || null
      });
      setShowEditLicense(false);
      setSelectedLicenseForEdit(null);
      fetchData();
    } catch (err) {
      console.error("Error al actualizar licencia:", err);
    } finally {
      setIsUpdatingLicense(false);
    }
  };

  const copyODataLink = () => {
    const link = `${window.location.origin.replace("3000", "8000")}/api/v1/it/analytics/odata`;
    navigator.clipboard.writeText(link);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <InlineCopilot
        moduleContext="IT"
        placeholder="Ask about IT assets, tickets, or licenses..."
        quickActions={[
          { label: "Summarize open tickets", message: "Summarize open tickets" },
          { label: "Check asset inventory", message: "Check asset inventory" },
          { label: "Show license costs", message: "Show license costs" },
        ]}
      />
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-cyan-950/20 to-slate-900/50 p-6 rounded-2xl border border-cyan-500/10 backdrop-blur-md">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent flex items-center gap-3">
            <Laptop className="w-8 h-8 text-cyan-400" />
            SuccessCore IT Management
          </h1>
          <p className="text-muted-foreground mt-2 max-w-xl">
            Gestiona el aprovisionamiento de hardware, licencias de software y atiende tickets de soporte de forma centralizada.
          </p>
        </div>
        
        {/* OData Power BI Connector Card */}
        <div className="bg-card border border-cyan-500/20 rounded-xl p-4 flex items-center gap-4 max-w-sm">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center border border-cyan-400/20">
            <Database className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wide">Conector de Datos</span>
            <h4 className="text-sm font-medium text-foreground truncate mt-0.5">Power BI / Tableau Feed</h4>
            <button 
              onClick={copyODataLink}
              className="text-xs text-muted-foreground hover:text-cyan-300 underline cursor-pointer mt-1 block text-left"
            >
              {copiedLink ? "¡Enlace Copiado!" : "Copiar URL del Feed OData"}
            </button>
          </div>
        </div>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-bl-full group-hover:bg-cyan-500/10 transition-all duration-300"></div>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-cyan-500/10 border border-cyan-400/20 rounded-xl text-cyan-400"><Cpu className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Activos de IT</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">{assets.length}</h2>
            </div>
          </div>
        </div>

        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-bl-full group-hover:bg-amber-500/10 transition-all duration-300"></div>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-amber-500/10 border border-amber-400/20 rounded-xl text-amber-400"><Ticket className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Soporte Pendiente</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">{tickets.filter(t => t.status === "open").length}</h2>
            </div>
          </div>
        </div>

        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-bl-full group-hover:bg-indigo-500/10 transition-all duration-300"></div>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-indigo-500/10 border border-indigo-400/20 rounded-xl text-indigo-400"><Key className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">SaaS Licenciados</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">{licenses.length}</h2>
            </div>
          </div>
        </div>

        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-bl-full group-hover:bg-emerald-500/10 transition-all duration-300"></div>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><ShieldAlert className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Coste Estimado Mensual</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">
                {licenses.reduce((acc, l) => acc + (l.seat_cost || 0), 0).toFixed(2)} €
              </h2>
            </div>
          </div>
        </div>
      </div>

      {/* NAVIGATION TABS */}
      <div className="border-b border-border/40 flex items-center justify-between pb-1">
        <div className="flex gap-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab("tickets")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "tickets"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Mesa de Ayuda (Tickets)
          </button>
          <button
            onClick={() => setActiveTab("assets")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "assets"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Inventario de Hardware
          </button>
          <button
            onClick={() => setActiveTab("licenses")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "licenses"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Licencias de Software
          </button>
          <button
            onClick={() => setActiveTab("requisitions")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "requisitions"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Solicitudes de Aprovisionamiento
          </button>
          <button
            onClick={() => setActiveTab("kb")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "kb"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Base de Conocimiento (KB)
          </button>
          <button
            onClick={() => setActiveTab("sla")}
            className={`pb-3 font-semibold text-sm transition-all border-b-2 cursor-pointer whitespace-nowrap ${
              activeTab === "sla"
                ? "border-cyan-500 text-cyan-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            SLA Dashboards
          </button>
        </div>

        {activeTab === "tickets" && (
          <button
            onClick={() => setShowNewTicket(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-cyan-400/20 shadow-lg shadow-cyan-950/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Nuevo Ticket
          </button>
        )}

        {activeTab === "assets" && isAdmin && (
          <button
            onClick={() => setShowNewAsset(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-cyan-400/20 shadow-lg shadow-cyan-950/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Nuevo Activo
          </button>
        )}

        {activeTab === "licenses" && isAdmin && (
          <button
            onClick={() => setShowNewLicense(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-cyan-400/20 shadow-lg shadow-cyan-950/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Nueva Licencia
          </button>
        )}

        {activeTab === "requisitions" && (
          <button
            onClick={() => setShowNewRequisition(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-cyan-400/20 shadow-lg shadow-cyan-950/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Nueva Solicitud
          </button>
        )}

        {activeTab === "kb" && isAdmin && (
          <button
            onClick={handleIndexTickets}
            disabled={kbIndexing}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted disabled:to-muted text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-cyan-400/20 shadow-lg shadow-cyan-950/20"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {kbIndexing ? "Indexando..." : "Generar desde Tickets Resueltos"}
          </button>
        )}
      </div>

      {/* TAB CONTENT: TICKETS */}
      {activeTab === "tickets" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* TICKETS LIST */}
          <div className="lg:col-span-2 space-y-4">
            {tickets.length === 0 ? (
              <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
                <Ticket className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-foreground">No hay tickets de soporte</h4>
                <p className="text-muted-foreground text-sm mt-1">Crea un nuevo ticket para reportar incidencias de IT.</p>
              </div>
            ) : (
              tickets.map((t) => (
                <div 
                  key={t.id} 
                  className="bg-card/30 border border-border/40 hover:border-cyan-500/20 rounded-xl p-6 transition-all duration-200 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        t.priority === "critical" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                        t.priority === "high" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                        "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      }`}>
                        {t.priority}
                      </span>
                      <span className="text-xs text-muted-foreground uppercase">{t.category}</span>
                    </div>
                    <h3 className="text-base font-bold text-foreground truncate">{t.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">{t.description}</p>
                    <div className="text-xs text-muted-foreground/60 flex items-center gap-2 mt-2">
                      <span>Solicitado por: <strong>{getAssigneeName(t.requester_id)}</strong></span>
                      <span>•</span>
                      <span>Asignado a: <strong>{getAssigneeName(t.assignee_id)}</strong></span>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between md:justify-end gap-4 min-w-[120px] border-t md:border-t-0 border-border/20 pt-4 md:pt-0">
                    <span className={`flex items-center gap-1.5 text-xs font-semibold ${
                      t.status === "open" ? "text-amber-400" : "text-emerald-400"
                    }`}>
                      {t.status === "open" ? (
                        <>
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Pendiente
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Resuelto
                        </>
                      )}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* SIDE INFO BOX */}
          <div className="bg-gradient-to-b from-card/30 to-card/10 border border-border/40 rounded-2xl p-6 h-fit space-y-6">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2 border-b border-border/30 pb-3">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
              SLA & Acuerdos de IT
            </h3>
            
            <div className="space-y-4">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">Tiempo de Respuesta</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">Crítico: &lt; 2h | Alto: &lt; 6h | Medio: &lt; 24h</p>
                </div>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold">100% SLA</span>
              </div>
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">Provisionamiento SaaS</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">Cuentas activas en la incorporación del empleado de forma automática.</p>
                </div>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold">Automático</span>
              </div>
            </div>
            
            <div className="bg-cyan-500/5 rounded-xl p-4 border border-cyan-500/10 text-xs text-cyan-300 leading-relaxed flex gap-3">
              <AlertTriangle className="w-5 h-5 text-cyan-400 shrink-0" />
              <span>Para incidencias físicas críticas (ej: portátil robado, pantalla dañada), por favor ponte en contacto directo con soporte al teléfono de emergencia.</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: HARDWARE ASSETS */}
      {activeTab === "assets" && (
        <div className="bg-card/25 border border-border/40 rounded-xl overflow-hidden animate-in fade-in duration-300">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border/40 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="px-6 py-4">Activo/Nombre</th>
                  <th className="px-6 py-4">Nº Serie</th>
                  <th className="px-6 py-4">Categoría</th>
                  <th className="px-6 py-4">Estado</th>
                  <th className="px-6 py-4">Asignado A</th>
                  <th className="px-6 py-4 text-right">Coste Compra</th>
                  {isAdmin && <th className="px-6 py-4 text-right">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20 text-sm">
                {assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-6 py-4 font-semibold text-foreground flex items-center gap-3">
                      <Laptop className="w-4 h-4 text-cyan-400" />
                      {asset.name}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{asset.serial_number}</td>
                    <td className="px-6 py-4 text-muted-foreground capitalize">{asset.category}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        asset.status === "assigned" ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" :
                        asset.status === "repair" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                        "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      }`}>
                        {asset.status === "assigned" ? "Asignado" : asset.status === "repair" ? "Taller" : "Disponible"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">{getAssigneeName(asset.assigned_to_id)}</td>
                    <td className="px-6 py-4 text-right font-semibold text-foreground">
                      {asset.cost ? `${parseFloat(asset.cost).toFixed(2)} €` : "—"}
                    </td>
                    {isAdmin && (
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => {
                              setSelectedAssetForEdit(asset);
                              setEditAssetName(asset.name);
                              setEditAssetSerial(asset.serial_number);
                              setEditAssetCategory(asset.category || "laptop");
                              setEditAssetStatus(asset.status || "available");
                              setEditAssetCost(asset.cost ? asset.cost.toString() : "");
                              setEditAssetAssigned(asset.assigned_to_id || "");
                              setShowEditAsset(true);
                            }}
                            className="px-2 py-1 border border-cyan-500/30 bg-cyan-500/5 hover:bg-cyan-500/10 text-cyan-400 text-xs font-semibold rounded cursor-pointer"
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => {
                              if (confirm("¿Estás seguro de que deseas eliminar este activo de hardware?")) {
                                ITAPI.deleteAsset(asset.id).then(() => fetchData());
                              }
                            }}
                            className="px-2 py-1 border border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-semibold rounded cursor-pointer"
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: SAAS LICENSES */}
      {activeTab === "licenses" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-300">
          {licenses.map((lic) => (
            <div key={lic.id} className="bg-card/25 border border-border/40 rounded-xl p-6 flex items-start gap-4 hover:border-cyan-500/20 transition-all duration-200">
              <div className="p-3 bg-indigo-500/10 border border-indigo-400/20 text-indigo-400 rounded-xl">
                <Key className="w-6 h-6" />
              </div>
              
              <div className="flex-1 space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <h4 className="text-base font-bold text-foreground">{lic.software_name}</h4>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold uppercase">
                      {lic.status}
                    </span>
                    {isAdmin && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => {
                            setSelectedLicenseForEdit(lic);
                            setEditLicSoftware(lic.software_name);
                            setEditLicCost(lic.seat_cost ? lic.seat_cost.toString() : "");
                            setEditLicStatus(lic.status || "active");
                            setEditLicAssigned(lic.assigned_to_id || "");
                            setShowEditLicense(true);
                          }}
                          className="p-1 hover:bg-muted rounded text-cyan-400 transition-colors"
                          title="Editar"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm("¿Estás seguro de que deseas eliminar esta licencia SaaS?")) {
                              ITAPI.deleteLicense(lic.id).then(() => fetchData());
                            }
                          }}
                          className="p-1 hover:bg-muted rounded text-red-400 transition-colors"
                          title="Eliminar"
                        >
                          <Trash className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div className="flex justify-between">
                    <span>Precio por usuario/mes:</span>
                    <span className="font-semibold text-foreground">{parseFloat(lic.seat_cost).toFixed(2)} €</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Asignado a:</span>
                    <span className="font-semibold text-foreground">{getAssigneeName(lic.assigned_to_id)}</span>
                  </div>
                  {lic.renewal_date && (
                    <div className="flex justify-between border-t border-border/10 pt-1 mt-1">
                      <span>Próxima Renovación:</span>
                      <span className="font-semibold text-foreground">{lic.renewal_date}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB CONTENT: IT REQUISITIONS */}
      {activeTab === "requisitions" && (
        <div className="bg-card/25 border border-border/40 rounded-xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border/40 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="px-6 py-4">Ítem / Recurso</th>
                  <th className="px-6 py-4">Tipo</th>
                  <th className="px-6 py-4">Motivo / Razón</th>
                  <th className="px-6 py-4">Solicitante</th>
                  <th className="px-6 py-4">Fecha</th>
                  <th className="px-6 py-4">Estado</th>
                  {isAdmin && <th className="px-6 py-4 text-right">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20 text-sm">
                {requisitions.length === 0 ? (
                  <tr>
                    <td colSpan={isAdmin ? 7 : 6} className="px-6 py-12 text-center text-muted-foreground">
                      No hay solicitudes de aprovisionamiento registradas.
                    </td>
                  </tr>
                ) : (
                  requisitions.map((req) => (
                    <tr key={req.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-6 py-4 font-semibold text-foreground flex items-center gap-3">
                        <FileText className="w-4 h-4 text-cyan-400" />
                        {req.item_name}
                      </td>
                      <td className="px-6 py-4 capitalize text-muted-foreground">{req.item_type}</td>
                      <td className="px-6 py-4 text-muted-foreground max-w-xs truncate" title={req.reason}>
                        {req.reason || "Sin especificar"}
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">{getAssigneeName(req.user_id)}</td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {new Date(req.created_at).toLocaleDateString("es-ES")}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          req.status === "approved" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                          req.status === "rejected" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                          "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {req.status === "approved" ? "Aprobado" : req.status === "rejected" ? "Rechazado" : "Pendiente"}
                        </span>
                      </td>
                      {isAdmin && (
                        <td className="px-6 py-4 text-right">
                          {req.status === "pending" && (
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => handleReviewRequisition(req.id, false)}
                                className="px-2.5 py-1 border border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-semibold rounded cursor-pointer"
                              >
                                Rechazar
                              </button>
                              <button
                                onClick={() => handleReviewRequisition(req.id, true)}
                                className="px-2.5 py-1 border border-cyan-500/30 bg-cyan-500/5 hover:bg-cyan-500/10 text-cyan-400 text-xs font-semibold rounded cursor-pointer"
                              >
                                Aprobar
                              </button>
                            </div>
                          )}
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: KNOWLEDGE BASE */}
      {activeTab === "kb" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Index Result Banner */}
          {kbIndexResult && (
            <div className={`p-4 rounded-xl border text-sm flex items-center gap-3 ${
              kbIndexResult.status === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                : "bg-red-500/10 border-red-500/20 text-red-300"
            }`}>
              <Sparkles className="w-4 h-4 shrink-0" />
              <span>
                {kbIndexResult.status === "success"
                  ? `${kbIndexResult.indexed_count} de ${kbIndexResult.total_resolved} tickets resueltos indexados en la base de conocimiento.`
                  : `Error: ${kbIndexResult.message}`}
              </span>
              <button onClick={() => setKbIndexResult(null)} className="ml-auto text-xs underline hover:opacity-70">Cerrar</button>
            </div>
          )}

          {/* SEARCH BAR */}
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Buscar en la base de conocimiento... (ej: 'VPN no conecta', 'pantalla azul')"
                value={kbSearchQuery}
                onChange={(e) => setKbSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleKbSearch()}
                className="w-full bg-muted/50 border border-input rounded-lg pl-10 pr-4 py-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <button
              onClick={handleKbSearch}
              disabled={kbSearching || !kbSearchQuery.trim()}
              className="px-6 py-3 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted disabled:to-muted text-white rounded-lg text-sm font-semibold cursor-pointer transition-all border border-cyan-400/20"
            >
              {kbSearching ? "Buscando..." : "Buscar"}
            </button>
          </div>

          {/* SEARCH RESULTS */}
          {kbSearchResults !== null && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Search className="w-4 h-4 text-cyan-400" />
                Resultados de búsqueda ({kbSearchResults.length})
              </h3>
              {kbSearchResults.length === 0 ? (
                <div className="bg-card/20 rounded-xl border border-border/30 p-8 text-center">
                  <BookOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">No se encontraron artículos para "{kbSearchQuery}"</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {kbSearchResults.map((result: any, idx: number) => (
                    <div key={idx} className="bg-card/25 border border-border/40 hover:border-cyan-500/20 rounded-xl p-5 transition-all duration-200">
                      <p className="text-sm text-foreground leading-relaxed line-clamp-4 whitespace-pre-wrap">{result.content || result.text || JSON.stringify(result)}</p>
                      {result.similarity !== undefined && (
                        <div className="mt-2 flex items-center gap-2">
                          <div className="h-1.5 flex-1 bg-muted/40 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full" style={{ width: `${Math.round((result.similarity || 0) * 100)}%` }} />
                          </div>
                          <span className="text-[10px] font-semibold text-cyan-400">{Math.round((result.similarity || 0) * 100)}%</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* RECURRING ISSUES & PREVENTIVE ACTIONS ROW */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* RECURRING ISSUES CARD */}
            <div className="bg-card/25 border border-border/40 rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Problemas Recurrentes
              </h3>
              {kbLoadingRecurring ? (
                <p className="text-sm text-muted-foreground">Analizando tickets...</p>
              ) : kbRecurringIssues.length === 0 ? (
                <p className="text-sm text-muted-foreground">No se detectaron problemas recurrentes en los últimos 30 días.</p>
              ) : (
                <div className="space-y-3">
                  {kbRecurringIssues.map((issue: any, idx: number) => (
                    <div key={idx} className="bg-card/30 border border-border/20 rounded-lg p-4 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-foreground">{issue.description}</p>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                          issue.severity === "critical" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                          issue.severity === "high" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                          "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                        }`}>{issue.severity}</span>
                      </div>
                      <div className="text-xs text-muted-foreground space-y-1">
                        <p><strong className="text-foreground/70">{issue.ticket_count}</strong> tickets detectados</p>
                        {issue.root_cause_hypothesis && <p>Raíz: {issue.root_cause_hypothesis}</p>}
                        {issue.recommended_permanent_fix && (
                          <p className="text-emerald-300/80 flex items-center gap-1">
                            <Lightbulb className="w-3 h-3" />
                            {issue.recommended_permanent_fix}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* PREVENTIVE ACTIONS CARD */}
            <div className="bg-card/25 border border-border/40 rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-emerald-400" />
                Acciones Preventivas
              </h3>
              {kbLoadingPreventive ? (
                <p className="text-sm text-muted-foreground">Generando recomendaciones...</p>
              ) : !kbPreventiveActions || !kbPreventiveActions.ranked_actions || kbPreventiveActions.ranked_actions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay acciones preventivas disponibles.</p>
              ) : (
                <div className="space-y-3">
                  {kbPreventiveActions.ranked_actions.map((action: any, idx: number) => (
                    <div key={idx} className="bg-card/30 border border-border/20 rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-3">
                        <span className="text-xs font-bold text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                          {action.rank || idx + 1}
                        </span>
                        <div className="space-y-1.5 flex-1">
                          <p className="text-sm font-semibold text-foreground">{action.action}</p>
                          <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-wider">
                            <span className={`px-1.5 py-0.5 rounded ${
                              action.estimated_roi === "high" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                              action.estimated_roi === "medium" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                              "bg-muted text-muted-foreground border border-border/20"
                            }`}>ROI: {action.estimated_roi}</span>
                            <span className={`px-1.5 py-0.5 rounded ${
                              action.effort === "low" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                              action.effort === "medium" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                              "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}>Esfuerzo: {action.effort}</span>
                            {action.category && <span className="text-muted-foreground">{action.category}</span>}
                          </div>
                          {action.impact && <p className="text-xs text-muted-foreground">{action.impact}</p>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* PAGINATED ARTICLE LIST */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-cyan-400" />
                Artículos de Conocimiento
                <span className="text-xs text-muted-foreground font-normal ml-1">({kbTotalArticles} total)</span>
              </h3>
              <button
                onClick={() => handleKbPageChange(1)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-cyan-400 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Actualizar
              </button>
            </div>

            {kbArticles.length === 0 ? (
              <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
                <BookOpen className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-foreground">No hay artículos en la base de conocimiento</h4>
                <p className="text-muted-foreground text-sm mt-1">Indexa tickets resueltos para generar artículos automáticamente.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {kbArticles.map((article: any) => {
                  const isExpanded = kbExpandedArticles.has(article.id);
                  const steps = Array.isArray(article.resolution_steps) ? article.resolution_steps : [];
                  const symptoms = Array.isArray(article.symptoms) ? article.symptoms : [];
                  return (
                    <div key={article.id} className="bg-card/25 border border-border/40 hover:border-cyan-500/20 rounded-xl p-5 transition-all duration-200 flex flex-col">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h4 className="text-sm font-bold text-foreground leading-snug">{article.title}</h4>
                        {article.category && (
                          <span className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded text-[10px] font-bold uppercase shrink-0">
                            {article.category}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{article.problem_description}</p>

                      {symptoms.length > 0 && (
                        <div className="mb-3">
                          <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Síntomas</span>
                          <ul className="mt-1 space-y-0.5">
                            {symptoms.slice(0, isExpanded ? undefined : 3).map((s: string, i: number) => (
                              <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                                <span className="text-cyan-400 mt-0.5 shrink-0">•</span>
                                {s}
                              </li>
                            ))}
                            {!isExpanded && symptoms.length > 3 && (
                              <li className="text-xs text-cyan-400/60">+{symptoms.length - 3} más...</li>
                            )}
                          </ul>
                        </div>
                      )}

                      {steps.length > 0 && (
                        <div className="mb-3">
                          <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Resolución</span>
                          <ol className="mt-1 space-y-0.5 list-decimal list-inside">
                            {steps.slice(0, isExpanded ? undefined : 2).map((s: string, i: number) => (
                              <li key={i} className="text-xs text-muted-foreground">{s}</li>
                            ))}
                            {!isExpanded && steps.length > 2 && (
                              <li className="text-xs text-cyan-400/60">+{steps.length - 2} pasos más...</li>
                            )}
                          </ol>
                        </div>
                      )}

                      {isExpanded && article.root_cause && (
                        <div className="mb-3 p-2 bg-amber-500/5 border border-amber-500/10 rounded-lg">
                          <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">Causa Raíz</span>
                          <p className="text-xs text-muted-foreground mt-0.5">{article.root_cause}</p>
                        </div>
                      )}

                      {isExpanded && Array.isArray(article.prevention_tips) && article.prevention_tips.length > 0 && (
                        <div className="mb-3 p-2 bg-emerald-500/5 border border-emerald-500/10 rounded-lg">
                          <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Prevención</span>
                          <ul className="mt-0.5 space-y-0.5">
                            {article.prevention_tips.map((tip: string, i: number) => (
                              <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                                <Lightbulb className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                                {tip}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {isExpanded && article.source_ticket_id && (
                        <p className="text-[10px] text-muted-foreground/50 mb-2">
                          Origen: Ticket {article.source_ticket_id} {article.author ? `— ${article.author}` : ""}
                        </p>
                      )}

                      <div className="mt-auto pt-3 border-t border-border/20 flex items-center justify-between">
                        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                          <span>{article.view_count || 0} vistas</span>
                          {article.created_at && (
                            <span>{new Date(article.created_at).toLocaleDateString("es-ES")}</span>
                          )}
                        </div>
                        <button
                          onClick={() => toggleKbArticleExpand(article.id)}
                          className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-semibold"
                        >
                          {isExpanded ? (
                            <>Colapsar <ChevronUp className="w-3.5 h-3.5" /></>
                          ) : (
                            <>Expandir <ChevronDown className="w-3.5 h-3.5" /></>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* PAGINATION */}
            {kbTotalArticles > 20 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  onClick={() => handleKbPageChange(kbPage - 1)}
                  disabled={kbPage <= 1}
                  className="px-3 py-1.5 border border-border/40 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:border-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  Anterior
                </button>
                <span className="text-xs text-muted-foreground">
                  Página {kbPage} de {Math.ceil(kbTotalArticles / 20)}
                </span>
                <button
                  onClick={() => handleKbPageChange(kbPage + 1)}
                  disabled={kbPage >= Math.ceil(kbTotalArticles / 20)}
                  className="px-3 py-1.5 border border-border/40 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:border-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  Siguiente
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: SLA DASHBOARDS */}
      {activeTab === "sla" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {slaLoading ? (
            <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
              <Ticket className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4 animate-pulse" />
              <p className="text-muted-foreground">Cargando métricas SLA...</p>
            </div>
          ) : slaSummary ? (
            <>
              {/* KPI CARDS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-card/40 border border-border/50 rounded-xl p-5 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
                  <div className="absolute top-0 right-0 w-20 h-20 bg-cyan-500/5 rounded-bl-full group-hover:bg-cyan-500/10 transition-all duration-300"></div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Open Tickets</p>
                  <h3 className="text-3xl font-bold text-foreground mt-1">{slaSummary.total_open}</h3>
                  <span className="text-xs text-cyan-400">{slaSummary.total_resolved} resolved</span>
                </div>

                <div className="bg-card/40 border border-border/50 rounded-xl p-5 relative overflow-hidden group hover:border-cyan-500/30 transition-all duration-300">
                  <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 rounded-bl-full group-hover:bg-emerald-500/10 transition-all duration-300"></div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Avg Resolution Time</p>
                  <h3 className="text-3xl font-bold text-foreground mt-1">{slaSummary.avg_resolution_hours}h</h3>
                  <span className="text-xs text-emerald-400">mean time to resolve</span>
                </div>

                <div className={`bg-card/40 border rounded-xl p-5 relative overflow-hidden group transition-all duration-300 ${
                  slaSummary.breach_pct > 30 ? "border-red-500/30 hover:border-red-500/50" :
                  slaSummary.breach_pct > 10 ? "border-amber-500/30 hover:border-amber-500/50" :
                  "border-border/50 hover:border-emerald-500/30"
                }`}>
                  <div className={`absolute top-0 right-0 w-20 h-20 rounded-bl-full transition-all duration-300 ${
                    slaSummary.breach_pct > 30 ? "bg-red-500/5 group-hover:bg-red-500/10" :
                    slaSummary.breach_pct > 10 ? "bg-amber-500/5 group-hover:bg-amber-500/10" :
                    "bg-emerald-500/5 group-hover:bg-emerald-500/10"
                  }`}></div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">SLA Breach %</p>
                  <h3 className={`text-3xl font-bold mt-1 ${
                    slaSummary.breach_pct > 30 ? "text-red-400" :
                    slaSummary.breach_pct > 10 ? "text-amber-400" :
                    "text-emerald-400"
                  }`}>{slaSummary.breach_pct}%</h3>
                  <span className="text-xs text-muted-foreground">across open tickets</span>
                </div>

                <div className={`bg-card/40 border rounded-xl p-5 relative overflow-hidden group transition-all duration-300 ${
                  slaSummary.sla_breached > 0 ? "border-red-500/30 hover:border-red-500/50" :
                  "border-border/50 hover:border-emerald-500/30"
                }`}>
                  <div className={`absolute top-0 right-0 w-20 h-20 rounded-bl-full transition-all duration-300 ${
                    slaSummary.sla_breached > 0 ? "bg-red-500/5 group-hover:bg-red-500/10" : "bg-emerald-500/5 group-hover:bg-emerald-500/10"
                  }`}></div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Breached Count</p>
                  <h3 className={`text-3xl font-bold mt-1 ${
                    slaSummary.sla_breached > 0 ? "text-red-400" : "text-emerald-400"
                  }`}>{slaSummary.sla_breached}</h3>
                  <span className="text-xs text-muted-foreground">tickets over SLA</span>
                </div>
              </div>

              {/* CHARTS ROW */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* TICKET AGE DISTRIBUTION */}
                <div className="bg-card/25 border border-border/40 rounded-xl p-6">
                  <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-cyan-400" />
                    Ticket Age Distribution
                  </h3>
                  <div className="space-y-3">
                    {Object.entries(slaSummary.age_distribution as Record<string, number>).map(([label, count]) => {
                      const vals = Object.values(slaSummary.age_distribution as Record<string, number>);
                      const maxVal = Math.max(...vals, 1);
                      const pct = Math.round((count / maxVal) * 100);
                      const color =
                        label === "<4h" ? "bg-emerald-500" :
                        label === "4-8h" ? "bg-amber-500" :
                        label === "8-24h" ? "bg-orange-500" :
                        label === "24-72h" ? "bg-red-500" :
                        "bg-red-700";
                      return (
                        <div key={label} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground font-medium">{label}</span>
                            <span className="text-foreground font-bold">{count}</span>
                          </div>
                          <div className="w-full bg-muted/40 rounded-full h-3 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${color}`}
                              style={{ width: `${Math.max(pct, 8)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* PRIORITY DISTRIBUTION */}
                <div className="bg-card/25 border border-border/40 rounded-xl p-6">
                  <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-cyan-400" />
                    Priority Distribution
                  </h3>
                  {(() => {
                    const pri = slaSummary.priority_distribution as Record<string, number>;
                    const total = (Object.values(pri) as number[]).reduce((a, b) => a + b, 0) || 1;
                    const colors: Record<string, string> = { critical: "bg-red-500", high: "bg-amber-500", medium: "bg-cyan-500", low: "bg-emerald-500" };
                    const labels: Record<string, string> = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };
                    const entries = Object.entries(pri);
                    return (
                      <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-center">
                          <div
                            className="w-40 h-40 rounded-full relative"
                            style={{
                              background: `conic-gradient(${(() => {
                                let cumulative = 0;
                                return entries.map(([key, count]) => {
                                  const segmentPct = (count / total) * 360;
                                  const prevCumulative = cumulative;
                                  cumulative += segmentPct;
                                  const colorMap: Record<string, string> = { critical: "#ef4444", high: "#f59e0b", medium: "#06b6d4", low: "#10b981" };
                                  return `${colorMap[key] || "#06b6d4"} ${prevCumulative}deg ${cumulative}deg`;
                                }).join(", ");
                              })()})`,
                            }}
                          >
                            <div className="absolute inset-[25%] rounded-full bg-card/25 border border-border/40 flex items-center justify-center">
                              <span className="text-xs font-bold text-foreground">{total} tickets</span>
                            </div>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {entries.map(([key, count]) => (
                            <div key={key} className="flex items-center gap-2">
                              <span className={`w-3 h-3 rounded-full shrink-0 ${colors[key]}`} />
                              <span className="text-xs text-muted-foreground">{labels[key]}: <strong className="text-foreground">{count}</strong></span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* 7-DAY RESPONSE TREND */}
                <div className="bg-card/25 border border-border/40 rounded-xl p-6">
                  <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    7-Day Trend
                  </h3>
                  {(() => {
                    const days = (slaSummary.response_data || []) as Array<{ date: string; opened: number; resolved: number }>;
                    const maxVal = Math.max(...days.map((d) => Math.max(d.opened || 0, d.resolved || 0)), 1);
                    return (
                      <div className="space-y-4">
                        <div className="flex items-end gap-2 h-28 px-1">
                          {days.map((day, i: number) => (
                            <div key={i} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                              <div className="w-full flex flex-col items-center gap-0.5" style={{ height: "100%" }}>
                                <div className="w-full flex justify-center items-end gap-[2px]" style={{ height: `${Math.round((day.resolved / maxVal) * 100)}%` }}>
                                  <div
                                    className="w-[45%] bg-emerald-500/80 rounded-t-sm transition-all duration-300"
                                    style={{ height: `${Math.max(Math.round((day.resolved / maxVal) * 100), 3)}%` }}
                                    title={`Resolved: ${day.resolved}`}
                                  />
                                  <div
                                    className="w-[45%] bg-cyan-500/80 rounded-t-sm transition-all duration-300"
                                    style={{ height: `${Math.max(Math.round((day.opened / maxVal) * 100), 3)}%` }}
                                    title={`Opened: ${day.opened}`}
                                  />
                                </div>
                              </div>
                              <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                                {new Date(day.date + "T00:00:00").toLocaleDateString("es-ES", { weekday: "short" }).slice(0, 2)}
                              </span>
                            </div>
                          ))}
                        </div>
                        <div className="flex items-center justify-center gap-6 text-xs">
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-cyan-500/80 rounded-sm" /> Opened</span>
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-emerald-500/80 rounded-sm" /> Resolved</span>
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground border-t border-border/20 pt-3">
                          <span>Opened: <strong className="text-foreground">{days.reduce((a, d) => a + (d.opened || 0), 0)}</strong></span>
                          <span>Resolved: <strong className="text-foreground">{days.reduce((a, d) => a + (d.resolved || 0), 0)}</strong></span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* MODAL: NEW TICKET */}
      {showNewTicket && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Crear Incidencia de Soporte</h3>
            
            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Título</label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Teclado roto, cuenta bloqueada..."
                  value={newTicketTitle}
                  onChange={(e) => setNewTicketTitle(e.target.value)}
                  className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Descripción del problema</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Proporciona detalles sobre el error o incidencia..."
                  value={newTicketDesc}
                  onChange={(e) => setNewTicketDesc(e.target.value)}
                  className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                  <select
                    value={newTicketCategory}
                    onChange={(e) => setNewTicketCategory(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="hardware">Hardware</option>
                    <option value="software">Software</option>
                    <option value="accounts">Cuentas/Permisos</option>
                    <option value="network">Red/VPN</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Prioridad</label>
                  <select
                    value={newTicketPriority}
                    onChange={(e) => setNewTicketPriority(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="low">Baja</option>
                    <option value="medium">Media</option>
                    <option value="high">Alta</option>
                    <option value="critical">Crítica</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowNewTicket(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingTicket}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isSubmittingTicket ? "Enviando..." : "Crear Ticket"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: NEW REQUISITION */}
      {showNewRequisition && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Solicitar Recurso de IT</h3>
            
            <form onSubmit={handleCreateRequisition} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Tipo de Ítem</label>
                  <select
                    value={newReqType}
                    onChange={(e) => setNewReqType(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="hardware">Hardware (ej: Portátil, Pantalla)</option>
                    <option value="software">Software / Licencia SaaS</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Nombre del recurso</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej: MacBook Pro M3, IntelliJ IDEA..."
                    value={newReqName}
                    onChange={(e) => setNewReqName(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Motivo / Razón de la Solicitud</label>
                <textarea
                  rows={4}
                  placeholder="Explica detalladamente por qué necesitas este recurso..."
                  value={newReqReason}
                  onChange={(e) => setNewReqReason(e.target.value)}
                  className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowNewRequisition(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRequisition}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isSubmittingRequisition ? "Enviando..." : "Enviar Solicitud"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DIRECT NEW HARDWARE ASSET */}
      {showNewAsset && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Añadir Activo de Hardware</h3>
            
            <form onSubmit={handleCreateAsset} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Nombre del Activo</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej: Dell XPS 15"
                    value={newAssetName}
                    onChange={(e) => setNewAssetName(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Número de Serie</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej: SN-49DFX82"
                    value={newAssetSerial}
                    onChange={(e) => setNewAssetSerial(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                  <select
                    value={newAssetCategory}
                    onChange={(e) => setNewAssetCategory(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="laptop">Laptop</option>
                    <option value="mobile">Móvil</option>
                    <option value="tablet">Tablet</option>
                    <option value="desktop">Sobremesa</option>
                    <option value="peripheral">Periférico</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Estado</label>
                  <select
                    value={newAssetStatus}
                    onChange={(e) => setNewAssetStatus(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="available">Disponible</option>
                    <option value="assigned">Asignado</option>
                    <option value="repair">En Reparación</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Coste de Compra (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Ej: 1199.99"
                    value={newAssetCost}
                    onChange={(e) => setNewAssetCost(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Asignar A (Usuario)</label>
                  <select
                    value={newAssetAssigned}
                    onChange={(e) => setNewAssetAssigned(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="">Sin Asignar</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowNewAsset(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingAsset}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isSubmittingAsset ? "Guardando..." : "Guardar Activo"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DIRECT EDIT HARDWARE ASSET */}
      {showEditAsset && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Editar Activo de Hardware</h3>
            
            <form onSubmit={handleUpdateAsset} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Nombre del Activo</label>
                  <input
                    type="text"
                    required
                    value={editAssetName}
                    onChange={(e) => setEditAssetName(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Número de Serie</label>
                  <input
                    type="text"
                    required
                    value={editAssetSerial}
                    onChange={(e) => setEditAssetSerial(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                  <select
                    value={editAssetCategory}
                    onChange={(e) => setEditAssetCategory(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="laptop">Laptop</option>
                    <option value="mobile">Móvil</option>
                    <option value="tablet">Tablet</option>
                    <option value="desktop">Sobremesa</option>
                    <option value="peripheral">Periférico</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Estado</label>
                  <select
                    value={editAssetStatus}
                    onChange={(e) => setEditAssetStatus(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="available">Disponible</option>
                    <option value="assigned">Asignado</option>
                    <option value="repair">En Reparación</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Coste de Compra (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editAssetCost}
                    onChange={(e) => setEditAssetCost(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Asignar A (Usuario)</label>
                  <select
                    value={editAssetAssigned}
                    onChange={(e) => setEditAssetAssigned(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="">Sin Asignar</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowEditAsset(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingAsset}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isUpdatingAsset ? "Guardando..." : "Guardar Cambios"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DIRECT NEW SOFTWARE LICENSE */}
      {showNewLicense && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Añadir Licencia SaaS</h3>
            
            <form onSubmit={handleCreateLicense} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Software / Servicio</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej: Slack Enterprise"
                    value={newLicSoftware}
                    onChange={(e) => setNewLicSoftware(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Coste de Asiento (€/mes)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="Ej: 15.00"
                    value={newLicCost}
                    onChange={(e) => setNewLicCost(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Estado</label>
                  <select
                    value={newLicStatus}
                    onChange={(e) => setNewLicStatus(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="active">Activa</option>
                    <option value="expired">Expirada</option>
                    <option value="suspended">Suspendida</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Asignar A (Usuario)</label>
                  <select
                    value={newLicAssigned}
                    onChange={(e) => setNewLicAssigned(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="">Sin Asignar</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowNewLicense(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingLicense}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isSubmittingLicense ? "Guardando..." : "Guardar Licencia"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DIRECT EDIT SOFTWARE LICENSE */}
      {showEditLicense && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-lg shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Editar Licencia SaaS</h3>
            
            <form onSubmit={handleUpdateLicense} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Software / Servicio</label>
                  <input
                    type="text"
                    required
                    value={editLicSoftware}
                    onChange={(e) => setEditLicSoftware(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Coste de Asiento (€/mes)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={editLicCost}
                    onChange={(e) => setEditLicCost(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Estado</label>
                  <select
                    value={editLicStatus}
                    onChange={(e) => setEditLicStatus(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="active">Activa</option>
                    <option value="expired">Expirada</option>
                    <option value="suspended">Suspendida</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Asignar A (Usuario)</label>
                  <select
                    value={editLicAssigned}
                    onChange={(e) => setEditLicAssigned(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-3 text-sm text-foreground focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="">Sin Asignar</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button
                  type="button"
                  onClick={() => setShowEditLicense(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingLicense}
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-cyan-500 hover:to-indigo-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                >
                  {isUpdatingLicense ? "Guardando..." : "Guardar Cambios"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
