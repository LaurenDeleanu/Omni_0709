"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RBACAPI, Role, Permission } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";

export default function RolesTab() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);

  const { data: roles, isLoading: rolesLoading } = useQuery({
    queryKey: ["rbacRoles"],
    queryFn: RBACAPI.getRoles,
  });

  const { data: permissions } = useQuery({
    queryKey: ["rbacPermissions"],
    queryFn: RBACAPI.getPermissions,
  });

  // Group permissions by module
  const permsByModule = permissions?.reduce((acc: Record<string, Permission[]>, perm: Permission) => {
    if (!acc[perm.module]) acc[perm.module] = [];
    acc[perm.module].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>) || {};

  const createMutation = useMutation({
    mutationFn: (data: { name: string, description: string, permission_ids: string[] }) => RBACAPI.createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbacRoles"] });
      toast.success("Rol creado");
      setIsModalOpen(false);
    },
    onError: (err: any) => toast.error("Error", { description: err.message })
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: string, payload: { name: string, description: string, permission_ids: string[] } }) => 
      RBACAPI.updateRole(data.id, data.payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbacRoles"] });
      toast.success("Rol actualizado");
      setIsModalOpen(false);
    },
    onError: (err: any) => toast.error("Error", { description: err.message })
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => RBACAPI.deleteRole(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbacRoles"] });
      toast.success("Rol eliminado");
    },
    onError: (err: any) => toast.error("Error al eliminar", { description: err.message })
  });

  const openCreate = () => {
    setEditingRole(null);
    setFormData({ name: "", description: "" });
    setSelectedPerms([]);
    setIsModalOpen(true);
  };

  const openEdit = (role: Role) => {
    setEditingRole(role);
    setFormData({ name: role.name, description: role.description || "" });
    setSelectedPerms(role.permissions.map(p => p.permission_id));
    setIsModalOpen(true);
  };

  const handleSave = () => {
    if (!formData.name) return toast.error("El nombre es requerido");
    
    if (editingRole) {
      updateMutation.mutate({ id: editingRole.id, payload: { ...formData, permission_ids: selectedPerms } });
    } else {
      createMutation.mutate({ ...formData, permission_ids: selectedPerms });
    }
  };

  const togglePermission = (permId: string) => {
    setSelectedPerms(prev => 
      prev.includes(permId) ? prev.filter(p => p !== permId) : [...prev, permId]
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
        <div>
          <h3 className="font-bold text-lg text-foreground">Global Role Builder (RBAC)</h3>
          <p className="text-sm text-muted-foreground">Crea roles personalizados y define sus permisos exactos en la plataforma.</p>
        </div>
        <Button onClick={openCreate} className="bg-primary hover:bg-primary/95 text-white">
          <Plus className="w-4 h-4 mr-2" /> Crear Nuevo Rol
        </Button>
      </div>
      
      <div className="border border-border/50 rounded-xl overflow-hidden">
        <div className="bg-muted/40 p-4 grid grid-cols-4 font-bold text-xs uppercase tracking-wider text-muted-foreground">
          <div className="col-span-1">Nombre del Rol</div>
          <div className="col-span-2">Descripción</div>
          <div className="col-span-1 text-right">Acciones</div>
        </div>
        <div className="divide-y divide-border/50">
          {rolesLoading ? (
            <div className="p-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : roles?.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No hay roles configurados.</div>
          ) : (
            roles?.map((r: Role) => (
              <div key={r.id} className="p-4 grid grid-cols-4 items-center hover:bg-muted/20 transition-colors">
                <div className="col-span-1 font-semibold flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    {r.name}
                    {r.is_system_default && <span className="px-1.5 py-0.5 rounded text-[10px] bg-primary/10 text-primary uppercase">Default</span>}
                  </div>
                  <span className="text-xs text-muted-foreground">{r.permissions.length} Permisos</span>
                </div>
                <div className="col-span-2 text-sm text-muted-foreground">{r.description || "Sin descripción"}</div>
                <div className="col-span-1 text-right flex justify-end gap-2">
                  <Button variant="outline" size="icon" className="w-8 h-8" onClick={() => openEdit(r)}>
                    <Pencil className="w-4 h-4" />
                  </Button>
                  {!r.is_system_default && (
                    <Button variant="outline" size="icon" className="w-8 h-8 text-destructive hover:bg-destructive/10" onClick={() => deleteMutation.mutate(r.id)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[700px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRole ? "Editar Rol" : "Crear Nuevo Rol"}</DialogTitle>
            <DialogDescription>Define el nombre y los permisos de acceso para este rol.</DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre del Rol</Label>
                <Input 
                  value={formData.name} 
                  onChange={(e) => setFormData(p => ({ ...p, name: e.target.value }))}
                  placeholder="Ej: IT Support Junior"
                />
              </div>
              <div className="space-y-2">
                <Label>Descripción</Label>
                <Input 
                  value={formData.description} 
                  onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder="Descripción corta"
                />
              </div>
            </div>

            <div className="space-y-4">
              <Label className="text-base">Matriz de Permisos</Label>
              <div className="grid gap-4">
                {Object.entries(permsByModule).map(([module, perms]: [string, any]) => (
                  <div key={module} className="border border-border rounded-lg p-4 bg-muted/10">
                    <h4 className="font-semibold text-sm uppercase text-muted-foreground mb-3">{module}</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {(perms as Permission[]).map((p: Permission) => (
                        <div key={p.id} className="flex items-start space-x-2">
                          <Checkbox 
                            id={p.id} 
                            checked={selectedPerms.includes(p.id)}
                            onCheckedChange={() => togglePermission(p.id)}
                          />
                          <div className="grid gap-1.5 leading-none">
                            <label
                              htmlFor={p.id}
                              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                            >
                              {p.action}
                            </label>
                            <p className="text-[10px] text-muted-foreground line-clamp-1">{p.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? "Guardando..." : "Guardar Rol"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
