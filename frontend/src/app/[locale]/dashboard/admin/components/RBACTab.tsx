"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2, Shield, Users, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface RBACTabProps {
  users: any[];
  roles: any[];
  permissions: any[];
  loadingUsers: boolean;
  loadingRoles: boolean;
  loadingPerms: boolean;
  refetchRoles: () => void;
  changeUserRoleMutation: any;
}

export function RBACTab({ users, roles, permissions, loadingUsers, loadingRoles, loadingPerms, refetchRoles, changeUserRoleMutation }: RBACTabProps) {
  const queryClient = useQueryClient();

  const [showRoleBuilder, setShowRoleBuilder] = useState(false);
  const [editingRole, setEditingRole] = useState<any>(null);
  const [roleFormName, setRoleFormName] = useState("");
  const [roleFormDesc, setRoleFormDesc] = useState("");
  const [roleFormPerms, setRoleFormPerms] = useState<string[]>([]);
  const [searchRoles, setSearchRoles] = useState("");
  const [searchUsers, setSearchUsers] = useState("");

  const filteredRoles = roles?.filter((r: any) =>
    r.name.toLowerCase().includes(searchRoles.toLowerCase())
  );

  const filteredUsers = users?.filter((u: any) =>
    u.full_name?.toLowerCase().includes(searchUsers.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchUsers.toLowerCase()) ||
    u.department?.toLowerCase().includes(searchUsers.toLowerCase())
  );

  const createRoleMutation = useMutation({
    mutationFn: (data: any) => AdminAPI.createRole(data),
    onSuccess: () => {
      toast.success("Rol Creado", { description: "El rol personalizado se creó correctamente." });
      refetchRoles();
      setShowRoleBuilder(false);
    }
  });

  const updateRoleMutation = useMutation({
    mutationFn: (data: { id: string, payload: any }) => AdminAPI.updateRole(data.id, data.payload),
    onSuccess: () => {
      toast.success("Rol Actualizado", { description: "Los permisos del rol se han guardado." });
      refetchRoles();
      setShowRoleBuilder(false);
    }
  });

  const deleteRoleMutation = useMutation({
    mutationFn: (id: string) => AdminAPI.deleteRole(id),
    onSuccess: () => {
      toast.success("Rol Eliminado", { description: "El rol ha sido borrado." });
      refetchRoles();
    },
    onError: () => toast.error("Error", { description: "No se puede eliminar este rol del sistema." }),
  });

  const openRoleBuilder = (role?: any) => {
    if (role) {
      setEditingRole(role);
      setRoleFormName(role.name);
      setRoleFormDesc(role.description || "");
      setRoleFormPerms(role.permissions?.map((p: any) => (typeof p === "string" ? p : p.id)) || []);
    } else {
      setEditingRole(null);
      setRoleFormName("");
      setRoleFormDesc("");
      setRoleFormPerms([]);
    }
    setShowRoleBuilder(true);
  };

  const handleSaveRole = (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleFormName) return toast.warning("Requerido", { description: "El rol necesita un nombre." });

    if (editingRole) {
      updateRoleMutation.mutate({
        id: editingRole.id,
        payload: { name: roleFormName, description: roleFormDesc, permissions: roleFormPerms }
      });
    } else {
      createRoleMutation.mutate({
        name: roleFormName, description: roleFormDesc, permissions: roleFormPerms
      });
    }
  };

  return (
    <div className="space-y-8">
      {/* ROLE BUILDER UI */}
      {showRoleBuilder ? (
        <Card className="border border-primary/30 bg-card/40 backdrop-blur-md shadow-lg">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex gap-2 items-center text-lg font-bold"><Shield className="w-5 h-5 text-primary" /> {editingRole ? "Editar Rol" : "Crear Nuevo Rol"}</CardTitle>
              <CardDescription>Selecciona los permisos granulares para este rol.</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setShowRoleBuilder(false)}>Cancelar</Button>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveRole} className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Nombre del Rol</Label>
                  <Input value={roleFormName} onChange={e => setRoleFormName(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label>Descripción</Label>
                  <Input value={roleFormDesc} onChange={e => setRoleFormDesc(e.target.value)} />
                </div>
              </div>

              <div className="space-y-4">
                <Label>Permisos Granulares</Label>
                {loadingPerms ? <div className="text-xs">Cargando permisos...</div> : (
                  <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                    {Object.entries(
                      permissions?.reduce((acc: any, p: any) => {
                        (acc[p.module] = acc[p.module] || []).push(p);
                        return acc;
                      }, {}) || {}
                    ).map(([module, perms]: any) => (
                      <div key={module} className="border border-border/50 rounded-lg p-3 bg-card/50">
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-2 text-primary">{module}</h4>
                        <div className="space-y-2">
                          {perms.map((p: any) => (
                            <label key={p.id} className="flex items-start gap-2 text-sm cursor-pointer">
                              <input
                                type="checkbox"
                                checked={roleFormPerms.includes(p.id)}
                                onChange={(e) => {
                                  if (e.target.checked) setRoleFormPerms([...roleFormPerms, p.id]);
                                  else setRoleFormPerms(roleFormPerms.filter(id => id !== p.id));
                                }}
                                className="mt-1 rounded border-border text-primary focus:ring-primary w-3.5 h-3.5"
                              />
                              <span className="leading-tight">
                                <span className="block font-semibold">{p.action}</span>
                                <span className="block text-[10px] text-muted-foreground">{p.description}</span>
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Button type="submit" disabled={createRoleMutation.isPending || updateRoleMutation.isPending}>
                {editingRole ? "Guardar Cambios" : "Crear Rol"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex gap-2 items-center text-lg font-bold"><Shield className="w-5 h-5 text-primary" /> Roles Personalizados</CardTitle>
              <CardDescription>Crea o edita roles para asignar a los usuarios.</CardDescription>
            </div>
            <div className="flex gap-3 items-center">
              <Input placeholder="Buscar rol..." className="h-8 text-xs w-[200px]" value={searchRoles} onChange={e => setSearchRoles(e.target.value)} />
              <Button onClick={() => openRoleBuilder()} size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground">
                + Crear Rol
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {loadingRoles ? <div className="text-xs">Cargando roles...</div> :
                filteredRoles?.map((r: any) => (
                  <div key={r.id} className="border border-border/60 rounded-lg p-4 bg-card/40 flex flex-col justify-between hover:border-primary/40 transition-colors">
                    <div>
                      <div className="flex justify-between items-start">
                        <h4 className="font-bold">{r.name}</h4>
                        {r.is_system_default && <span className="text-[9px] uppercase font-bold bg-muted px-1.5 py-0.5 rounded text-muted-foreground">Sistema</span>}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 mb-3">{r.description}</p>
                      <div className="flex flex-wrap gap-1 mb-4">
                        <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                          {r.permissions?.length || 0} permisos
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => openRoleBuilder(r)}>Editar</Button>
                      {!r.is_system_default && (
                        <Button variant="destructive" size="sm" className="h-7 w-7 p-0" onClick={() => {
                          if (confirm("¿Estás seguro de eliminar este rol?")) {
                            deleteRoleMutation.mutate(r.id);
                          }
                        }}>
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))
              }
            </div>
          </CardContent>
        </Card>
      )}

      {/* EMPLOYEE DIRECTORY */}
      <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex gap-2 items-center text-lg font-bold"><Users className="w-5 h-5 text-indigo-400" /> Directorio de Empleados</CardTitle>
            <CardDescription>Supervisa a los empleados registrados y ajusta directamente sus roles.</CardDescription>
          </div>
          <Input placeholder="Buscar por nombre, email o departamento..." className="h-8 text-xs w-[300px]" value={searchUsers} onChange={e => setSearchUsers(e.target.value)} />
        </CardHeader>
        <CardContent>
          <div className="border border-border/60 rounded-lg overflow-x-auto bg-card/20 shadow-md max-h-[500px] overflow-y-auto">
            {loadingUsers ? <div className="text-xs text-muted-foreground p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" /> Cargando directorio...</div> :
              filteredUsers?.length === 0 ? <div className="text-sm text-muted-foreground p-10 text-center flex flex-col items-center gap-2"><Users className="w-8 h-8 text-muted-foreground/50" /> No se encontraron empleados.</div> :
              <table className="w-full text-sm text-left border-collapse">
                <thead className="bg-muted text-muted-foreground border-b border-border/60">
                  <tr>
                    <th className="p-4 font-semibold uppercase tracking-wider text-xs">Empleado</th>
                    <th className="p-4 font-semibold uppercase tracking-wider text-xs">Correo Electrónico</th>
                    <th className="p-4 font-semibold uppercase tracking-wider text-xs">Departamento</th>
                    <th className="p-4 font-semibold uppercase tracking-wider text-xs">Rol Asignado</th>
                    <th className="p-4 text-center font-semibold uppercase tracking-wider text-xs">Estado de Acceso</th>
                    <th className="p-4 text-right font-semibold uppercase tracking-wider text-xs">Modificar Nivel</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {filteredUsers?.map((u: any) => (
                    <tr key={u.id} className="hover:bg-muted/15 transition-colors">
                      <td className="p-4 font-bold text-foreground flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs border border-primary/20">
                          {u.full_name ? u.full_name.split(" ").map((n: string) => n[0]).join("").substring(0, 2) : "EM"}
                        </div>
                        {u.full_name}
                      </td>
                      <td className="p-4 text-muted-foreground text-xs font-mono">{u.email}</td>
                      <td className="p-4 text-muted-foreground">{u.department || "General"}</td>
                      <td className="p-4">
                        <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${u.role === "hr_admin" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                            u.role === "it_manager" ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" :
                              u.role === "finance_manager" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                                "bg-blue-500/10 text-blue-400 border-blue-500/20"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="p-4 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${u.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                          {u.is_active ? "Activo" : "Inactivo"}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <select
                          value={u.role}
                          onChange={(e) => changeUserRoleMutation.mutate({ userId: u.id, role: e.target.value })}
                          disabled={changeUserRoleMutation.isPending || loadingRoles}
                          className="text-xs rounded border border-border/80 bg-card px-2.5 py-1 text-foreground focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer"
                        >
                          {roles?.map((r: any) => (
                            <option key={r.id} value={r.id}>{r.name}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
