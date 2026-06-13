// src/lib/api/pay.ts — Payroll & benefits API
import { fetchClient, downloadBlob } from './client';

export interface PayrollCycle {
  id: string;
  period_name: string;
  start_date: string;
  end_date: string;
  status: string;
  total_gross: number;
  total_net: number;
  currency: string;
  created_at: string;
}

export interface Payslip {
  id: string;
  cycle_id: string;
  employee_id: string;
  employee_name?: string;
  employee_email?: string;
  gross_salary: number;
  deductions: number;
  net_salary: number;
  currency: string;
  status: string;
  created_at: string;
}

export interface TaxRule {
  id: string;
  country_code: string;
  name: string;
  calculation_type: string;
  rate: number;
  min_salary?: number;
  max_salary?: number;
  is_deduction: boolean;
  is_marginal: boolean;
}

export interface Bonus {
  id: string;
  employee_id: string;
  amount: number;
  description: string;
  type: string;
  status: string;
  payslip_id?: string;
  created_at: string;
}

export interface EmployeeCompensation {
  id: string;
  email: string;
  full_name?: string;
  department?: string;
  base_salary: number;
  country: string;
}

export const PayAPI = {
  getMyPayslips: () => fetchClient("/pay/my-payslips"),
  downloadPayslipPDF: (payslipId: string, periodName: string) =>
    downloadBlob(`/pay/payslips/${payslipId}/pdf`, `nomina_${periodName.replace(/ /g, "_")}_${payslipId}.pdf`),
  getCycles: () => fetchClient("/pay/cycles"),
  createCycle: (data: Partial<PayrollCycle>) => fetchClient("/pay/cycles", { method: "POST", body: JSON.stringify(data) }),
  updateCycleStatus: (cycleId: string, status: string) => fetchClient(`/pay/cycles/${cycleId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  getCyclePayslips: (cycleId: string) => fetchClient(`/pay/cycles/${cycleId}/payslips`),
  processPayroll: (cycleId: string) => fetchClient(`/pay/cycles/${cycleId}/process`, { method: "POST" }),
  getTaxRules: () => fetchClient("/pay/rules"),
  updateTaxRule: (id: string, data: Partial<TaxRule>) => fetchClient(`/pay/rules/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  getEmployeeCompensations: () => fetchClient("/pay/employees/compensation"),
  updateEmployeeCompensation: (id: string, data: Partial<EmployeeCompensation>) => fetchClient(`/pay/employees/${id}/compensation`, { method: "PUT", body: JSON.stringify(data) }),
  getBonuses: (employeeId: string) => fetchClient(`/pay/employees/${employeeId}/bonuses`),
  createBonus: (employeeId: string, data: { amount: number, description: string, type: string }) => fetchClient(`/pay/employees/${employeeId}/bonuses`, { method: "POST", body: JSON.stringify(data) }),
  deleteBonus: (bonusId: string) => fetchClient(`/pay/bonuses/${bonusId}`, { method: "DELETE" }),
};
