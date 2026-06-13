"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SalesAPI, Client } from "@/lib/api";
import { Plus, Search, Building, Mail, Phone, Globe, Download, Edit2, Trash2 } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState, useMemo } from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ClientsDirectory() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedClientForEdit, setSelectedClientForEdit] = useState<Client | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: clients, isLoading } = useQuery<Client[]>({
    queryKey: ["salesClients"],
    queryFn: SalesAPI.getClients,
  });

  const createClientMutation = useMutation<Client, Error, Partial<Client>>({
    mutationFn: SalesAPI.createClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesClients"] });
      setIsModalOpen(false);
      toast.success("Cliente creado con éxito");
    },
  });

  const updateClientMutation = useMutation<Client, Error, { id: string; data: Partial<Client> }>({
    mutationFn: ({ id, data }) => SalesAPI.updateClient(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesClients"] });
      setIsEditModalOpen(false);
      toast.success("Cliente actualizado");
    },
  });

  const deleteClientMutation = useMutation<any, Error, string>({
    mutationFn: (id: string) => SalesAPI.deleteClient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesClients"] });
      setIsEditModalOpen(false);
      toast.success("Cliente eliminado");
    },
  });

  const handleCreateClient = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createClientMutation.mutate({
      company_name: formData.get("company_name") as string,
      industry: formData.get("industry") as string,
      website: formData.get("website") as string,
      primary_contact_name: formData.get("primary_contact_name") as string,
      primary_contact_email: formData.get("primary_contact_email") as string,
      primary_contact_phone: formData.get("primary_contact_phone") as string,
    });
  };

  const handleEditClient = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedClientForEdit) return;
    const formData = new FormData(e.currentTarget);
    updateClientMutation.mutate({
      id: selectedClientForEdit.id,
      data: {
        company_name: formData.get("company_name") as string,
        industry: formData.get("industry") as string,
        website: formData.get("website") as string,
        primary_contact_name: formData.get("primary_contact_name") as string,
        primary_contact_email: formData.get("primary_contact_email") as string,
        primary_contact_phone: formData.get("primary_contact_phone") as string,
      }
    });
  };

  const handleDeleteClient = (id: string) => {
    if (confirm("¿Estás seguro de que deseas eliminar este cliente? Se borrarán sus datos permanentemente.")) {
      deleteClientMutation.mutate(id);
    }
  };

  const filteredClients = useMemo(() => {
    if (!clients) return [];
    if (!searchQuery) return clients;
    const lower = searchQuery.toLowerCase();
    return clients.filter((c: Client) => 
      c.company_name.toLowerCase().includes(lower) || 
      (c.primary_contact_name && c.primary_contact_name.toLowerCase().includes(lower)) ||
      (c.industry && c.industry.toLowerCase().includes(lower))
    );
  }, [clients, searchQuery]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-xl px-6 py-4 flex flex-col md:flex-row md:items-center justify-between shrink-0 gap-4">
        <div>
          <h1 className="text-2xl font-bold">CRM & Ventas</h1>
          <div className="flex items-center gap-6 mt-2">
            <Link href="/dashboard/sales" className="text-sm font-medium text-muted-foreground hover:text-foreground pb-1">
              Pipeline (Deals)
            </Link>
            <Link href="/dashboard/sales/clients" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
              Directorio de Clientes
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative hidden md:block">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Buscar cliente..." 
              className="pl-9 w-64 bg-background"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <Button variant="outline" className="gap-2 hidden md:flex">
            <Download className="h-4 w-4" />
            Exportar
          </Button>

          <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogTrigger render={<Button className="gap-2" />}>
                <Plus className="h-4 w-4" />
                Nuevo Cliente
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>Añadir Cliente</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateClient} className="space-y-6 py-4">
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-primary uppercase tracking-wider">Detalles de Empresa</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="company_name">Nombre de Empresa</Label>
                      <Input id="company_name" name="company_name" required placeholder="Ej: Acme Corp" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="industry">Industria</Label>
                      <Input id="industry" name="industry" placeholder="Ej: Tecnología" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="website">Sitio Web</Label>
                    <Input id="website" name="website" placeholder="https://..." />
                  </div>
                </div>

                <div className="space-y-4 pt-2 border-t border-border">
                  <h4 className="text-sm font-semibold text-primary uppercase tracking-wider">Contacto Principal</h4>
                  <div className="space-y-2">
                    <Label htmlFor="primary_contact_name">Nombre Completo</Label>
                    <Input id="primary_contact_name" name="primary_contact_name" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="primary_contact_email">Email</Label>
                      <Input id="primary_contact_email" name="primary_contact_email" type="email" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="primary_contact_phone">Teléfono</Label>
                      <Input id="primary_contact_phone" name="primary_contact_phone" />
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={createClientMutation.isPending}>
                    {createClientMutation.isPending ? "Guardando..." : "Guardar Cliente"}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Directory Area */}
      <div className="flex-1 overflow-auto p-6 bg-muted/10">
        <div className="max-w-6xl mx-auto">
          <div className="bg-card rounded-xl border border-border overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Empresa</th>
                    <th className="px-6 py-4 font-medium">Contacto Principal</th>
                    <th className="px-6 py-4 font-medium">Información de Contacto</th>
                    <th className="px-6 py-4 font-medium">Industria</th>
                    <th className="px-6 py-4 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                        Cargando directorio...
                      </td>
                    </tr>
                  ) : filteredClients.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center">
                        <div className="flex flex-col items-center justify-center text-muted-foreground">
                          <Building className="w-12 h-12 mb-4 opacity-20" />
                          <p className="text-lg font-medium text-foreground">No hay clientes encontrados</p>
                          <p className="text-sm mt-1">Añade tu primer cliente o cambia tus filtros de búsqueda.</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredClients.map((client: Client) => (
                      <tr key={client.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold">
                              {client.company_name.substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-semibold text-foreground">{client.company_name}</div>
                              {client.website && (
                                <a href={client.website.startsWith('http') ? client.website : `https://${client.website}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:underline flex items-center gap-1 mt-0.5">
                                  <Globe className="w-3 h-3" />
                                  {client.website.replace(/^https?:\/\//, '')}
                                </a>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-medium">{client.primary_contact_name || "—"}</div>
                        </td>
                        <td className="px-6 py-4 space-y-1">
                          {client.primary_contact_email && (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Mail className="w-3.5 h-3.5" />
                              <a href={`mailto:${client.primary_contact_email}`} className="hover:text-primary transition-colors">{client.primary_contact_email}</a>
                            </div>
                          )}
                          {client.primary_contact_phone && (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Phone className="w-3.5 h-3.5" />
                              <a href={`tel:${client.primary_contact_phone}`} className="hover:text-primary transition-colors">{client.primary_contact_phone}</a>
                            </div>
                          )}
                          {!client.primary_contact_email && !client.primary_contact_phone && "—"}
                        </td>
                        <td className="px-6 py-4">
                          {client.industry ? (
                            <span className="bg-muted px-2.5 py-1 rounded-md text-xs font-medium border border-border">
                              {client.industry}
                            </span>
                          ) : "—"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-primary hover:text-primary/80"
                            onClick={() => {
                              setSelectedClientForEdit(client);
                              setIsEditModalOpen(true);
                            }}
                          >
                            Editar / Ver
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* DIALOG: EDIT/DELETE CLIENT */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Editar Cliente</DialogTitle>
          </DialogHeader>
          {selectedClientForEdit && (
            <form onSubmit={handleEditClient} className="space-y-6 py-4">
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-primary uppercase tracking-wider">Detalles de Empresa</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit-company_name">Nombre de Empresa</Label>
                    <Input id="edit-company_name" name="company_name" defaultValue={selectedClientForEdit.company_name} required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-industry">Industria</Label>
                    <Input id="edit-industry" name="industry" defaultValue={selectedClientForEdit.industry} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-website">Sitio Web</Label>
                  <Input id="edit-website" name="website" defaultValue={selectedClientForEdit.website} />
                </div>
              </div>

              <div className="space-y-4 pt-2 border-t border-border">
                <h4 className="text-sm font-semibold text-primary uppercase tracking-wider">Contacto Principal</h4>
                <div className="space-y-2">
                  <Label htmlFor="edit-primary_contact_name">Nombre Completo</Label>
                  <Input id="edit-primary_contact_name" name="primary_contact_name" defaultValue={selectedClientForEdit.primary_contact_name} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit-primary_contact_email">Email</Label>
                    <Input id="edit-primary_contact_email" name="primary_contact_email" type="email" defaultValue={selectedClientForEdit.primary_contact_email} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-primary_contact_phone">Teléfono</Label>
                    <Input id="edit-primary_contact_phone" name="primary_contact_phone" defaultValue={selectedClientForEdit.primary_contact_phone} />
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-between gap-2 border-t border-border mt-4">
                <Button type="button" variant="destructive" onClick={() => handleDeleteClient(selectedClientForEdit.id)} disabled={deleteClientMutation.isPending}>
                  Eliminar Cliente
                </Button>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsEditModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={updateClientMutation.isPending}>
                    {updateClientMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                  </Button>
                </div>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
