"use client";

import React from "react";
import { useBuilder, generateId, SchemaNode } from "./BuilderContext";
import { Button } from "@/components/ui/button";
import { Type, LayoutGrid, FormInput, Table2, CreditCard } from "lucide-react";

const TOOLBOX_ITEMS: { type: SchemaNode["type"]; label: string; icon: React.ReactNode; defaultProps: Record<string, any> }[] = [
  {
    type: "layout",
    label: "Layout",
    icon: <LayoutGrid className="h-5 w-5" />,
    defaultProps: { direction: "column", title: "" },
  },
  {
    type: "text",
    label: "Texto",
    icon: <Type className="h-5 w-5" />,
    defaultProps: { text: "Texto de ejemplo", fontSize: 16 },
  },
  {
    type: "form",
    label: "Formulario",
    icon: <FormInput className="h-5 w-5" />,
    defaultProps: {
      title: "Nuevo Formulario",
      submitLabel: "Enviar",
      fields: [{ name: "campo1", label: "Campo 1", type: "text", required: false }],
    },
  },
  {
    type: "table",
    label: "Tabla",
    icon: <Table2 className="h-5 w-5" />,
    defaultProps: {
      title: "Nueva Tabla",
      columns: [
        { key: "col1", label: "Columna 1" },
        { key: "col2", label: "Columna 2" },
      ],
      data: [{ col1: "Dato 1", col2: "Dato 2" }],
    },
  },
  {
    type: "card",
    label: "Tarjeta",
    icon: <CreditCard className="h-5 w-5" />,
    defaultProps: { title: "Tarjeta", content: "Contenido de la tarjeta" },
  },
];

export function Toolbox() {
  const { addNode, state } = useBuilder();

  const handleAdd = (item: (typeof TOOLBOX_ITEMS)[0]) => {
    const newNode: SchemaNode = {
      id: generateId(),
      type: item.type,
      props: { ...item.defaultProps },
      children: item.type === "layout" ? [] : undefined,
    };
    // Add to root or selected layout
    const parentId = state.schema.id;
    addNode(parentId, newNode);
  };

  const handleDragStart = (e: React.DragEvent, item: (typeof TOOLBOX_ITEMS)[0]) => {
    e.dataTransfer.setData(
      "application/builder-new-component",
      JSON.stringify({ type: item.type, props: item.defaultProps })
    );
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm text-muted-foreground mb-4 uppercase tracking-wider">
        Componentes
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {TOOLBOX_ITEMS.map((item) => (
          <Button
            key={item.type}
            variant="outline"
            className="flex flex-col items-center justify-center h-20 gap-2 cursor-grab active:cursor-grabbing"
            draggable
            onDragStart={(e) => handleDragStart(e, item)}
            onClick={() => handleAdd(item)}
          >
            {item.icon}
            <span className="text-xs">{item.label}</span>
          </Button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Arrastra al canvas o haz clic para añadir al contenedor raíz.
      </p>
    </div>
  );
}
