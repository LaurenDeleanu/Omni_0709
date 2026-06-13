"use client";

import React, { createContext, useContext, useState, useCallback, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
export interface SchemaNode {
  id: string;
  type: "layout" | "form" | "table" | "text" | "card" | "page";
  props: Record<string, any>;
  children?: SchemaNode[];
}

export interface BuilderState {
  schema: SchemaNode;
  selectedId: string | null;
}

interface BuilderContextValue {
  state: BuilderState;
  selectNode: (id: string | null) => void;
  updateNodeProps: (id: string, props: Record<string, any>) => void;
  addNode: (parentId: string, node: SchemaNode) => void;
  removeNode: (id: string) => void;
  moveNode: (nodeId: string, newParentId: string, index: number) => void;
  getSelectedNode: () => SchemaNode | null;
  setSchema: (schema: SchemaNode) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

const BuilderContext = createContext<BuilderContextValue | null>(null);

export function useBuilder() {
  const ctx = useContext(BuilderContext);
  if (!ctx) throw new Error("useBuilder must be used within BuilderProvider");
  return ctx;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
let _idCounter = 0;
export function generateId(): string {
  return `node_${Date.now()}_${++_idCounter}`;
}

function findNode(root: SchemaNode, id: string): SchemaNode | null {
  if (root.id === id) return root;
  for (const child of root.children ?? []) {
    const found = findNode(child, id);
    if (found) return found;
  }
  return null;
}

function cloneSchema(node: SchemaNode): SchemaNode {
  return JSON.parse(JSON.stringify(node));
}

function removeNodeFromTree(root: SchemaNode, id: string): boolean {
  if (!root.children) return false;
  const idx = root.children.findIndex((c) => c.id === id);
  if (idx >= 0) {
    root.children.splice(idx, 1);
    return true;
  }
  for (const child of root.children) {
    if (removeNodeFromTree(child, id)) return true;
  }
  return false;
}

// ─── Provider ─────────────────────────────────────────────────────────────────
const MAX_HISTORY = 50;

export function BuilderProvider({
  children,
  initialSchema,
}: {
  children: React.ReactNode;
  initialSchema: SchemaNode;
}) {
  const [state, setState] = useState<BuilderState>({
    schema: initialSchema,
    selectedId: null,
  });

  // History for undo/redo
  const historyRef = useRef<SchemaNode[]>([cloneSchema(initialSchema)]);
  const historyIdxRef = useRef(0);

  const pushHistory = useCallback((schema: SchemaNode) => {
    const h = historyRef.current;
    const idx = historyIdxRef.current;
    // Discard any future states
    historyRef.current = h.slice(0, idx + 1);
    historyRef.current.push(cloneSchema(schema));
    if (historyRef.current.length > MAX_HISTORY) {
      historyRef.current.shift();
    } else {
      historyIdxRef.current = historyRef.current.length - 1;
    }
  }, []);

  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const refreshUndoRedo = useCallback(() => {
    setCanUndo(historyIdxRef.current > 0);
    setCanRedo(historyIdxRef.current < historyRef.current.length - 1);
  }, []);

  const applySchema = useCallback(
    (schema: SchemaNode, recordHistory = true) => {
      setState((prev) => ({ ...prev, schema }));
      if (recordHistory) pushHistory(schema);
      refreshUndoRedo();
    },
    [pushHistory, refreshUndoRedo]
  );

  const selectNode = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, selectedId: id }));
  }, []);

  const updateNodeProps = useCallback(
    (id: string, props: Record<string, any>) => {
      setState((prev) => {
        const schema = cloneSchema(prev.schema);
        const node = findNode(schema, id);
        if (node) {
          node.props = { ...node.props, ...props };
        }
        pushHistory(schema);
        refreshUndoRedo();
        return { ...prev, schema };
      });
    },
    [pushHistory, refreshUndoRedo]
  );

  const addNode = useCallback(
    (parentId: string, node: SchemaNode) => {
      setState((prev) => {
        const schema = cloneSchema(prev.schema);
        const parent = findNode(schema, parentId);
        if (parent) {
          if (!parent.children) parent.children = [];
          parent.children.push(node);
        }
        pushHistory(schema);
        refreshUndoRedo();
        return { ...prev, schema, selectedId: node.id };
      });
    },
    [pushHistory, refreshUndoRedo]
  );

  const removeNode = useCallback(
    (id: string) => {
      setState((prev) => {
        const schema = cloneSchema(prev.schema);
        removeNodeFromTree(schema, id);
        pushHistory(schema);
        refreshUndoRedo();
        return { ...prev, schema, selectedId: prev.selectedId === id ? null : prev.selectedId };
      });
    },
    [pushHistory, refreshUndoRedo]
  );

  const moveNode = useCallback(
    (nodeId: string, newParentId: string, index: number) => {
      setState((prev) => {
        const schema = cloneSchema(prev.schema);
        const node = findNode(schema, nodeId);
        if (!node) return prev;
        const nodeCopy = cloneSchema(node);
        removeNodeFromTree(schema, nodeId);
        const newParent = findNode(schema, newParentId);
        if (newParent) {
          if (!newParent.children) newParent.children = [];
          newParent.children.splice(index, 0, nodeCopy);
        }
        pushHistory(schema);
        refreshUndoRedo();
        return { ...prev, schema };
      });
    },
    [pushHistory, refreshUndoRedo]
  );

  const getSelectedNode = useCallback((): SchemaNode | null => {
    if (!state.selectedId) return null;
    return findNode(state.schema, state.selectedId);
  }, [state.schema, state.selectedId]);

  const setSchema = useCallback(
    (schema: SchemaNode) => {
      applySchema(schema, true);
    },
    [applySchema]
  );

  const undo = useCallback(() => {
    if (historyIdxRef.current > 0) {
      historyIdxRef.current--;
      const schema = cloneSchema(historyRef.current[historyIdxRef.current]);
      setState((prev) => ({ ...prev, schema }));
      refreshUndoRedo();
    }
  }, [refreshUndoRedo]);

  const redo = useCallback(() => {
    if (historyIdxRef.current < historyRef.current.length - 1) {
      historyIdxRef.current++;
      const schema = cloneSchema(historyRef.current[historyIdxRef.current]);
      setState((prev) => ({ ...prev, schema }));
      refreshUndoRedo();
    }
  }, [refreshUndoRedo]);

  return (
    <BuilderContext.Provider
      value={{
        state,
        selectNode,
        updateNodeProps,
        addNode,
        removeNode,
        moveNode,
        getSelectedNode,
        setSchema,
        undo,
        redo,
        canUndo,
        canRedo,
      }}
    >
      {children}
    </BuilderContext.Provider>
  );
}
