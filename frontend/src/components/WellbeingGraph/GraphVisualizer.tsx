"use client";

import { useState } from "react";

interface GraphData {
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    data: {
      label: string;
      category: string;
      val_score: number;
      colorStyle: { bg: string; border: string; text: string };
    };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    animated: boolean;
    label: string;
    style: { stroke: string; strokeWidth: number; opacity: number };
    data?: { weight: number; description?: string };
  }>;
}

interface GraphVisualizerProps {
  graph: GraphData;
}

export default function GraphVisualizer({ graph }: GraphVisualizerProps) {
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        Generating Personal Wellbeing Graph from conversation patterns...
      </div>
    );
  }

  const nodeMap = new Map<string, any>();
  graph.nodes.forEach((n) => nodeMap.set(n.id, n));

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🕸️</span>
            <h3 className="font-bold text-white text-base">Personal Wellbeing Topology</h3>
          </div>
          <p className="text-xs text-slate-400">
            Interactive network showing causal stress links and restorative anchor pathways
          </p>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1.5 text-rose-300 font-medium">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span> Stress Loop
          </span>
          <span className="flex items-center gap-1.5 text-sky-300 font-medium">
            <span className="w-2 h-2 rounded-full bg-sky-400"></span> Life Factor
          </span>
        </div>
      </div>

      {/* Interactive SVG Canvas */}
      <div className="relative w-full h-[320px] bg-slate-950/70 rounded-xl border border-white/5 overflow-hidden flex items-center justify-center p-3">
        <svg className="w-full h-full" viewBox="0 0 720 340">
          <defs>
            <marker
              id="arrowhead-sky"
              markerWidth="8"
              markerHeight="6"
              refX="16"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#38bdf8" />
            </marker>
            <marker
              id="arrowhead-rose"
              markerWidth="8"
              markerHeight="6"
              refX="16"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#fb7185" />
            </marker>
          </defs>

          {/* Edges / Connections */}
          {graph.edges.map((eg) => {
            const src = nodeMap.get(eg.source);
            const tgt = nodeMap.get(eg.target);
            if (!src || !tgt) return null;

            const sx = (src.position.x / 650) * 580 + 70;
            const sy = (src.position.y / 450) * 230 + 55;
            const tx = (tgt.position.x / 650) * 580 + 70;
            const ty = (tgt.position.y / 450) * 230 + 55;

            const isHighWeight = (eg.data?.weight || 0) >= 0.8;

            return (
              <g key={eg.id} className="cursor-pointer group">
                <line
                  x1={sx}
                  y1={sy}
                  x2={tx}
                  y2={ty}
                  stroke={isHighWeight ? "#fb7185" : "#38bdf8"}
                  strokeWidth={Math.max(1.8, (eg.data?.weight || 0.7) * 3)}
                  strokeDasharray={eg.animated ? "5, 4" : "none"}
                  markerEnd={isHighWeight ? "url(#arrowhead-rose)" : "url(#arrowhead-sky)"}
                  opacity={isHighWeight ? "0.9" : "0.6"}
                />

                {/* Edge Label Badge */}
                <rect
                  x={(sx + tx) / 2 - 28}
                  y={(sy + ty) / 2 - 14}
                  width="56"
                  height="16"
                  rx="6"
                  fill="#070913"
                  stroke={isHighWeight ? "#fb7185" : "#38bdf8"}
                  strokeWidth="0.75"
                  opacity="0.9"
                />
                <text
                  x={(sx + tx) / 2}
                  y={(sy + ty) / 2 - 3}
                  fill="#e2e8f0"
                  fontSize="8.5"
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {eg.label}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {graph.nodes.map((node) => {
            const cx = (node.position.x / 650) * 580 + 70;
            const cy = (node.position.y / 450) * 230 + 55;
            const isSelected = selectedNode?.id === node.id;

            return (
              <g
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className="cursor-pointer group transition-all"
              >
                {/* Glowing Outer Ring */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected ? "32" : "26"}
                  fill={node.data.colorStyle.bg}
                  stroke={node.data.colorStyle.border}
                  strokeWidth={isSelected ? "2.5" : "1.2"}
                  className="group-hover:stroke-white transition-all shadow-xl"
                  style={{
                    filter: isSelected
                      ? `drop-shadow(0 0 10px ${node.data.colorStyle.border})`
                      : "none",
                  }}
                />

                {/* Node Text */}
                <text
                  x={cx}
                  y={cy - 2}
                  fill="#ffffff"
                  fontSize="9.5"
                  fontWeight="bold"
                  textAnchor="middle"
                  pointerEvents="none"
                >
                  {node.data.label.split(" ")[0]}
                </text>
                <text
                  x={cx}
                  y={cy + 10}
                  fill={node.data.colorStyle.text}
                  fontSize="8"
                  fontWeight="500"
                  textAnchor="middle"
                  pointerEvents="none"
                >
                  {node.data.category}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Selected Node Details Floating Popup */}
        {selectedNode && (
          <div className="absolute bottom-3 right-3 p-3.5 rounded-xl bg-slate-900/95 border border-white/15 backdrop-blur-md text-xs max-w-xs shadow-2xl animate-fadeIn">
            <div className="flex items-center justify-between gap-3 mb-1.5">
              <span className="font-bold text-white text-xs">{selectedNode.data.label}</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-0.5"
              >
                ✕
              </button>
            </div>
            <p className="text-slate-300 text-[11px] mb-1">
              Dimension: <span className="capitalize text-indigo-300 font-semibold">{selectedNode.data.category}</span>
            </p>
            <p className="text-slate-300 text-[11px]">
              Current Balance: <strong className="text-white font-bold">{selectedNode.data.val_score.toFixed(0)}/100</strong>
            </p>
          </div>
        )}
      </div>

      <div className="mt-2 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
        <span>💡 Tap any node to inspect balance score • Dashed links show active compounding loops</span>
        <span>Graph Engine</span>
      </div>
    </div>
  );
}
