import dagre from "dagre";
import { Node, Edge } from "@xyflow/react";

export function getLayoutedElements(nodes: Node[], edges: Edge[], direction = "LR"): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: direction, nodesep: 100, ranksep: 180 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    // Set node dimensions (approximate size of our custom nodes)
    g.setNode(node.id, { width: 320, height: 260 });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  return nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    if (!nodeWithPosition) return node;
    return {
      ...node,
      position: {
        x: Math.round(nodeWithPosition.x - 160), // Center the node horizontally
        y: Math.round(nodeWithPosition.y - 130), // Center the node vertically
      },
    };
  });
}
