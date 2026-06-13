"use client";

import React from "react";
import { useNode } from "@craftjs/core";
import { DynamicForm, FormSchema } from "../dynamic/DynamicForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table as UiTable, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const CraftContainer = ({ children, padding = 20, direction = "column" }: { children?: React.ReactNode, padding?: number, direction?: "row" | "column" }) => {
  const { connectors: { connect, drag } } = useNode();
  return (
    <div 
      ref={(ref) => { if (ref) connect(drag(ref)); }} 
      style={{ padding: `${padding}px` }}
      className={`border border-dashed border-gray-300 min-h-[100px] flex ${direction === 'row' ? 'flex-row gap-4' : 'flex-col gap-4'}`}
    >
      {children}
    </div>
  );
};

export const CraftContainerSettings = () => {
  const { actions: { setProp }, padding, direction } = useNode((node) => ({
    padding: node.data.props.padding,
    direction: node.data.props.direction,
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Padding</Label>
        <Input 
          type="number" 
          value={padding} 
          onChange={(e) => setProp((props: any) => props.padding = parseInt(e.target.value, 10))} 
        />
      </div>
      <div className="space-y-2">
        <Label>Dirección</Label>
        <select 
          value={direction} 
          onChange={(e) => setProp((props: any) => props.direction = e.target.value)}
          className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="column">Columna</option>
          <option value="row">Fila</option>
        </select>
      </div>
    </div>
  );
};

CraftContainer.craft = {
  displayName: "Contenedor",
  props: { padding: 20, direction: "column" },
  related: { settings: CraftContainerSettings }
};

export const CraftText = ({ text, fontSize = 16 }: { text: string, fontSize?: number }) => {
  const { connectors: { connect, drag } } = useNode();
  return (
    <div ref={(ref) => { if (ref) connect(drag(ref)); }}>
      <p style={{ fontSize: `${fontSize}px` }}>{text}</p>
    </div>
  );
};

export const CraftTextSettings = () => {
  const { actions: { setProp }, text, fontSize } = useNode((node) => ({
    text: node.data.props.text,
    fontSize: node.data.props.fontSize,
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Texto</Label>
        <Input type="text" value={text} onChange={(e) => setProp((props: any) => props.text = e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label>Tamaño de Fuente (px)</Label>
        <Input type="number" value={fontSize} onChange={(e) => setProp((props: any) => props.fontSize = parseInt(e.target.value, 10))} />
      </div>
    </div>
  );
};

CraftText.craft = {
  displayName: "Texto",
  props: { text: "Texto de ejemplo", fontSize: 16 },
  related: { settings: CraftTextSettings }
};

export const CraftForm = ({ title, submitLabel }: { title: string, submitLabel: string }) => {
  const { connectors: { connect, drag } } = useNode();
  const schema: FormSchema = {
    type: "form",
    title,
    submitLabel,
    fields: [{ name: "ejemplo", label: "Campo Ejemplo", type: "text" }]
  };

  return (
    <div ref={(ref) => { if (ref) connect(drag(ref)); }} className="w-full">
      <Card>
        <CardContent className="pt-6 pointer-events-none">
          <DynamicForm schema={schema} onSubmit={() => {}} />
        </CardContent>
      </Card>
    </div>
  );
};

export const CraftFormSettings = () => {
  const { actions: { setProp }, title, submitLabel } = useNode((node) => ({
    title: node.data.props.title,
    submitLabel: node.data.props.submitLabel,
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Título del Formulario</Label>
        <Input type="text" value={title} onChange={(e) => setProp((props: any) => props.title = e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label>Texto del Botón</Label>
        <Input type="text" value={submitLabel} onChange={(e) => setProp((props: any) => props.submitLabel = e.target.value)} />
      </div>
    </div>
  );
};

CraftForm.craft = {
  displayName: "Formulario",
  props: { title: "Nuevo Formulario", submitLabel: "Enviar" },
  related: { settings: CraftFormSettings }
};

export const CraftTable = ({ title }: { title: string }) => {
  const { connectors: { connect, drag } } = useNode();
  
  return (
    <div ref={(ref) => { if (ref) connect(drag(ref)); }} className="w-full">
      <Card>
        {title && <CardHeader><CardTitle>{title}</CardTitle></CardHeader>}
        <CardContent className="pointer-events-none">
           <UiTable>
             <TableHeader>
               <TableRow>
                 <TableHead>Columna 1</TableHead>
                 <TableHead>Columna 2</TableHead>
               </TableRow>
             </TableHeader>
             <TableBody>
               <TableRow>
                 <TableCell>Dato 1</TableCell>
                 <TableCell>Dato 2</TableCell>
               </TableRow>
             </TableBody>
           </UiTable>
        </CardContent>
      </Card>
    </div>
  );
};

export const CraftTableSettings = () => {
  const { actions: { setProp }, title } = useNode((node) => ({
    title: node.data.props.title,
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Título de la Tabla</Label>
        <Input type="text" value={title} onChange={(e) => setProp((props: any) => props.title = e.target.value)} />
      </div>
    </div>
  );
};

CraftTable.craft = {
  displayName: "Tabla",
  props: { title: "Nueva Tabla" },
  related: { settings: CraftTableSettings }
};
