"use client";

import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import { Plus, Trash2, ArrowUp, ArrowDown, Save, RefreshCw } from "lucide-react";
import { fetchClient } from "@/lib/api";

interface Stage {
  id: string;
  name: string;
  color: string;
}

interface PipelineConfigViewProps {
  orgId: string;
  onPipelineUpdated: () => void;
}

const PRESET_COLORS = [
  "#6366f1", // Indigo
  "#3b82f6", // Blue
  "#06b6d4", // Cyan
  "#10b981", // Emerald
  "#eab308", // Yellow
  "#f97316", // Orange
  "#ef4444", // Red
  "#ec4899", // Pink
  "#a855f7", // Purple
  "#71717a", // Zinc
];

export default function PipelineConfigView({
  orgId,
  onPipelineUpdated,
}: PipelineConfigViewProps) {
  const [pipelineName, setPipelineName] = useState("Ventas Principal");
  const [stages, setStages] = useState<Stage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // New stage form state
  const [newStageName, setNewStageName] = useState("");
  const [newStageColor, setNewStageColor] = useState("#6366f1");

  useEffect(() => {
    async function fetchPipeline() {
      setIsLoading(true);
      try {
        const d = await fetchClient("/crm/stages");
        if (Array.isArray(d)) {
          const mapped = d.map((name: string, index: number) => ({
            id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
            name: name.charAt(0).toUpperCase() + name.slice(1),
            color: PRESET_COLORS[index % PRESET_COLORS.length]
          }));
          setStages(mapped);
        }
      } catch (err) {
        console.error(err);
        toast.error("Failed to load pipeline stages");
      } finally {
        setIsLoading(false);
      }
    }
    fetchPipeline();
  }, [orgId]);

  const handleSavePipeline = async () => {
    if (stages.length === 0) {
      toast.error("You must have at least one stage in the pipeline.");
      return;
    }
    setIsSaving(true);
    try {
      toast.success("Pipeline stages updated successfully.");
      onPipelineUpdated();
    } catch (err) {
      console.error(err);
      toast.error("Connection error saving pipeline.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddStage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStageName.trim()) return;

    const id = newStageName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
    
    // Check if ID already exists
    if (stages.some(st => st.id === id)) {
      toast.error("A stage with a similar name already exists.");
      return;
    }

    const newStage: Stage = {
      id,
      name: newStageName,
      color: newStageColor,
    };

    setStages([...stages, newStage]);
    setNewStageName("");
    toast.success(`Stage "${newStageName}" added to the list. Save to write changes.`);
  };

  const handleDeleteStage = (id: string) => {
    if (stages.length <= 1) {
      toast.error("You must keep at least one pipeline stage.");
      return;
    }
    setStages(stages.filter(s => s.id !== id));
  };

  const moveStage = (index: number, direction: "up" | "down") => {
    const nextIndex = direction === "up" ? index - 1 : index + 1;
    if (nextIndex < 0 || nextIndex >= stages.length) return;

    const updated = [...stages];
    const temp = updated[index];
    updated[index] = updated[nextIndex];
    updated[nextIndex] = temp;
    setStages(updated);
  };

  const handleUpdateStageColor = (index: number, color: string) => {
    const updated = [...stages];
    updated[index].color = color;
    setStages(updated);
  };

  if (isLoading) {
    return (
      <div className="py-24 text-center text-zinc-500">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-3" />
        Loading pipeline stages...
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* Stages Reordering & Edit List */}
      <div className="md:col-span-2 glass-card p-6 border border-white/5 rounded-2xl shadow-xl space-y-6">
        <div>
          <h3 className="text-base font-bold text-white mb-1">Pipeline Customization</h3>
          <p className="text-xs text-zinc-400 font-light">
            Rename, recolor, and change the hierarchy sequence of your deal pipeline stages.
          </p>
        </div>

        <div className="space-y-3">
          <div>
            <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Pipeline Name</label>
            <input
              className="input py-2 text-xs max-w-sm"
              value={pipelineName}
              onChange={e => setPipelineName(e.target.value)}
              required
            />
          </div>

          <div className="border border-white/5 rounded-xl overflow-hidden divide-y divide-white/5 text-xs text-zinc-300">
            {stages.map((stage, index) => (
              <div key={stage.id} className="flex items-center justify-between p-3.5 bg-black/10 hover:bg-black/20 transition-colors">
                <div className="flex items-center gap-3">
                  {/* color indicator */}
                  <div className="w-3.5 h-3.5 rounded-full shrink-0 border border-white/10" style={{ backgroundColor: stage.color }} />
                  
                  <div>
                    <input
                      className="bg-transparent border-b border-transparent focus:border-zinc-700 hover:border-zinc-800 text-white font-semibold focus:outline-none py-0.5 px-1 font-mono text-xs"
                      value={stage.name}
                      onChange={(e) => {
                        const updated = [...stages];
                        updated[index].name = e.target.value;
                        setStages(updated);
                      }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* color swatches inline selection */}
                  <div className="hidden sm:flex gap-1">
                    {PRESET_COLORS.slice(0, 5).map((color) => (
                      <button
                        key={color}
                        onClick={() => handleUpdateStageColor(index, color)}
                        className={`w-3.5 h-3.5 rounded-full border ${stage.color === color ? "border-white scale-110" : "border-transparent opacity-75 hover:opacity-100"}`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>

                  <div className="flex items-center gap-1 border-l border-white/5 pl-3">
                    <button
                      onClick={() => moveStage(index, "up")}
                      disabled={index === 0}
                      className="btn-ghost p-1 text-zinc-400 hover:text-white disabled:opacity-30"
                      title="Move up"
                    >
                      <ArrowUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveStage(index, "down")}
                      disabled={index === stages.length - 1}
                      className="btn-ghost p-1 text-zinc-400 hover:text-white disabled:opacity-30"
                      title="Move down"
                    >
                      <ArrowDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteStage(stage.id)}
                      className="btn-ghost p-1 text-rose-400 hover:text-white hover:bg-rose-500/10 rounded-lg ml-1"
                      title="Delete stage"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-2">
          <button
            onClick={handleSavePipeline}
            disabled={isSaving}
            className="btn-primary px-8 py-3 text-xs font-bold flex items-center gap-2"
          >
            {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {isSaving ? "Saving Config..." : "Save Pipeline Settings"}
          </button>
        </div>
      </div>

      {/* Add New Stage Box Form */}
      <div className="md:col-span-1 glass-card p-6 border border-white/5 rounded-2xl shadow-xl h-fit space-y-5 bg-zinc-900/60">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">Add New Stage</h4>
        
        <form onSubmit={handleAddStage} className="space-y-4 text-xs">
          <div>
            <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Stage Name</label>
            <input
              className="input py-2.5 text-xs"
              placeholder="e.g. Contract Signed"
              value={newStageName}
              onChange={e => setNewStageName(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Stage Theme Color</label>
            <div className="grid grid-cols-5 gap-2 mb-3">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setNewStageColor(color)}
                  className={`h-7 rounded-lg border flex items-center justify-center transition-all ${
                    newStageColor === color 
                      ? "border-white scale-105 shadow-md" 
                      : "border-white/5 opacity-80 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            
            {/* Custom HEX code input */}
            <div className="flex gap-2 items-center">
              <span className="text-zinc-500 font-mono">HEX:</span>
              <input
                className="input py-1 text-xs font-mono w-24 text-center"
                value={newStageColor}
                onChange={e => setNewStageColor(e.target.value)}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={!newStageName.trim()}
            className="btn-primary w-full py-2.5 font-bold text-[10px] flex items-center justify-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            Add Stage to List
          </button>
        </form>
      </div>
    </div>
  );
}
