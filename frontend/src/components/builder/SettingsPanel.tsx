"use client";

import React from "react";
import { useBuilder } from "./BuilderContext";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Trash } from "lucide-react";

export function SettingsPanel() {
  const { getSelectedNode, updateNodeProps, removeNode } = useBuilder();
  const selected = getSelectedNode();

  if (!selected) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm text-center">
        Selecciona un componente para editar sus propiedades.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b pb-2">
        <h3 className="font-semibold text-sm uppercase tracking-wider">{selected.type} Settings</h3>
        {selected.id !== "root" && (
          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => removeNode(selected.id)}>
            <Trash className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      <div className="space-y-4">
        {selected.type === "layout" && (
          <div className="space-y-2">
            <Label>Dirección</Label>
            <select 
              value={selected.props.direction || "column"} 
              onChange={(e) => updateNodeProps(selected.id, { direction: e.target.value })}
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="column">Columna</option>
              <option value="row">Fila</option>
            </select>
          </div>
        )}

        {selected.type === "text" && (
          <>
            <div className="space-y-2">
              <Label>Texto</Label>
              <Input 
                type="text" 
                value={selected.props.text || ""} 
                onChange={(e) => updateNodeProps(selected.id, { text: e.target.value })} 
              />
            </div>
            <div className="space-y-2">
              <Label>Tamaño de fuente (px)</Label>
              <Input 
                type="number" 
                value={selected.props.fontSize || 16} 
                onChange={(e) => updateNodeProps(selected.id, { fontSize: parseInt(e.target.value, 10) })} 
              />
            </div>
          </>
        )}

        {selected.type === "form" && (
          <>
            <div className="space-y-2">
              <Label>Título del Formulario</Label>
              <Input 
                type="text" 
                value={selected.props.title || ""} 
                onChange={(e) => updateNodeProps(selected.id, { title: e.target.value })} 
              />
            </div>
            <div className="space-y-2">
              <Label>Texto del Botón</Label>
              <Input 
                type="text" 
                value={selected.props.submitLabel || ""} 
                onChange={(e) => updateNodeProps(selected.id, { submitLabel: e.target.value })} 
              />
            </div>
          </>
        )}

        {selected.type === "table" && (
          <div className="space-y-2">
            <Label>Título de la Tabla</Label>
            <Input 
              type="text" 
              value={selected.props.title || ""} 
              onChange={(e) => updateNodeProps(selected.id, { title: e.target.value })} 
            />
          </div>
        )}

        {selected.type === "page" && (
          <>
            <div className="space-y-2">
              <Label>Título de la Página</Label>
              <Input 
                type="text" 
                value={selected.props.title || ""} 
                onChange={(e) => updateNodeProps(selected.id, { title: e.target.value })} 
              />
            </div>
            <div className="space-y-2">
              <Label>Descripción</Label>
              <Input 
                type="text" 
                value={selected.props.description || ""} 
                onChange={(e) => updateNodeProps(selected.id, { description: e.target.value })} 
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
