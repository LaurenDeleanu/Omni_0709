// src/lib/api/finance.ts — Finance & accounting API
import { fetchClient } from './client';

export const FinanceAPI = {
  getExpenses: (status?: string, userId?: string) => {
    let query = "";
    const params = [];
    if (status) params.push(`status=${status}`);
    if (userId) params.push(`user_id=${userId}`);
    if (params.length) query = `?${params.join("&")}`;
    return fetchClient(`/finance/expenses${query}`);
  },
  createExpense: (data: any) => fetchClient("/finance/expenses", { method: "POST", body: JSON.stringify(data) }),
  updateExpense: (id: string, data: any) => fetchClient(`/finance/expenses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  scanReceiptOCR: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchClient("/finance/expenses/ocr", { method: "POST", body: formData });
  },
  exportExpenses: (format: string) => fetchClient(`/finance/expenses/export?format=${format}`),
  getTimeLogs: (userId?: string) => {
    const query = userId ? `?user_id=${userId}` : "";
    return fetchClient(`/finance/time-logs${query}`);
  },
  clockIn: (data: any) => fetchClient("/finance/time-logs/clock-in", { method: "POST", body: JSON.stringify(data) }),
  clockOut: (logId: string, data: any) => fetchClient(`/finance/time-logs/clock-out/${logId}`, { method: "POST", body: JSON.stringify(data) }),
  getLedger: () => fetchClient("/finance/ledger"),

  // ── Budget API ──
  getBudgets: (params?: { fiscal_year?: number; department?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.fiscal_year) qs.set("fiscal_year", String(params.fiscal_year));
    if (params?.department) qs.set("department", params.department);
    if (params?.status) qs.set("budget_status", params.status);
    const query = qs.toString();
    return fetchClient(`/finance/budgets${query ? `?${query}` : ""}`);
  },
  getBudgetSummary: (fiscalYear?: number) => {
    const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
    return fetchClient(`/finance/budgets/summary${query}`);
  },
  getBudget: (id: string) => fetchClient(`/finance/budgets/${id}`),
  createBudget: (data: any) => fetchClient("/finance/budgets", { method: "POST", body: JSON.stringify(data) }),
  updateBudget: (id: string, data: any) => fetchClient(`/finance/budgets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteBudget: (id: string) => fetchClient(`/finance/budgets/${id}`, { method: "DELETE" }),
  addBudgetLine: (budgetId: string, data: any) => fetchClient(`/finance/budgets/${budgetId}/lines`, { method: "POST", body: JSON.stringify(data) }),
  updateBudgetLine: (lineId: string, data: any) => fetchClient(`/finance/budgets/lines/${lineId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteBudgetLine: (lineId: string) => fetchClient(`/finance/budgets/lines/${lineId}`, { method: "DELETE" }),
  checkBudgetAlert: (budgetId: string) => fetchClient(`/finance/budgets/${budgetId}/alert`, { method: "POST" }),

  // ── Invoice API ──
  getInvoices: (params?: { status?: string; type?: string; date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.type) qs.set("type", params.type);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    const query = qs.toString();
    return fetchClient(`/finance/invoices${query ? `?${query}` : ""}`);
  },
  createInvoice: (data: any) => fetchClient("/finance/invoices", { method: "POST", body: JSON.stringify(data) }),
  getInvoice: (id: string) => fetchClient(`/finance/invoices/${id}`),
  updateInvoice: (id: string, data: any) => fetchClient(`/finance/invoices/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteInvoice: (id: string) => fetchClient(`/finance/invoices/${id}`, { method: "DELETE" }),
  markInvoicePaid: (id: string) => fetchClient(`/finance/invoices/${id}/mark-paid`, { method: "POST" }),
  markInvoiceOverdue: (id: string) => fetchClient(`/finance/invoices/${id}/mark-overdue`, { method: "POST" }),
  getInvoiceAging: (type?: string) => {
    const query = type ? `?type=${type}` : "";
    return fetchClient(`/finance/invoices/aging${query}`);
  },

  // ── Currency API ──
  getCurrencies: () => fetchClient("/finance/currencies"),
  convertCurrency: (from: string, to: string, amount: number) =>
    fetchClient("/finance/currencies/convert", { method: "POST", body: JSON.stringify({ from_currency: from, to_currency: to, amount }) }),
  refreshCurrencyRates: () => fetchClient("/finance/currencies/refresh"),
};

export const getBudgetSummary = FinanceAPI.getBudgetSummary;
export const getInvoices = FinanceAPI.getInvoices;
export const getInvoiceAging = FinanceAPI.getInvoiceAging;
export const getCurrencies = FinanceAPI.getCurrencies;
export const getExpenses = FinanceAPI.getExpenses;
