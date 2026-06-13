"use client";

import React, { DragEvent } from "react";
import { useBuilder, SchemaNode, generateId } from "./BuilderContext";
import { Toolbox } from "./Toolbox";
import { SettingsPanel } from "./SettingsPanel";
import { Topbar } from "./Topbar";
import { DynamicRenderer } from "../dynamic/DynamicRenderer";

function NodeWrapper({ node }: { node: SchemaNode }) {
  const { state, selectNode, addNode, moveNode } = useBuilder();
  const isSelected = state.selectedId === node.id;

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const dataString = e.dataTransfer.getData("application/builder-new-component");
    if (dataString) {
      try {
        const data = JSON.parse(dataString);
        const newNode: SchemaNode = {
          id: generateId(),
          type: data.type,
          props: data.props,
          children: data.type === "layout" || data.type === "page" ? [] : undefined,
        };
        addNode(node.id, newNode);
      } catch (err) {
        console.error("Error parsing drop data", err);
      }
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectNode(node.id);
  };

  // Convert SchemaNode to the format expected by DynamicRenderer
  const renderSchema = {
    ...node.props,
    type: node.type,
    children: node.children?.map(child => ({ ...child.props, type: child.type, id: child.id })),
  };

  // Temporarily overriding children to render NodeWrappers instead of raw DynamicRenderers
  if (node.type === "layout" || node.type === "page") {
    return (
      <div
        className={`relative border-2 p-4 min-h-[100px] transition-colors ${
          isSelected ? "border-blue-500" : "border-dashed border-gray-300 hover:border-gray-400"
        }`}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="absolute -top-3 left-2 bg-background px-1 text-xs text-muted-foreground">
          {node.type.toUpperCase()}
        </div>
        <div className={`flex ${node.props.direction === "row" ? "flex-row gap-6" : "flex-col gap-6"}`}>
          {node.children?.map((child) => (
            <div key={child.id} className={node.props.direction === "row" ? "flex-1" : "w-full"}>
              <NodeWrapper node={child} />
            </div>
          ))}
          {(!node.children || node.children.length === 0) && (
            <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground opacity-50">
              Arrastra componentes aquí
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`relative border-2 p-2 transition-colors ${
        isSelected ? "border-blue-500" : "border-transparent hover:border-gray-300 border-dashed"
      }`}
      onClick={handleClick}
    >
      <div className="pointer-events-none">
        <DynamicRenderer schema={renderSchema} />
      </div>
    </div>
  );
}

export function VisualEditor({ onSave }: { onSave?: (state: any) => void }) {
  const { state } = useBuilder();

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      <div className="flex w-full flex-col h-full">
        {/* Topbar for actions like Save, Undo, Redo */}
        <Topbar onSave={onSave} />
        
        <div className="flex flex-1 overflow-hidden">
          {/* Left sidebar: Toolbox */}
          <div className="w-64 border-r bg-card p-4 overflow-y-auto">
            <Toolbox />
          </div>

          {/* Main canvas area */}
          <div className="flex-1 overflow-y-auto p-8 bg-muted/30">
            <div className="mx-auto max-w-4xl bg-background shadow-sm min-h-[800px] p-8 border" onClick={() => {}}>
              <NodeWrapper node={state.schema} />
            </div>
          </div>

          {/* Right sidebar: Settings Panel */}
          <div className="w-80 border-l bg-card p-4 overflow-y-auto">
            <SettingsPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
