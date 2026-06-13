"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminAPI, TrainingAPI } from "@/lib/api";
import { Shield, Laptop, GraduationCap, Users, Activity } from "lucide-react";
import { toast } from "sonner";
import { useTenant } from "@/providers/tenant-provider";

import { ModulesTab } from "./components/ModulesTab";
import { AssignmentsTab } from "./components/AssignmentsTab";
import { RBACTab } from "./components/RBACTab";
import { AuditTab } from "./components/AuditTab";
import { PageHeader } from "@/components/layout/PageHeader";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { enabledModules } = useTenant();
  const [activeTab, setActiveTab] = useState("modules");

  // ── Shared queries ────────────────────────────────────────────────────────
  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: () => AdminAPI.getUsers(),
  });

  const { data: auditLogs = [], isLoading: loadingLogs } = useQuery({
    queryKey: ["adminAuditLogs"],
    queryFn: () => AdminAPI.getAuditLogs(),
  });

  const { data: courses = [], isLoading: loadingCourses } = useQuery({
    queryKey: ["adminCourses"],
    queryFn: () => TrainingAPI.getCourses(),
  });

  const { data: assignments, isLoading: loadingAssignments } = useQuery({
    queryKey: ["adminAssignmentsStatus"],
    queryFn: () => AdminAPI.getAssignmentsStatus(),
  });

  const { data: roles = [], isLoading: loadingRoles, refetch: refetchRoles } = useQuery({
    queryKey: ["adminRoles"],
    queryFn: () => AdminAPI.getRoles(),
  });

  const { data: permissions = [], isLoading: loadingPerms } = useQuery({
    queryKey: ["adminPermissions"],
    queryFn: () => AdminAPI.getPermissions(),
  });

  // ── Shared mutations ──────────────────────────────────────────────────────
  const toggleModuleMutation = useMutation({
    mutationFn: (data: { enabled_modules: Record<string, boolean> }) => AdminAPI.toggleModules(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
      toast.success("Módulos actualizados", { description: "La configuración de la plataforma se ha guardado." });
      setTimeout(() => window.location.reload(), 1000);
    },
    onError: () => toast.error("Error", { description: "No se pudieron actualizar los módulos." }),
  });

  const changeUserRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => AdminAPI.updateUserRole(userId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
      toast.success("Rol Actualizado", { description: "El rol del empleado se actualizó correctamente." });
    },
    onError: () => toast.error("Error", { description: "No se pudo actualizar el rol." }),
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  const isModuleActive = (key: string) => enabledModules?.[key] !== false;

  const handleModuleToggle = (moduleKey: string, checked: boolean) => {
    const nextModules = {
      it: enabledModules?.it ?? true,
      finance: enabledModules?.finance ?? true,
      training: enabledModules?.training ?? true,
      schedules: enabledModules?.schedules ?? true,
      ...enabledModules,
      [moduleKey]: checked
    };
    toggleModuleMutation.mutate({ enabled_modules: nextModules });
  };

  // ── Tab definitions ───────────────────────────────────────────────────────
  const TABS = [
    { id: "modules", name: "Módulos de la Plataforma", icon: Laptop },
    { id: "assignments", name: "Asignación de Cursos y Tareas", icon: GraduationCap },
    { id: "rbac", name: "Seguridad y Roles (RBAC)", icon: Users },
    { id: "audit", name: "Historial de Auditoría", icon: Activity }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <PageHeader
        title="Panel de Administración"
        description="Gestiona módulos activos, asignaciones formativas, roles de seguridad y auditoría de la organización."
        icon={Shield}
      />
      
      <InlineCopilot
        moduleContext="admin"
        placeholder="Pregunta sobre permisos, módulos o auditoría..."
        quickActions={[
          { label: "Mostrar historial de auditoría", message: "Mostrar historial de auditoría" },
          { label: "Verificar roles de usuario", message: "Verificar roles de usuario" },
          { label: "Resumir estado de módulos", message: "Resumir estado de módulos" },
        ]}
      />

      {/* HORIZONTAL TABS CONTROLLER */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="border-b border-border/50">
          <TabsList className="bg-transparent h-auto p-0 gap-6 overflow-x-auto flex justify-start scrollbar-none w-full">
            {TABS.map((tab) => (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-transparent border-b-2 py-3 px-1 flex items-center gap-2.5 whitespace-nowrap"
              >
                <tab.icon className="w-4 h-4" />
                {tab.name}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
      </Tabs>

      {/* ACTIVE TAB CONTENT */}
      <div className="mt-6">
        {activeTab === "modules" && (
          <ModulesTab
            enabledModules={enabledModules}
            isModuleActive={isModuleActive}
            handleModuleToggle={handleModuleToggle}
            togglePending={toggleModuleMutation.isPending}
            usersCount={users?.length ?? 0}
            coursesCount={courses?.length ?? 0}
            loadingUsers={loadingUsers}
            loadingCourses={loadingCourses}
          />
        )}

        {activeTab === "assignments" && (
          <AssignmentsTab
            users={users}
            courses={courses}
            assignments={assignments}
            loadingUsers={loadingUsers}
            loadingCourses={loadingCourses}
            loadingAssignments={loadingAssignments}
          />
        )}

        {activeTab === "rbac" && (
          <RBACTab
            users={users}
            roles={roles}
            permissions={permissions}
            loadingUsers={loadingUsers}
            loadingRoles={loadingRoles}
            loadingPerms={loadingPerms}
            refetchRoles={refetchRoles}
            changeUserRoleMutation={changeUserRoleMutation}
          />
        )}

        {activeTab === "audit" && (
          <AuditTab
            auditLogs={auditLogs}
            loadingLogs={loadingLogs}
          />
        )}
      </div>
    </div>
  );
}
