// src/lib/api/self_service.ts — Employee Self-Service API
import { fetchClient } from './client';

export interface ProfileData {
  full_name?: string;
  phone?: string;
  address?: string;
  emergency_contact?: string;
  emergency_phone?: string;
  bank_iban?: string;
  tax_id?: string;
  [key: string]: any;
}

export const SelfServiceAPI = {
  getProfile: () => fetchClient("/self-service/profile"),
  updateProfile: (data: ProfileData) => fetchClient("/self-service/profile", { method: "PUT", body: JSON.stringify(data) }),
  getTimeOff: () => fetchClient("/self-service/time-off"),
  requestTimeOff: (data: { start_date: string; end_date: string; type?: string; reason?: string }) => fetchClient("/self-service/time-off", { method: "POST", body: JSON.stringify(data) }),
  getPayslips: () => fetchClient("/self-service/payslips"),
};
