// src/lib/api/index.ts — Barrel re-export
// All consumers importing from "@/lib/api" continue to work unchanged.
export { APIError, fetchClient, downloadBlob, API_BASE } from './client';
export * from './notifications';
export * from './kudos';
export * from './workflows';
export * from './chat';

// Domain modules — split for tree-shaking
export { type TenantSettings, TenantAPI } from './tenant';
export { type Employee, type HistoryEntry, UserAPI, HistoryAPI } from './users';
export { type CalendarEvent, type VacationRequest, type Meeting, type Task, CalendarAPI } from './calendar';
export { type ReportSummary, type DashboardSummary, type DashboardData, ReportAPI } from './reports';
export { type PageMetadata, MetadataAPI } from './metadata';
export { type Schedule, ScheduleAPI } from './schedules';
export { type ImportStatus, type EntityDefinition, type EntityList, ImportAPI } from './imports';
export { AiAPI, CopilotAPI } from './ai';
export { ITAPI } from './it';
export { FinanceAPI } from './finance';
export { TrainingAPI } from './training';
export { type AdminDashboardSummary, AdminAPI } from './admin';
export { type JobPosting, type Candidate, type CandidatePool, type PoolCandidate, type CrmCandidate, HireAPI } from './hire';
export { type Client, type Lead, SalesAPI } from './sales';
export { type Project, type BoardColumn, type KanbanBoard, type WikiPage, WorkAPI } from './work';
export { type FacilityAsset, type AssetBooking, type VisitorLog, type CalendarBooking, type MaintenanceRequest, type MaintenanceStats, OpsAPI } from './ops';
export { type DashboardWidget, type Dashboard, IntelAPI } from './intel';
export { type PayrollCycle, type Payslip, type TaxRule, type Bonus, type EmployeeCompensation, PayAPI } from './pay';
export { type Contract, type WhistleblowerReport, type DSARTicket, LegalAPI } from './legal';
export { type Permission, type RolePermission, type Role, RBACAPI } from './rbac';
export { type KeyResult, type Objective, type PerformanceReview, GrowAPI } from './grow';
export { OmniAPI, type OmniFileItem, type OmniGitStatusFile, type OmniGitStatus, type OmniBranch, type OmniAgentSettings, type OmniRunResult, type OmniTraceStep } from './omni';
export { HRPanelAPI, type HROverview, type HRTicket, type HREmployeeRequest, type RecruitingOverview, type ComplianceOverview } from './hr_panel';

// Added during codebase audit:
export { type Agent, AgentsAPI } from './agents';
export { type BillingSettings, BillingAPI } from './billing';
export { type ChecklistTemplate, ChecklistsAPI } from './checklists';
export { type Scorecard, InterviewsAPI } from './interviews';
export { MarketplaceAPI } from './marketplace';
export { type ProfileData, SelfServiceAPI } from './self_service';
export { SurveysAPI } from './surveys';
export { TimeTrackingAPI } from './time_tracking';
export { DocumentsAPI } from './documents';
export { DevPortalAPI } from './dev_portal';

