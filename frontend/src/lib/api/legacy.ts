// src/lib/api/legacy.ts — Backward-compatible re-export barrel
// All modules have been split into individual files for tree-shaking.
// This file re-exports everything for backward compatibility.
export { type TenantSettings, TenantAPI } from './tenant';
export { type Employee, type HistoryEntry, UserAPI, HistoryAPI } from './users';
export { type CalendarEvent, type VacationRequest, type Meeting, type Task as CalendarTask, CalendarAPI } from './calendar';
export { type ReportSummary, type DashboardSummary, ReportAPI } from './reports';
export { type PageMetadata, MetadataAPI } from './metadata';
export { type Schedule, ScheduleAPI } from './schedules';
export { type ImportStatus, ImportAPI } from './imports';
export { AiAPI } from './ai';
export { ITAPI } from './it';
export { FinanceAPI } from './finance';
export { TrainingAPI } from './training';
export { AdminAPI } from './admin';
export { type JobPosting, type Candidate, HireAPI } from './hire';
export { type Client, type Lead, SalesAPI } from './sales';
export { type Project, type BoardColumn, type KanbanBoard, type WikiPage, WorkAPI } from './work';
export { type FacilityAsset, type AssetBooking, type VisitorLog, OpsAPI } from './ops';
export { type DashboardWidget, type Dashboard, IntelAPI } from './intel';
export { type PayrollCycle, type Payslip, type TaxRule, type Bonus, type EmployeeCompensation, PayAPI } from './pay';
export { type Contract, type WhistleblowerReport, type DSARTicket, LegalAPI } from './legal';
export { type Permission, type RolePermission, type Role, RBACAPI } from './rbac';
export { type KeyResult, type Objective, type PerformanceReview, GrowAPI } from './grow';
