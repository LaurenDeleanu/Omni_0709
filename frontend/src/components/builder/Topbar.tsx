"use client";

import React from "react";
import { useBuilder } from "./BuilderContext";
import { Button } from "@/components/ui/button";
import { Save, Undo, Redo } from "lucide-react";

// Convert our internal SchemaNode tree into the JSON structure expected by the backend and DynamicRenderer
function convertToExportFormat(node: any): any {
  const result: any = {
    type: node.type,
    ...node.props,
  };
  
  if (node.children && node.children.length > 0) {
    result.children = node.children.map(convertToExportFormat);
  }
  
  return result;
}

export function Topbar({ onSave }: { onSave?: (state: any) => void }) {
  const { state, undo, redo, canUndo, canRedo } = useBuilder();

  return (
    <div className="flex items-center justify-between p-4 bg-background border-b h-16">
      <div className="flex items-center space-x-4">
        <h2 className="font-semibold text-lg">Visual Builder</h2>
        <div className="flex items-center space-x-1 border-l pl-4">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={undo}
            disabled={!canUndo}
          >
            <Undo className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={redo}
            disabled={!canRedo}
          >
            <Redo className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div>
        <Button 
          onClick={() => {
            if (onSave) {
              const exportableSchema = convertToExportFormat(state.schema);
              onSave(exportableSchema);
            }
          }}
          className="flex items-center space-x-2"
        >
          <Save className="h-4 w-4" />
          <span>Guardar Cambios</span>
        </Button>
      </div>
    </div>
  );
}
