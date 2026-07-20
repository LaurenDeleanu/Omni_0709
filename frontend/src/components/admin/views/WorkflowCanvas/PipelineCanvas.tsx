"use client";
import React, { useCallback, useEffect, useState } from "react";
import { 
  ReactFlow, 
  Background, 
  Controls, 
  Node, 
  Edge, 
  addEdge, 
  applyNodeChanges, 
  applyEdgeChanges, 
  Connection, 
  NodeChange, 
  EdgeChange, 
  Position 
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import StartNode from "./nodes/StartNode";
import EndNode from "./nodes/EndNode";
import MessageNode from "./nodes/MessageNode";
import LogicNode from "./nodes/LogicNode";
import AINode from "./nodes/AINode";
import ActionNode from "./nodes/ActionNode";
import CommerceNode from "./nodes/CommerceNode";
import PowerAutomateNode from "./nodes/PowerAutomateNode";

const nodeTypes = {
  welcome: StartNode,
  completed: EndNode,
  messageNode: MessageNode,
  logicNode: LogicNode,
  aiNode: AINode,
  actionNode: ActionNode,
  commerceNode: CommerceNode,
  powerAutomateNode: PowerAutomateNode,
};

export default function PipelineCanvas({
  steps,
  workflowId,
  onEdit,
  fetchSteps,
  onSaveStep,
  canvasNodes,
  setCanvasNodes,
  canvasEdges,
  setCanvasEdges
}: {
  steps: any[];
  workflowId: string;
  onEdit: (step: any) => void;
  fetchSteps: () => void;
  onSaveStep: (stepId: string, updatedData: Partial<any>) => Promise<void>;
  canvasNodes: Node[];
  setCanvasNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  canvasEdges: Edge[];
  setCanvasEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
}) {
  // Sync DB steps with React Flow nodes & edges
  useEffect(() => {
    // 1. Calculate relative depth of steps for grid positioning if they lack custom coordinate attributes
    const branchDepth: Record<string, number> = {};
    steps.forEach(s => branchDepth[s.id] = 0);
    steps.forEach(step => {
      try { 
        const c = typeof step.config === "string" ? JSON.parse(step.config) : step.config;
        if (c.branches && Array.isArray(c.branches)) {
          c.branches.forEach((b: any) => {
            const target = steps.find(s => s.id === b.goToStepId || s.order === b.goToStepOrder);
            if (target) {
              branchDepth[target.id] = Math.max(branchDepth[target.id], branchDepth[step.id] + 1);
            }
          });
        }
      } catch {}
    });

    const newNodes: Node[] = steps.map((s, i) => {
      let config: any = {};
      try { 
        config = typeof s.config === "string" ? JSON.parse(s.config) : s.config || {}; 
      } catch {}
      
      // Classify step type to match custom styled react-flow nodes
      let type = "messageNode";
      if (["WELCOME", "WEBHOOK_TRIGGER", "SCHEDULE_TRIGGER"].includes(s.type)) type = "welcome";
      else if (s.type === "COMPLETED") type = "completed";
      else if (["CONDITION", "AB_TEST", "PARALLEL_SPLIT", "MERGE", "LOOP", "APPROVAL_GATE"].includes(s.type)) type = "logicNode";
      else if (["AI_RESPONDER", "AUTONOMOUS_AGENT", "AI_DECISION", "SUB_AGENT"].includes(s.type)) type = "aiNode";
      else if (["API_CALL", "CREATE_LEAD", "CALL_WORKFLOW", "HUMAN_TAKEOVER", "CRM_ACTION", "DATA_TRANSFORM", "CODE_GENERATE", "GIT_COMMIT", "NOTIFICATION"].includes(s.type)) type = "actionNode";
      else if (s.type === "POWER_AUTOMATE") type = "powerAutomateNode";
      else if (["SHOW_PRODUCTS", "ADD_TO_CART", "CHECKOUT", "BOOKING", "PAYMENT"].includes(s.type)) type = "commerceNode";

      const depthX = branchDepth[s.id] || 0;
      const defaultX = 100 + (depthX * 380);
      const defaultY = i * 280 + 50;

      return {
        id: s.id,
        type,
        position: config.position || { x: defaultX, y: defaultY },
        data: { 
          label: s.label || s.name, 
          type: s.type, 
          config,
          onEdit: () => onEdit(s),
        }
      };
    });

    const newEdges: Edge[] = [];
    
    // Connect visual nodes sequentially & conditionally
    steps.forEach((s, i) => {
      let config: any = {};
      try { 
        config = typeof s.config === "string" ? JSON.parse(s.config) : s.config || {}; 
      } catch {}

      // A. Linear Connection routing
      if (config.nextStepId && config.nextStepId !== false) {
        newEdges.push({
          id: `edge-${s.id}-${config.nextStepId}`,
          source: s.id,
          sourceHandle: "default",
          target: config.nextStepId,
          type: "smoothstep",
          animated: true,
          style: { stroke: "#6366f1", strokeWidth: 2 }
        });
      } else if (config.nextStepId === false) {
        // Disconnected
      } else if (i < steps.length - 1 && s.type !== "HUMAN_TAKEOVER" && s.type !== "COMPLETED") {
        newEdges.push({
          id: `edge-${s.id}-${steps[i+1].id}`,
          source: s.id,
          sourceHandle: "default",
          target: steps[i+1].id,
          type: "smoothstep",
          animated: true,
          style: { stroke: "#6366f1", strokeWidth: 2 }
        });
      }

      // B. Conditional branching rules
      if (config.branches && config.branches.length > 0) {
        ((config.branches || []) as any[]).forEach((branch: any, idx: number) => {
          const targetStep = branch.goToStepId 
            ? steps.find(st => st.id === branch.goToStepId)
            : steps.find(st => st.order === branch.goToStepOrder);
            
          if (targetStep) {
            let sourceHandle = `branch-${idx}`;
            
            // Connect options handle directly to option badge if CHOICE_LIST
            if (s.type === "CHOICE_LIST") {
              const matchedIdx = config.options?.findIndex(
                (o: string) => o.toLowerCase() === (branch.match || "").toLowerCase()
              );
              if (matchedIdx !== undefined && matchedIdx !== -1) {
                sourceHandle = `option-${matchedIdx}`;
              }
            }

            newEdges.push({
              id: `branch-edge-${s.id}-${targetStep.id}-${idx}`,
              source: s.id,
              sourceHandle,
              target: targetStep.id,
              type: "smoothstep",
              animated: true,
              label: branch.match || `Regla ${idx + 1}`,
              labelStyle: { fill: "#f59e0b", fontWeight: "bold", fontSize: 9 },
              style: { stroke: "#f59e0b", strokeWidth: 2, strokeDasharray: "4,4" }
            });
          }
        });
      }

      // C. AB Testing Routing edges
      if (s.type === "AB_TEST") {
        if (config.branchAStepId) {
          newEdges.push({
            id: `ab-edge-A-${s.id}-${config.branchAStepId}`,
            source: s.id,
            sourceHandle: "ab-A",
            target: config.branchAStepId,
            type: "smoothstep",
            animated: true,
            label: `Rama A (${config.branchAWeight ?? 50}%)`,
            labelStyle: { fill: "#f472b6", fontWeight: "bold", fontSize: 9 },
            style: { stroke: "#f472b6", strokeWidth: 2, strokeDasharray: "4,4" }
          });
        }
        if (config.branchBStepId) {
          newEdges.push({
            id: `ab-edge-B-${s.id}-${config.branchBStepId}`,
            source: s.id,
            sourceHandle: "ab-B",
            target: config.branchBStepId,
            type: "smoothstep",
            animated: true,
            label: `Rama B (${100 - (config.branchAWeight ?? 50)}%)`,
            labelStyle: { fill: "#a78bfa", fontWeight: "bold", fontSize: 9 },
            style: { stroke: "#a78bfa", strokeWidth: 2, strokeDasharray: "4,4" }
          });
        }
      }
    });

    setCanvasNodes(newNodes);
    setCanvasEdges(newEdges);
  }, [steps, onEdit, setCanvasNodes, setCanvasEdges]);

  // Handle visual edits on drag changes
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setCanvasNodes(nds => applyNodeChanges(changes, nds));
  }, [setCanvasNodes]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setCanvasEdges(eds => applyEdgeChanges(changes, eds));
  }, [setCanvasEdges]);

  // Save node coordinate positions
  const onNodeDragStop = async (_: any, node: Node) => {
    const step = steps.find(s => s.id === node.id);
    if (!step) return;

    let config: any = {};
    try {
      config = typeof step.config === "string" ? JSON.parse(step.config) : step.config || {};
    } catch {}

    config.position = node.position;
    await onSaveStep(step.id, { config: JSON.stringify(config) });
  };

  // Connection dragging rules (React Flow handles standard)
  const onConnect = useCallback(async (connection: Connection) => {
    const sourceStep = steps.find(s => s.id === connection.source);
    const targetStep = steps.find(s => s.id === connection.target);
    if (!sourceStep || !targetStep) return;

    let config: any = {};
    try {
      config = typeof sourceStep.config === "string" ? JSON.parse(sourceStep.config) : sourceStep.config || {};
    } catch {}

    const handle = connection.sourceHandle || "default";

    if (handle.startsWith("option-")) {
      const idx = parseInt(handle.split("-")[1], 10);
      const optText = config.options?.[idx] || `Opción ${idx + 1}`;
      const branches = Array.isArray(config.branches) ? [...config.branches] : [];
      
      const existsIdx = branches.findIndex(b => b.match.toLowerCase() === optText.toLowerCase());
      if (existsIdx !== -1) {
        branches[existsIdx].goToStepId = targetStep.id;
        branches[existsIdx].goToStepOrder = targetStep.order;
      } else {
        branches.push({ match: optText, goToStepId: targetStep.id, goToStepOrder: targetStep.order });
      }
      config.branches = branches;
    } else if (handle.startsWith("branch-")) {
      const idx = parseInt(handle.split("-")[1], 10);
      const branches = Array.isArray(config.branches) ? [...config.branches] : [];
      if (branches[idx]) {
        branches[idx].goToStepId = targetStep.id;
        branches[idx].goToStepOrder = targetStep.order;
        config.branches = branches;
      }
    } else if (handle === "ab-A") {
      config.branchAStepId = targetStep.id;
    } else if (handle === "ab-B") {
      config.branchBStepId = targetStep.id;
    } else {
      config.nextStepId = targetStep.id;
    }

    await onSaveStep(sourceStep.id, { config: JSON.stringify(config) });
    fetchSteps();
  }, [steps, onSaveStep, fetchSteps]);

  // Handle deletions of connected links
  const onEdgesDelete = useCallback(async (edgesToDelete: Edge[]) => {
    for (const edge of edgesToDelete) {
      const sourceStep = steps.find(s => s.id === edge.source);
      if (!sourceStep) continue;

      let config: any = {};
      try {
        config = typeof sourceStep.config === "string" ? JSON.parse(sourceStep.config) : sourceStep.config || {};
      } catch {}

      const handle = edge.sourceHandle || "default";

      if (handle.startsWith("option-")) {
        const idx = parseInt(handle.split("-")[1], 10);
        const optText = config.options?.[idx] || "";
        if (optText && Array.isArray(config.branches)) {
          config.branches = config.branches.filter((b: any) => b.match.toLowerCase() !== optText.toLowerCase());
        }
      } else if (handle.startsWith("branch-")) {
        const idx = parseInt(handle.split("-")[1], 10);
        if (Array.isArray(config.branches)) {
          config.branches = config.branches.filter((_: any, i: number) => i !== idx);
        }
      } else if (handle === "ab-A") {
        delete config.branchAStepId;
      } else if (handle === "ab-B") {
        delete config.branchBStepId;
      } else {
        config.nextStepId = false;
      }

      await onSaveStep(sourceStep.id, { config: JSON.stringify(config) });
    }
    fetchSteps();
  }, [steps, onSaveStep, fetchSteps]);

  // Support drop events from left dragging palette
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <div 
      className="w-full h-full min-h-[500px] relative bg-zinc-950"
      onDragOver={onDragOver}
    >
      <ReactFlow
        nodes={canvasNodes}
        edges={canvasEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgesDelete={onEdgesDelete}
        onNodeDragStop={onNodeDragStop}
        onConnect={onConnect}
        fitView
        colorMode="dark"
      >
        <Background color="#27272a" gap={16} size={1} />
        <Controls className="bg-zinc-900 border border-white/5 rounded-xl shadow-lg fill-white" />
      </ReactFlow>
    </div>
  );
}
