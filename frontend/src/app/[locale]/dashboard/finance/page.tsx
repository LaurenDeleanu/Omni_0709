"use client";

import React, { useState, useEffect } from "react";
import { FinanceAPI, UserAPI } from "@/lib/api";
import { fetchClient } from "@/lib/api/client";
import { CreditCard, Clock, FileSpreadsheet, Plus, Upload, Check, ChevronRight, Eye, ShieldAlert, Sparkles, MapPin, Globe, PiggyBank, TrendingDown, TrendingUp, BarChart3, AlertTriangle, Edit, Trash2, ChevronDown } from "lucide-react";
import { useUser } from "@/hooks/use-user";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { ReceiptScanner } from "@/components/finance/ReceiptScanner";
import { InvoiceAging } from "@/components/finance/InvoiceAging";
import { PageHeader } from "@/components/layout/PageHeader";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function FinanceDashboard() {
  const [activeTab, setActiveTab] = useState<"expenses" | "ledger" | "budgets" | "invoices">("expenses");
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "super_admin";
  
  // States
  const [expenses, setExpenses] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [timeLogs, setTimeLogs] = useState<any[]>([]);
  const [activeClockIn, setActiveClockIn] = useState<any>(null);
  const [ledgerEntries, setLedgerEntries] = useState<any[]>([]);

  // Expense states
  const [showNewExpense, setShowNewExpense] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState<"idle" | "uploading" | "scanning" | "done">("idle");
  const [scannedFile, setScannedFile] = useState<File | null>(null);
  
  // Scanned Fields
  const [merchant, setMerchant] = useState("");
  const [totalAmount, setTotalAmount] = useState("");
  const [taxAmount, setTaxAmount] = useState("");
  const [category, setCategory] = useState("other");
  const [expenseDate, setExpenseDate] = useState("");
  const [expenseComments, setExpenseComments] = useState("");
  const [isSubmittingExpense, setIsSubmittingExpense] = useState(false);

  // ERP Exports
  const [exportFormat, setExportFormat] = useState("holded");
  const [exportOutput, setExportOutput] = useState("");
  const [copiedExport, setCopiedExport] = useState(false);

  // Budget states
  const [budgets, setBudgets] = useState<any[]>([]);
  const [budgetSummary, setBudgetSummary] = useState<any>(null);
  const [expandedBudget, setExpandedBudget] = useState<string | null>(null);
  const [showBudgetModal, setShowBudgetModal] = useState(false);
  const [showLineModal, setShowLineModal] = useState<string | null>(null);
  const [editingBudget, setEditingBudget] = useState<any>(null);
  const [budgetName, setBudgetName] = useState("");
  const [budgetDepartment, setBudgetDepartment] = useState("");
  const [budgetFiscalYear, setBudgetFiscalYear] = useState(new Date().getFullYear());
  const [budgetTotal, setBudgetTotal] = useState("");
  const [budgetCategory, setBudgetCategory] = useState("OPEX");
  const [budgetSpent, setBudgetSpent] = useState("");
  const [lineDescription, setLineDescription] = useState("");
  const [linePlanned, setLinePlanned] = useState("");
  const [lineActual, setLineActual] = useState("");
  const [lineCategory, setLineCategory] = useState("");

  // Invoice states
  const [invoices, setInvoices] = useState<any[]>([]);
  const [invoiceAging, setInvoiceAging] = useState<any>(null);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<any>(null);
  const [invType, setInvType] = useState("payable");
  const [invVendor, setInvVendor] = useState("");
  const [invDescription, setInvDescription] = useState("");
  const [invAmount, setInvAmount] = useState("");
  const [invTax, setInvTax] = useState("");
  const [invCurrency, setInvCurrency] = useState("EUR");
  const [invExchangeRate, setInvExchangeRate] = useState("1");
  const [invStatus, setInvStatus] = useState("draft");
  const [invIssueDate, setInvIssueDate] = useState("");
  const [invDueDate, setInvDueDate] = useState("");
  const [invCategory, setInvCategory] = useState("");
  const [invFilterType, setInvFilterType] = useState("");
  const [invFilterStatus, setInvFilterStatus] = useState("");

  // Currency states
  const [currencies, setCurrencies] = useState<any[]>([]);
  const [expenseCurrency, setExpenseCurrency] = useState("EUR");

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (user && (user.role === "hr_admin" || user.role === "super_admin")) {
      FinanceAPI.getLedger()
        .then(setLedgerEntries)
        .catch(err => console.error("Error loading ledger:", err));
    }
  }, [user]);

  useEffect(() => {
    fetchBudgetData();
  }, []);

  useEffect(() => {
    fetchInvoiceData();
    fetchCurrencies();
  }, [invFilterStatus, invFilterType]);

  const fetchInvoiceData = async () => {
    try {
      const params: any = {};
      if (invFilterStatus) params.status = invFilterStatus;
      if (invFilterType) params.type = invFilterType;
      const [invoiceData, agingData] = await Promise.all([
        FinanceAPI.getInvoices(Object.keys(params).length > 0 ? params : undefined),
        FinanceAPI.getInvoiceAging(invFilterType || undefined),
      ]);
      setInvoices(invoiceData);
      setInvoiceAging(agingData);
    } catch (err) {
      console.error("Error loading invoices:", err);
    }
  };

  const fetchCurrencies = async () => {
    try {
      const data = await FinanceAPI.getCurrencies();
      setCurrencies(data);
    } catch (err) {
      console.error("Error loading currencies:", err);
    }
  };

  const fetchBudgetData = async () => {
    try {
      const summary = await fetchClient("/finance/budgets/summary");
      setBudgetSummary(summary);
      setBudgets(summary.budgets || []);
    } catch (err) {
      console.error("Error loading budgets:", err);
    }
  };

  const fetchData = async () => {
    try {
      const [expensesData, empData] = await Promise.all([
        fetchClient("/finance/expenses"),
        UserAPI.getEmployees(),
      ]);
      setExpenses(expensesData);
      setEmployees(empData);
    } catch (err) {
      console.error("Error cargando datos de Finanzas:", err);
    }
  };

  const getEmployeeName = (userId: string) => {
    const emp = employees.find(e => e.id === userId);
    return emp ? emp.full_name : "Empleado";
  };


  // AI OCR Upload & Scanning Simulation
  const handleFileDrop = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setScannedFile(file);
    setScanStep("uploading");
    
    // Simulate uploading...
    setTimeout(async () => {
      setScanStep("scanning");
      
      // Simulate glowing scanning beam...
      setTimeout(async () => {
        try {
          const res = await FinanceAPI.scanReceiptOCR(file);
          if (res.success) {
            setMerchant(res.data.merchant);
            setTotalAmount(res.data.total_amount.toString());
            setTaxAmount(res.data.tax_amount.toString());
            setCategory(res.data.category);
            setExpenseDate(res.data.date);
            setExpenseComments(res.data.comments);
            setScanStep("done");
          }
        } catch (err) {
          console.error("Error en OCR:", err);
          setScanStep("idle");
        }
      }, 2500); // OCR scan laser duration
    }, 1000);
  };

  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchant || !totalAmount || !expenseDate) return;

    setIsSubmittingExpense(true);
    try {
      const adminUser = employees.find(e => e.email === "lauren.deleanu@gmail.com") || employees[0];
      await FinanceAPI.createExpense({
        user_id: adminUser?.id || "temp-user",
        merchant,
        date: expenseDate,
        total_amount: parseFloat(totalAmount),
        tax_amount: parseFloat(taxAmount || "0"),
        category,
        receipt_url: "https://example.com/uploads/" + (scannedFile?.name || "receipt.jpg"),
        comments: expenseComments
      });
      // Reset
      setMerchant("");
      setTotalAmount("");
      setTaxAmount("");
      setCategory("other");
      setExpenseDate("");
      setExpenseComments("");
      setExpenseCurrency("EUR");
      setScannedFile(null);
      setScanStep("idle");
      setShowNewExpense(false);
      fetchData();
    } catch (err) {
      console.error("Error creando gasto:", err);
    } finally {
      setIsSubmittingExpense(false);
    }
  };

  const handleApproveExpense = async (id: string, approve: boolean) => {
    try {
      await FinanceAPI.updateExpense(id, {
        status: approve ? "approved" : "rejected"
      });
      fetchData();
    } catch (err) {
      console.error("Error actualizando gasto:", err);
    }
  };

  const handleERPExport = async (format: string) => {
    setExportFormat(format);
    try {
      const res = await FinanceAPI.exportExpenses(format);
      if (res.success) {
        setExportOutput(res.csv_content);
      }
    } catch (err) {
      console.error("Error en exportación:", err);
    }
  };

  const copyExportCSV = () => {
    navigator.clipboard.writeText(exportOutput);
    setCopiedExport(true);
    setTimeout(() => setCopiedExport(false), 2000);
  };

  const handleCreateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!budgetName || !budgetTotal) return;
    try {
      if (editingBudget) {
        await FinanceAPI.updateBudget(editingBudget.id, {
          name: budgetName,
          department: budgetDepartment || null,
          fiscal_year: budgetFiscalYear,
          total_amount: parseFloat(budgetTotal),
          spent_amount: parseFloat(budgetSpent || "0"),
          category: budgetCategory,
        });
      } else {
        await FinanceAPI.createBudget({
          name: budgetName,
          department: budgetDepartment || null,
          fiscal_year: budgetFiscalYear,
          total_amount: parseFloat(budgetTotal),
          spent_amount: parseFloat(budgetSpent || "0"),
          category: budgetCategory,
          status: "active",
        });
      }
      resetBudgetForm();
      fetchBudgetData();
    } catch (err) {
      console.error("Error saving budget:", err);
    }
  };

  const handleDeleteBudget = async (id: string) => {
    if (!confirm("Delete this budget and all its lines?")) return;
    try {
      await FinanceAPI.deleteBudget(id);
      fetchBudgetData();
    } catch (err) {
      console.error("Error deleting budget:", err);
    }
  };

  const handleAddLine = async (budgetId: string) => {
    if (!lineDescription || !linePlanned) return;
    try {
      await FinanceAPI.addBudgetLine(budgetId, {
        description: lineDescription,
        planned_amount: parseFloat(linePlanned),
        actual_amount: parseFloat(lineActual || "0"),
        category: lineCategory || null,
      });
      setLineDescription("");
      setLinePlanned("");
      setLineActual("");
      setLineCategory("");
      setShowLineModal(null);
      fetchBudgetData();
    } catch (err) {
      console.error("Error adding line:", err);
    }
  };

  const handleDeleteLine = async (lineId: string) => {
    try {
      await FinanceAPI.deleteBudgetLine(lineId);
      fetchBudgetData();
    } catch (err) {
      console.error("Error deleting line:", err);
    }
  };

  const openEditBudget = (b: any) => {
    setEditingBudget(b);
    setBudgetName(b.name);
    setBudgetDepartment(b.department || "");
    setBudgetFiscalYear(b.fiscal_year);
    setBudgetTotal(b.total_amount.toString());
    setBudgetSpent((b.spent_amount || 0).toString());
    setBudgetCategory(b.category || "OPEX");
    setShowBudgetModal(true);
  };

  const resetBudgetForm = () => {
    setEditingBudget(null);
    setBudgetName("");
    setBudgetDepartment("");
    setBudgetFiscalYear(new Date().getFullYear());
    setBudgetTotal("");
    setBudgetSpent("");
    setBudgetCategory("OPEX");
    setShowBudgetModal(false);
  };

  const handleCreateInvoice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invAmount) return;
    try {
      const data: any = {
        type: invType,
        vendor_client: invVendor,
        description: invDescription,
        amount: parseFloat(invAmount),
        tax_amount: parseFloat(invTax || "0"),
        currency: invCurrency,
        exchange_rate: parseFloat(invExchangeRate || "1"),
        status: invStatus,
        issue_date: invIssueDate || null,
        due_date: invDueDate || null,
        category: invCategory || null,
      };
      if (editingInvoice) {
        await FinanceAPI.updateInvoice(editingInvoice.id, data);
      } else {
        await FinanceAPI.createInvoice(data);
      }
      resetInvoiceForm();
      fetchInvoiceData();
    } catch (err) {
      console.error("Error saving invoice:", err);
    }
  };

  const handleDeleteInvoice = async (id: string) => {
    if (!confirm("Delete this invoice?")) return;
    try {
      await FinanceAPI.deleteInvoice(id);
      fetchInvoiceData();
    } catch (err) {
      console.error("Error deleting invoice:", err);
    }
  };

  const handleMarkPaid = async (id: string) => {
    try {
      await FinanceAPI.markInvoicePaid(id);
      fetchInvoiceData();
    } catch (err) {
      console.error("Error marking paid:", err);
    }
  };

  const openEditInvoice = (inv: any) => {
    setEditingInvoice(inv);
    setInvType(inv.type);
    setInvVendor(inv.vendor_client || "");
    setInvDescription(inv.description || "");
    setInvAmount(inv.amount?.toString() || "");
    setInvTax(inv.tax_amount?.toString() || "");
    setInvCurrency(inv.currency || "EUR");
    setInvExchangeRate(inv.exchange_rate?.toString() || "1");
    setInvStatus(inv.status);
    setInvIssueDate(inv.issue_date ? inv.issue_date.split("T")[0] : "");
    setInvDueDate(inv.due_date ? inv.due_date.split("T")[0] : "");
    setInvCategory(inv.category || "");
    setShowInvoiceModal(true);
  };

  const resetInvoiceForm = () => {
    setEditingInvoice(null);
    setInvType("payable");
    setInvVendor("");
    setInvDescription("");
    setInvAmount("");
    setInvTax("");
    setInvCurrency("EUR");
    setInvExchangeRate("1");
    setInvStatus("draft");
    setInvIssueDate("");
    setInvDueDate("");
    setInvCategory("");
    setShowInvoiceModal(false);
  };

  const getStatusBadge = (s: string) => {
    const map: Record<string, string> = {
      draft: "bg-gray-500/10 text-gray-400 border-gray-500/20",
      sent: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      paid: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      overdue: "bg-red-500/10 text-red-400 border-red-500/20",
      cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    };
    return map[s] || map.draft;
  };

  const getStatusLabel = (s: string) => {
    const map: Record<string, string> = {
      draft: "Borrador",
      sent: "Enviada",
      paid: "Pagada",
      overdue: "Vencida",
      cancelled: "Cancelada",
    };
    return map[s] || s;
  };

  const getCurrencyFlag = (code: string) => {
    const map: Record<string, string> = {
      EUR: "🇪🇺",
      USD: "🇺🇸",
      GBP: "🇬🇧",
      MXN: "🇲🇽",
      JPY: "🇯🇵",
      CHF: "🇨🇭",
      CAD: "🇨🇦",
      AUD: "🇦🇺",
      CNY: "🇨🇳",
      BRL: "🇧🇷",
      ARS: "🇦🇷",
    };
    return map[code] || "💱";
  };

  const getPctBarColor = (pct: number) => {
    if (pct > 95) return "bg-red-500";
    if (pct > 80) return "bg-amber-500";
    return "bg-emerald-500";
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* HEADER SECTION */}
      <PageHeader
        title="Finanzas & Gastos"
        description="Aprobación inteligente de notas de gastos con escaneo IA OCR y exportación rápida a ERPs locales (Holded, Sage)."
        icon={CreditCard}
      />

      <InlineCopilot
        moduleContext="finance"
        placeholder="Pregunta sobre gastos o presupuestos..."
        quickActions={[
          { label: "Summarize my expenses", message: "Summarize my expenses" },
          { label: "Show my pending claims", message: "Show my pending claims" },
          { label: "Check budget vs actual", message: "Check budget vs actual" },
          { label: "Analyze recent transactions", message: "Analyze recent transactions" }
        ]}
      />

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><CreditCard className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Gastos en Revisión</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">
                {expenses.filter(e => e.status === "pending").length}
              </h2>
            </div>
          </div>
        </div>

        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><Sparkles className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Total Aprobado (Mes)</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">
                {expenses.filter(e => e.status === "approved").reduce((acc, e) => acc + parseFloat(e.total_amount), 0).toFixed(2)} €
              </h2>
            </div>
          </div>
        </div>

        <div className="bg-card/40 border border-border/50 rounded-xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><FileSpreadsheet className="w-6 h-6" /></div>
            <div>
              <span className="text-sm font-medium text-muted-foreground">Integraciones ERP</span>
              <h2 className="text-2xl font-bold text-foreground mt-1">Sage & Holded</h2>
            </div>
          </div>
        </div>
      </div>

      {/* NAVIGATION TABS */}
      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as any)}>
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <TabsList className="bg-transparent h-auto p-0 gap-6">
            <TabsTrigger 
              value="expenses" 
              className="data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 data-[state=active]:text-emerald-400 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-transparent border-b-2 py-2"
            >
              Notas de Gastos (Reembolsos)
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger 
                value="ledger" 
                className="data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 data-[state=active]:text-emerald-400 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-transparent border-b-2 py-2"
              >
                Libro Diario (General Ledger)
              </TabsTrigger>
            )}
            <TabsTrigger 
              value="budgets" 
              className="data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 data-[state=active]:text-emerald-400 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-transparent border-b-2 py-2"
            >
              Presupuestos
            </TabsTrigger>
            <TabsTrigger 
              value="invoices" 
              className="data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 data-[state=active]:text-emerald-400 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-transparent border-b-2 py-2"
            >
              Facturas
            </TabsTrigger>
          </TabsList>

          {activeTab === "expenses" && (
            <button
              onClick={() => setShowNewExpense(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-emerald-400/20 shadow-lg shadow-emerald-950/20"
            >
              <Plus className="w-3.5 h-3.5" />
              Escanear/Subir Recibo
            </button>
          )}
        </div>
      </Tabs>

      {/* TAB CONTENT: EXPENSE CLAIMS */}
      {activeTab === "expenses" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* EXPENSES LIST */}
          <div className="lg:col-span-2 space-y-4">
            {expenses.length === 0 ? (
              <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
                <CreditCard className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-foreground">No hay notas de gastos</h4>
                <p className="text-muted-foreground text-sm mt-1">Sube el recibo de tu primera comida, viaje o software para solicitar reembolso.</p>
              </div>
            ) : (
              expenses.map((e) => (
                <div 
                  key={e.id} 
                  className="bg-card/30 border border-border/40 hover:border-emerald-500/20 rounded-xl p-6 transition-all duration-200 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                        {e.category}
                      </span>
                      <span className="text-xs text-muted-foreground">{e.date}</span>
                    </div>
                    <h3 className="text-base font-bold text-foreground truncate">{e.merchant}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-1">{e.comments || "Sin comentarios adicionales"}</p>
                    <div className="text-xs text-muted-foreground/60 flex items-center gap-2">
                      <span>Solicitado por: <strong>{getEmployeeName(e.user_id)}</strong></span>
                      {e.tax_amount && <span>• IVA: {parseFloat(e.tax_amount).toFixed(2)} €</span>}
                    </div>
                  </div>
                  
                  <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-4 min-w-[150px] border-t md:border-t-0 border-border/20 pt-4 md:pt-0">
                    <div className="text-right">
                      <span className="text-lg font-bold text-foreground">{parseFloat(e.total_amount).toFixed(2)} €</span>
                      <span className={`block text-xs font-semibold uppercase mt-0.5 ${
                        e.status === "approved" ? "text-emerald-400" :
                        e.status === "rejected" ? "text-red-400" : "text-amber-400"
                      }`}>
                        {e.status === "approved" ? "Aprobado" :
                         e.status === "rejected" ? "Rechazado" : "Pendiente"}
                      </span>
                    </div>

                    {e.status === "pending" && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApproveExpense(e.id, false)}
                          className="px-2.5 py-1 border border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-semibold rounded cursor-pointer"
                        >
                          Rechazar
                        </button>
                        <button
                          onClick={() => handleApproveExpense(e.id, true)}
                          className="px-2.5 py-1 border border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10 text-emerald-400 text-xs font-semibold rounded cursor-pointer"
                        >
                          Aprobar
                        </button>
        </div>
      )}

      {/* TAB CONTENT: BUDGETS */}
      {(activeTab as string) === "budgets" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><PiggyBank className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Total Presupuestado</span>
                  <h2 className="text-2xl font-bold text-foreground mt-1">
                    {budgetSummary?.total_budgeted?.toFixed(0) || "0"} €
                  </h2>
                </div>
              </div>
            </div>
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-500/10 border border-amber-400/20 rounded-xl text-amber-400"><TrendingDown className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Total Gastado</span>
                  <h2 className="text-2xl font-bold text-foreground mt-1">
                    {budgetSummary?.total_spent?.toFixed(0) || "0"} €
                  </h2>
                </div>
              </div>
            </div>
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/10 border border-blue-400/20 rounded-xl text-blue-400"><TrendingUp className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Restante</span>
                  <h2 className="text-2xl font-bold text-foreground mt-1">
                    {budgetSummary?.total_remaining?.toFixed(0) || "0"} €
                  </h2>
                </div>
              </div>
            </div>
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/10 border border-purple-400/20 rounded-xl text-purple-400"><BarChart3 className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">% Utilizado</span>
                  <h2 className={`text-2xl font-bold mt-1 ${
                    budgetSummary && budgetSummary.total_budgeted > 0 && (budgetSummary.total_spent / budgetSummary.total_budgeted) > 0.8
                      ? "text-red-400"
                      : "text-emerald-400"
                  }`}>
                    {budgetSummary && budgetSummary.total_budgeted > 0
                      ? ((budgetSummary.total_spent / budgetSummary.total_budgeted) * 100).toFixed(1)
                      : "0"}%
                  </h2>
                </div>
              </div>
            </div>
          </div>

          {/* Budget List Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <PiggyBank className="w-5 h-5 text-emerald-400" />
              Presupuestos ({budgets.length})
            </h3>
            {isAdmin && (
              <button
                onClick={() => { resetBudgetForm(); setShowBudgetModal(true); }}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-emerald-400/20 shadow-lg shadow-emerald-950/20"
              >
                <Plus className="w-3.5 h-3.5" />
                Nuevo Presupuesto
              </button>
            )}
          </div>

          {/* Budget List */}
          {budgets.length === 0 ? (
            <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
              <PiggyBank className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-foreground">No hay presupuestos</h4>
              <p className="text-muted-foreground text-sm mt-1">Crea tu primer presupuesto para empezar a hacer seguimiento financiero.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {budgets.map((b: any) => {
                const pct = b.total_amount > 0 ? (b.spent_amount / b.total_amount) * 100 : 0;
                const isExpanded = expandedBudget === b.id;
                const isOver80 = pct > 80;
                return (
                  <div key={b.id} className="bg-card/30 border border-border/40 rounded-xl overflow-hidden transition-all duration-200">
                    <div
                      className="p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4 cursor-pointer hover:bg-muted/10"
                      onClick={() => setExpandedBudget(isExpanded ? null : b.id)}
                    >
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          {isOver80 && (
                            <span className="px-2 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" /> Alerta
                            </span>
                          )}
                          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                            {b.category || "OPEX"}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            b.status === "active" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                            b.status === "closed" ? "bg-slate-500/10 text-slate-400 border border-slate-500/20" :
                            "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}>
                            {b.status === "active" ? "Activo" : b.status === "closed" ? "Cerrado" : "Archivado"}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-foreground">{b.name}</h3>
                        <div className="text-xs text-muted-foreground flex items-center gap-3">
                          {b.department && <span>Dept: <strong>{b.department}</strong></span>}
                          <span>FY: <strong>{b.fiscal_year}</strong></span>
                          <span>Líneas: <strong>{(b.lines || []).length}</strong></span>
                        </div>
                      </div>

                      <div className="flex flex-col items-end min-w-[200px] gap-2">
                        <div className="flex items-center gap-5 text-sm">
                          <div className="text-right">
                            <span className="text-muted-foreground text-xs">Plan</span>
                            <div className="font-bold text-foreground">{b.total_amount.toFixed(0)} €</div>
                          </div>
                          <div className="text-right">
                            <span className="text-muted-foreground text-xs">Gastado</span>
                            <div className="font-bold text-foreground">{b.spent_amount.toFixed(0)} €</div>
                          </div>
                          <div className="text-right">
                            <span className="text-muted-foreground text-xs">Restante</span>
                            <div className={`font-bold ${b.total_amount - b.spent_amount < 0 ? "text-red-400" : "text-emerald-400"}`}>
                              {(b.total_amount - b.spent_amount).toFixed(0)} €
                            </div>
                          </div>
                        </div>
                        <div className="w-full h-2 bg-muted/50 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${getPctBarColor(pct)}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                        </div>
                        <span className={`text-xs font-semibold ${isOver80 ? "text-red-400" : "text-muted-foreground"}`}>
                          {pct.toFixed(1)}%
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {isAdmin && (
                          <>
                            <button
                              onClick={(e) => { e.stopPropagation(); openEditBudget(b); }}
                              className="p-1.5 border border-border/60 hover:bg-muted/50 rounded-lg text-muted-foreground hover:text-foreground cursor-pointer"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDeleteBudget(b.id); }}
                              className="p-1.5 border border-red-500/20 hover:bg-red-500/10 rounded-lg text-muted-foreground hover:text-red-400 cursor-pointer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        <ChevronDown className={`w-5 h-5 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                      </div>
                    </div>

                    {/* Expandable Budget Lines */}
                    {isExpanded && (
                      <div className="border-t border-border/30 px-6 py-4 bg-muted/10 space-y-3 animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-bold text-foreground">Líneas de Presupuesto</h4>
                          {isAdmin && (
                            <button
                              onClick={() => { setShowLineModal(b.id); }}
                              className="flex items-center gap-1 px-3 py-1 border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10 text-emerald-400 text-xs font-semibold rounded-lg cursor-pointer"
                            >
                              <Plus className="w-3 h-3" /> Agregar Línea
                            </button>
                          )}
                        </div>
                        {(b.lines || []).length === 0 ? (
                          <p className="text-xs text-muted-foreground py-4 text-center">Sin líneas de presupuesto. Agrega líneas para detallar los gastos planificados vs reales.</p>
                        ) : (
                          <div className="space-y-2">
                            {b.lines.map((line: any) => {
                              const linePct = line.planned_amount > 0 ? (line.actual_amount / line.planned_amount) * 100 : 0;
                              return (
                                <div key={line.id} className="flex items-center justify-between bg-card/40 border border-border/30 rounded-lg px-4 py-3 gap-4">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="text-sm font-semibold text-foreground truncate">{line.description}</span>
                                      {line.category && (
                                        <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded text-muted-foreground">{line.category}</span>
                                      )}
                                    </div>
                                    <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
                                      <span>Plan: <strong className="text-foreground">{line.planned_amount.toFixed(0)} €</strong></span>
                                      <span>Real: <strong className="text-foreground">{line.actual_amount.toFixed(0)} €</strong></span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-3 shrink-0">
                                    <div className="w-20 h-1.5 bg-muted/50 rounded-full overflow-hidden hidden sm:block">
                                      <div className={`h-full rounded-full ${getPctBarColor(linePct)}`} style={{ width: `${Math.min(linePct, 100)}%` }} />
                                    </div>
                                    <span className={`text-xs font-semibold w-10 text-right ${linePct > 80 ? "text-red-400" : "text-muted-foreground"}`}>
                                      {linePct.toFixed(0)}%
                                    </span>
                                    {isAdmin && (
                                      <button
                                        onClick={() => handleDeleteLine(line.id)}
                                        className="p-1 hover:bg-red-500/10 rounded text-muted-foreground hover:text-red-400 cursor-pointer"
                                      >
                                        <Trash2 className="w-3.5 h-3.5" />
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* ERP INTEGRATOR EXPORTER */}
          <div className="bg-gradient-to-b from-card/30 to-card/10 border border-border/40 rounded-2xl p-6 h-fit space-y-6">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2 border-b border-border/30 pb-3">
              <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
              Sincronización Contable ERP
            </h3>

            <div className="space-y-4">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Exporta las notas de gastos aprobadas en formatos estructurados planos compatibles con los ERPs españoles más utilizados.
              </p>
              
              <div className="flex gap-2">
                <button
                  onClick={() => handleERPExport("holded")}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg border cursor-pointer transition-colors ${
                    exportFormat === "holded"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "border-border/60 hover:bg-muted/50 text-muted-foreground"
                  }`}
                >
                  Holded CSV
                </button>
                <button
                  onClick={() => handleERPExport("sage")}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg border cursor-pointer transition-colors ${
                    exportFormat === "sage"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "border-border/60 hover:bg-muted/50 text-muted-foreground"
                  }`}
                >
                  Sage Diario
                </button>
              </div>
            </div>

            {exportOutput && (
              <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase">Resultado Mapeado</span>
                  <button 
                    onClick={copyExportCSV}
                    className="text-xs text-emerald-400 hover:underline cursor-pointer"
                  >
                    {copiedExport ? "¡Copiado!" : "Copiar CSV"}
                  </button>
                </div>
                <pre className="bg-muted/80 border border-border/50 rounded-lg p-3 text-[10px] font-mono text-emerald-600 dark:text-emerald-300 overflow-x-auto max-h-[150px]">
                  {exportOutput}
                </pre>
              </div>
            )}
            
            <div className="bg-emerald-500/5 rounded-xl p-4 border border-emerald-500/10 text-xs text-emerald-300 leading-relaxed flex gap-3">
              <ShieldAlert className="w-5 h-5 text-emerald-400 shrink-0" />
              <span>Las notas aprobadas se marcan con subcuentas 629000 (Otros servicios) y 465000 (Remuneraciones pendientes) en el asiento diario.</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: GENERAL LEDGER */}
      {activeTab === "ledger" && (
        <div className="bg-card/25 border border-border/40 rounded-xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border/40 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="px-6 py-4">Asiento / Ref</th>
                  <th className="px-6 py-4">Fecha</th>
                  <th className="px-6 py-4">Descripción</th>
                  <th className="px-6 py-4">Cuentas Mapeadas (Debe / Haber)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20 text-sm">
                {ledgerEntries.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-muted-foreground">
                      No hay asientos registrados en el libro diario.
                    </td>
                  </tr>
                ) : (
                  ledgerEntries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-6 py-4 font-mono text-xs text-emerald-400 font-semibold">{entry.reference}</td>
                      <td className="px-6 py-4 text-muted-foreground">{entry.date}</td>
                      <td className="px-6 py-4 text-foreground">{entry.description}</td>
                      <td className="px-6 py-4">
                        <div className="space-y-2 py-1">
                          {entry.lines?.map((line: any) => (
                            <div key={line.id} className="flex justify-between items-center gap-6 max-w-md bg-muted/40 px-3 py-1.5 rounded-lg border border-border/10 text-xs">
                              <div className="flex flex-col">
                                <span className="font-mono text-emerald-500 font-semibold">{line.account_code}</span>
                                <span className="text-[10px] text-muted-foreground">{line.account_name}</span>
                              </div>
                              <div className="flex gap-4 font-mono text-right shrink-0">
                                {parseFloat(line.debit) > 0 && (
                                  <span className="text-emerald-400">Debe: {parseFloat(line.debit).toFixed(2)} €</span>
                                )}
                                {parseFloat(line.credit) > 0 && (
                                  <span className="text-amber-400">Haber: {parseFloat(line.credit).toFixed(2)} €</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: INVOICES */}
      {activeTab === "invoices" && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/10 border border-blue-400/20 rounded-xl text-blue-400"><CreditCard className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Total Pagos</span>
                  <h2 className="text-2xl font-bold text-foreground mt-1">
                    {invoices.filter((i: any) => i.type === "payable").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0).toFixed(0)} €
                  </h2>
                </div>
              </div>
            </div>
            <div className="bg-card/40 border border-border/50 rounded-xl p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-500/10 border border-emerald-400/20 rounded-xl text-emerald-400"><TrendingUp className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Total Cobros</span>
                  <h2 className="text-2xl font-bold text-foreground mt-1">
                    {invoices.filter((i: any) => i.type === "receivable").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0).toFixed(0)} €
                  </h2>
                </div>
              </div>
            </div>
            <div className={`bg-card/40 border rounded-xl p-6 ${(invoices.filter((i: any) => i.status === "overdue").length > 0) ? "border-red-500/30" : "border-border/50"}`}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${(invoices.filter((i: any) => i.status === "overdue").length > 0) ? "bg-red-500/10 border border-red-400/20 text-red-400" : "bg-amber-500/10 border border-amber-400/20 text-amber-400"}`}><AlertTriangle className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Facturas Vencidas</span>
                  <h2 className={`text-2xl font-bold mt-1 ${(invoices.filter((i: any) => i.status === "overdue").length > 0) ? "text-red-400" : "text-foreground"}`}>
                    {invoices.filter((i: any) => i.status === "overdue").length}
                  </h2>
                </div>
              </div>
            </div>
            <div className={`bg-card/40 border rounded-xl p-6 ${(invoices.filter((i: any) => i.status === "overdue").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0) > 0) ? "border-red-500/30" : "border-border/50"}`}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${(invoices.filter((i: any) => i.status === "overdue").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0) > 0) ? "bg-red-500/10 border border-red-400/20 text-red-400" : "bg-slate-500/10 border border-slate-400/20 text-slate-400"}`}><TrendingDown className="w-6 h-6" /></div>
                <div>
                  <span className="text-sm font-medium text-muted-foreground">Importe Vencido</span>
                  <h2 className={`text-2xl font-bold mt-1 ${(invoices.filter((i: any) => i.status === "overdue").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0) > 0) ? "text-red-400" : "text-foreground"}`}>
                    {invoices.filter((i: any) => i.status === "overdue").reduce((acc: number, i: any) => acc + (i.base_amount || 0), 0).toFixed(0)} €
                  </h2>
                </div>
              </div>
            </div>
          </div>

          {/* Invoice List Header with Filters */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                Facturas ({invoices.length})
              </h3>
              <select
                value={invFilterType}
                onChange={(e) => setInvFilterType(e.target.value)}
                className="bg-muted/50 border border-input rounded-lg px-3 py-1.5 text-xs text-foreground focus:border-emerald-500 focus:outline-none"
              >
                <option value="">Todos los tipos</option>
                <option value="payable">Por Pagar</option>
                <option value="receivable">Por Cobrar</option>
              </select>
              <select
                value={invFilterStatus}
                onChange={(e) => setInvFilterStatus(e.target.value)}
                className="bg-muted/50 border border-input rounded-lg px-3 py-1.5 text-xs text-foreground focus:border-emerald-500 focus:outline-none"
              >
                <option value="">Todos los estados</option>
                <option value="draft">Borrador</option>
                <option value="sent">Enviada</option>
                <option value="paid">Pagada</option>
                <option value="overdue">Vencida</option>
                <option value="cancelled">Cancelada</option>
              </select>
            </div>
            <button
              onClick={() => { resetInvoiceForm(); setShowInvoiceModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-semibold cursor-pointer transition-all border border-emerald-400/20 shadow-lg shadow-emerald-950/20"
            >
              <Plus className="w-3.5 h-3.5" />
              Nueva Factura
            </button>
          </div>

          {/* Invoice List */}
          {invoices.length === 0 ? (
            <div className="bg-card/20 rounded-xl border border-border/30 p-12 text-center">
              <FileSpreadsheet className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-foreground">No hay facturas</h4>
              <p className="text-muted-foreground text-sm mt-1">Crea tu primera factura para empezar a gestionar pagos y cobros.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {invoices.map((inv: any) => (
                <div key={inv.id} className="bg-card/30 border border-border/40 hover:border-emerald-500/20 rounded-xl p-6 transition-all duration-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-emerald-400 font-bold">{inv.invoice_number}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${inv.type === "payable" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"}`}>
                        {inv.type === "payable" ? "Por Pagar" : "Por Cobrar"}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getStatusBadge(inv.status)}`}>
                        {getStatusLabel(inv.status)}
                      </span>
                      {inv.category && (
                        <span className="px-2 py-0.5 bg-muted/50 rounded text-[10px] text-muted-foreground">{inv.category}</span>
                      )}
                    </div>
                    <h3 className="text-base font-bold text-foreground truncate">{inv.vendor_client || "Sin proveedor/cliente"}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-1">{inv.description || "Sin descripción"}</p>
                    <div className="text-xs text-muted-foreground flex items-center gap-3">
                      {inv.issue_date && <span>Emisión: <strong>{inv.issue_date.split("T")[0]}</strong></span>}
                      {inv.due_date && <span>Vencimiento: <strong className={inv.status === "overdue" ? "text-red-400" : ""}>{inv.due_date.split("T")[0]}</strong></span>}
                    </div>
                  </div>

                  <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-4 min-w-[160px] border-t md:border-t-0 border-border/20 pt-4 md:pt-0">
                    <div className="text-right">
                      <div className="flex items-center gap-1.5 justify-end">
                        <span className="text-sm">{getCurrencyFlag(inv.currency)}</span>
                        <span className="text-lg font-bold text-foreground">{inv.total_amount?.toFixed(2)}</span>
                        <span className="text-xs text-muted-foreground">{inv.currency}</span>
                      </div>
                      {inv.currency !== "EUR" && (
                        <span className="block text-xs text-muted-foreground mt-0.5">≈ {inv.base_amount?.toFixed(2)} €</span>
                      )}
                    </div>

                    <div className="flex gap-2">
                      {(inv.status === "sent" || inv.status === "overdue") && (
                        <button
                          onClick={() => handleMarkPaid(inv.id)}
                          className="px-2.5 py-1 border border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10 text-emerald-400 text-xs font-semibold rounded cursor-pointer"
                        >
                          Pagar
                        </button>
                      )}
                      {isAdmin && inv.status === "draft" && (
                        <button
                          onClick={() => handleDeleteInvoice(inv.id)}
                          className="px-2.5 py-1 border border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-semibold rounded cursor-pointer"
                        >
                          Eliminar
                        </button>
                      )}
                      <button
                        onClick={() => openEditInvoice(inv)}
                        className="px-2.5 py-1 border border-border/60 hover:bg-muted/50 text-muted-foreground hover:text-foreground text-xs font-semibold rounded cursor-pointer"
                      >
                        Editar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Aging Report */}
          {invoiceAging && (
            <div className="bg-card/25 border border-border/40 rounded-xl p-6 space-y-4">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-400" />
                Informe de Antigüedad (Aging)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-muted/30 rounded-lg p-4 text-center">
                  <span className="text-xs text-muted-foreground">0-30 días</span>
                  <div className={`text-lg font-bold mt-1 ${invoiceAging.bucket_0_30 > 0 ? "text-emerald-400" : "text-foreground"}`}>
                    {invoiceAging.bucket_0_30?.toFixed(0)} €
                  </div>
                  <span className="text-xs text-muted-foreground">{invoiceAging.count_0_30} facturas</span>
                </div>
                <div className="bg-muted/30 rounded-lg p-4 text-center">
                  <span className="text-xs text-muted-foreground">31-60 días</span>
                  <div className={`text-lg font-bold mt-1 ${invoiceAging.bucket_31_60 > 0 ? "text-amber-400" : "text-foreground"}`}>
                    {invoiceAging.bucket_31_60?.toFixed(0)} €
                  </div>
                  <span className="text-xs text-muted-foreground">{invoiceAging.count_31_60} facturas</span>
                </div>
                <div className="bg-muted/30 rounded-lg p-4 text-center">
                  <span className="text-xs text-muted-foreground">61-90 días</span>
                  <div className={`text-lg font-bold mt-1 ${invoiceAging.bucket_61_90 > 0 ? "text-orange-400" : "text-foreground"}`}>
                    {invoiceAging.bucket_61_90?.toFixed(0)} €
                  </div>
                  <span className="text-xs text-muted-foreground">{invoiceAging.count_61_90} facturas</span>
                </div>
                <div className="bg-muted/30 rounded-lg p-4 text-center">
                  <span className="text-xs text-muted-foreground">90+ días</span>
                  <div className={`text-lg font-bold mt-1 ${invoiceAging.bucket_90_plus > 0 ? "text-red-400" : "text-foreground"}`}>
                    {invoiceAging.bucket_90_plus?.toFixed(0)} €
                  </div>
                  <span className="text-xs text-muted-foreground">{invoiceAging.count_90_plus} facturas</span>
                </div>
              </div>
              <div className="text-right text-sm text-muted-foreground">
                Total pendiente: <strong className="text-foreground">{invoiceAging.total_outstanding?.toFixed(0)} €</strong>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: AI RECEIPTS OCR SCANNER */}
      {showNewExpense && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-xl shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Escanear Recibo mediante IA</h3>
            
            {scanStep !== "done" ? (
              <div className="border-2 border-dashed border-border/80 hover:border-emerald-500/40 bg-muted/40 rounded-2xl p-8 flex flex-col items-center justify-center text-center relative overflow-hidden h-[250px]">
                
                {/* Glowing Laser Scan beam */}
                {scanStep === "scanning" && (
                  <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent top-0 animate-[bounce_2.5s_infinite] shadow-lg shadow-emerald-400/50"></div>
                )}

                <Upload className={`w-12 h-12 mb-4 transition-colors ${
                  scanStep === "scanning" ? "text-emerald-400 animate-pulse" : "text-muted-foreground/50"
                }`} />

                {scanStep === "idle" && (
                  <>
                    <h4 className="text-base font-bold text-foreground">Arrastra tu ticket o haz click</h4>
                    <p className="text-xs text-muted-foreground mt-1">Soporta imágenes JPG, PNG y documentos PDF.</p>
                    <input
                      type="file"
                      onChange={handleFileDrop}
                      className="absolute inset-0 opacity-0 cursor-pointer"
                    />
                  </>
                )}

                {scanStep === "uploading" && (
                  <h4 className="text-base font-bold text-foreground animate-pulse">Cargando archivo en Sandbox seguro...</h4>
                )}

                {scanStep === "scanning" && (
                  <>
                    <h4 className="text-base font-bold text-emerald-400 flex items-center gap-2">
                      <Sparkles className="w-5 h-5 animate-spin" />
                      Analizando con SuccessCore AI OCR...
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">Extrayendo proveedor, fecha, base imponible e IVA.</p>
                  </>
                )}
              </div>
            ) : (
              <form onSubmit={handleCreateExpense} className="space-y-4">
                <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 text-xs text-emerald-300 rounded-lg flex items-center gap-2">
                  <Sparkles className="w-4 h-4 shrink-0" />
                  <span>Extracción completada. Por favor revisa los datos antes de enviar.</span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Establecimiento</label>
                    <input
                      type="text"
                      required
                      value={merchant}
                      onChange={(e) => setMerchant(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Fecha del ticket</label>
                    <input
                      type="date"
                      required
                      value={expenseDate}
                      onChange={(e) => setExpenseDate(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Importe Total</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={totalAmount}
                      onChange={(e) => setTotalAmount(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Impuestos (IVA)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={taxAmount}
                      onChange={(e) => setTaxAmount(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    >
                      <option value="other">Otros</option>
                      <option value="meals">Comida/Restauración</option>
                      <option value="travel">Viajes/Transporte</option>
                      <option value="software">Software SaaS</option>
                      <option value="supplies">Suministros</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Moneda</label>
                    <select
                      value={expenseCurrency}
                      onChange={(e) => setExpenseCurrency(e.target.value)}
                      className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                    >
                      {currencies.map((c: any) => (
                        <option key={c.code} value={c.code}>{getCurrencyFlag(c.code)} {c.code}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1 flex items-end">
                    {expenseCurrency !== "EUR" && (
                      <div className="text-xs text-muted-foreground bg-muted/30 rounded-lg p-2.5 w-full">
                        ≈ {(parseFloat(totalAmount || "0") * parseFloat(currencies.find((c: any) => c.code === expenseCurrency)?.rate_to_eur || "1")).toFixed(2)} €
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Comentarios</label>
                  <input
                    type="text"
                    value={expenseComments}
                    onChange={(e) => setExpenseComments(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                  <button
                    type="button"
                    onClick={() => {
                      setScanStep("idle");
                      setScannedFile(null);
                    }}
                    className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                  >
                    Volver a subir
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingExpense}
                    className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 disabled:from-muted text-white text-sm font-semibold rounded-lg cursor-pointer"
                  >
                    {isSubmittingExpense ? "Registrando..." : "Guardar Nota de Gasto"}
                  </button>
                </div>
              </form>
            )}

            {scanStep === "idle" && (
              <div className="flex justify-end pt-4 border-t border-border/20 mt-4">
                <button
                  type="button"
                  onClick={() => setShowNewExpense(false)}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer"
                >
                  Cerrar
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: BUDGET CREATE/EDIT */}
      {showBudgetModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-xl shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">{editingBudget ? "Editar Presupuesto" : "Nuevo Presupuesto"}</h3>
            <form onSubmit={handleCreateBudget} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1 col-span-2">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Nombre</label>
                  <input type="text" required value={budgetName} onChange={(e) => setBudgetName(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Departamento</label>
                  <input type="text" value={budgetDepartment} onChange={(e) => setBudgetDepartment(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Año Fiscal</label>
                  <input type="number" required value={budgetFiscalYear} onChange={(e) => setBudgetFiscalYear(parseInt(e.target.value))}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Total Presupuestado</label>
                  <input type="number" step="0.01" required value={budgetTotal} onChange={(e) => setBudgetTotal(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Gastado</label>
                  <input type="number" step="0.01" value={budgetSpent} onChange={(e) => setBudgetSpent(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                  <select value={budgetCategory} onChange={(e) => setBudgetCategory(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none">
                    <option value="OPEX">OPEX</option>
                    <option value="CAPEX">CAPEX</option>
                    <option value="HR">HR</option>
                    <option value="IT">IT</option>
                    <option value="Marketing">Marketing</option>
                    <option value="Ventas">Ventas</option>
                    <option value="Otros">Otros</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button type="button" onClick={resetBudgetForm}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer">
                  Cancelar
                </button>
                <button type="submit"
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-semibold rounded-lg cursor-pointer">
                  {editingBudget ? "Actualizar" : "Crear"} Presupuesto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD BUDGET LINE */}
      {showLineModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl relative animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-foreground mb-4">Agregar Línea de Presupuesto</h3>
            <form onSubmit={(e) => { e.preventDefault(); handleAddLine(showLineModal!); }} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Descripción</label>
                <input type="text" required value={lineDescription} onChange={(e) => setLineDescription(e.target.value)}
                  className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Planificado</label>
                  <input type="number" step="0.01" required value={linePlanned} onChange={(e) => setLinePlanned(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Real</label>
                  <input type="number" step="0.01" value={lineActual} onChange={(e) => setLineActual(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                <input type="text" value={lineCategory} onChange={(e) => setLineCategory(e.target.value)}
                  placeholder="Ej: Nóminas, SaaS, Viajes..."
                  className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button type="button" onClick={() => { setShowLineModal(null); setLineDescription(""); setLinePlanned(""); setLineActual(""); setLineCategory(""); }}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer">
                  Cancelar
                </button>
                <button type="submit"
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-semibold rounded-lg cursor-pointer">
                  Agregar Línea
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: INVOICE CREATE/EDIT */}
      {showInvoiceModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-2xl shadow-2xl relative animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-foreground mb-4">{editingInvoice ? "Editar Factura" : "Nueva Factura"}</h3>
            <form onSubmit={handleCreateInvoice} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Tipo</label>
                  <select value={invType} onChange={(e) => setInvType(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none">
                    <option value="payable">Por Pagar</option>
                    <option value="receivable">Por Cobrar</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Estado</label>
                  <select value={invStatus} onChange={(e) => setInvStatus(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none">
                    <option value="draft">Borrador</option>
                    <option value="sent">Enviada</option>
                    <option value="paid">Pagada</option>
                    <option value="overdue">Vencida</option>
                    <option value="cancelled">Cancelada</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Proveedor / Cliente</label>
                  <input type="text" value={invVendor} onChange={(e) => setInvVendor(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Categoría</label>
                  <input type="text" value={invCategory} onChange={(e) => setInvCategory(e.target.value)} placeholder="Ej: SaaS, Consultoría..."
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Descripción</label>
                <textarea value={invDescription} onChange={(e) => setInvDescription(e.target.value)} rows={2}
                  className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none resize-none" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Importe</label>
                  <input type="number" step="0.01" required value={invAmount} onChange={(e) => setInvAmount(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Impuestos</label>
                  <input type="number" step="0.01" value={invTax} onChange={(e) => setInvTax(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Moneda</label>
                  <select value={invCurrency} onChange={(e) => { setInvCurrency(e.target.value); const c = currencies.find((c: any) => c.code === e.target.value); if (c) setInvExchangeRate(c.rate_to_eur.toString()); }}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none">
                    {currencies.map((c: any) => (
                      <option key={c.code} value={c.code}>{getCurrencyFlag(c.code)} {c.code}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Tipo de Cambio (a EUR)</label>
                  <input type="number" step="0.000001" value={invExchangeRate} onChange={(e) => setInvExchangeRate(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Fecha Emisión</label>
                  <input type="date" value={invIssueDate} onChange={(e) => setInvIssueDate(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">Fecha Vencimiento</label>
                  <input type="date" value={invDueDate} onChange={(e) => setInvDueDate(e.target.value)}
                    className="w-full bg-muted/50 border border-input rounded-lg p-2.5 text-sm text-foreground focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>
              {invCurrency !== "EUR" && (
                <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 text-xs text-emerald-300 rounded-lg">
                  <span>Total en EUR: <strong>≈ {((parseFloat(invAmount || "0") + parseFloat(invTax || "0")) * parseFloat(invExchangeRate || "1")).toFixed(2)} €</strong></span>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                <button type="button" onClick={resetInvoiceForm}
                  className="px-4 py-2 border border-border/60 hover:bg-muted/50 text-foreground text-sm font-semibold rounded-lg cursor-pointer">
                  Cancelar
                </button>
                <button type="submit"
                  className="px-4 py-2 bg-gradient-to-r bg-primary hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-semibold rounded-lg cursor-pointer">
                  {editingInvoice ? "Actualizar" : "Crear"} Factura
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ReceiptScanner />

      <InvoiceAging />

    </div>
  );
}
