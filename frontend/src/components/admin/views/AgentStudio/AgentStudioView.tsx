"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import { fetchClient } from "@/lib/api";
import { 
  Save, Sparkles, MessageSquare, Database, Settings, ShieldAlert, Cpu, 
  Terminal, Play, HelpCircle
} from "lucide-react";

import AgentTypeSelector from "./AgentTypeSelector";
import CapabilitiesPanel from "./CapabilitiesPanel";
import ToolBindingPanel from "./ToolBindingPanel";
import MemoryConfigPanel from "./MemoryConfigPanel";
import GuardrailsPanel from "./GuardrailsPanel";
import AgentTestBench from "./AgentTestBench";
import ScrapeModal from "../ScrapeModal";

interface AgentStudioViewProps {
  botId: string;
  userTier?: string;
  onUpgradeClick?: () => void;
  dynamicModels: any[];
}

export default function AgentStudioView({
  botId,
  userTier = "FREE",
  onUpgradeClick,
  dynamicModels,
}: AgentStudioViewProps) {
  const [bot, setBot] = useState<any | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showScrapeModal, setShowScrapeModal] = useState(false);
  const [saved, setSaved] = useState(false);
  const [knowledgeDocs, setKnowledgeDocs] = useState<any[]>([]);
  const [fallbackList, setFallbackList] = useState<string[]>([]);
  
  // Tab controller state
  const [activeTab, setActiveTab] = useState<"identity" | "capabilities" | "tools" | "memory" | "guardrails" | "testbench">("identity");

  const fetchDocs = useCallback(async () => {
    try {
      const d = await fetchClient(`/agents/${botId}/knowledge`);
      setKnowledgeDocs(Array.isArray(d) ? d : (d.docs || []));
    } catch (err) {
      console.error(err);
    }
  }, [botId]);

  useEffect(() => {
    fetchClient(`/agents/${botId}`)
      .then((d: any) => {
        const agentData = d.bot || d;
        if (agentData) {
          setBot(agentData);
          try {
            setFallbackList(JSON.parse(agentData.aiFallbackModels || "[]"));
          } catch {
            setFallbackList([]);
          }
        }
      })
      .catch((err) => console.error(err));
    fetchDocs();
  }, [botId, fetchDocs]);

  const saveConfig = async () => {
    setIsSaving(true);
    const toastId = toast.loading("Updating agent properties...");
    try {
      await fetchClient(`/agents/${botId}`, {
        method: "PATCH",
        body: JSON.stringify({
          aiModel: bot.aiModel,
          aiSystemPrompt: bot.aiSystemPrompt,
          aiTemperature: parseFloat(bot.aiTemperature || 0.7),
          aiTone: bot.aiTone,
          aiKnowledgeBase: bot.aiKnowledgeBase,
          aiGuardrails: bot.aiGuardrails,
          aiTools: bot.aiTools,
          aiVisionModel: bot.aiVisionModel,
          aiFallbackModels: bot.aiFallbackModels,
          agentSettings: bot.agentSettings,
          agentType: bot.agentType,
        }),
      });
      setSaved(true);
      toast.success("Agent settings successfully updated!", { id: toastId });
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      console.error("Agent settings save error:", err);
      const detail = err?.message || err?.detail || "Unknown error";
      toast.error(`Failed to update agent settings: ${detail}`, { id: toastId });
    } finally {
      setIsSaving(false);
    }
  };

  const autoSaveConfig = async (updatedBot: any) => {
    toast.loading("Saving changes...", { id: "autosave" });
    try {
      await fetchClient(`/agents/${botId}`, {
        method: "PATCH",
        body: JSON.stringify({
          aiModel: updatedBot.aiModel,
          aiSystemPrompt: updatedBot.aiSystemPrompt,
          aiTemperature: parseFloat(updatedBot.aiTemperature || 0.7),
          aiTone: updatedBot.aiTone,
          aiKnowledgeBase: updatedBot.aiKnowledgeBase,
          aiGuardrails: updatedBot.aiGuardrails,
          aiTools: updatedBot.aiTools,
          aiVisionModel: updatedBot.aiVisionModel,
          aiFallbackModels: updatedBot.aiFallbackModels,
          agentSettings: updatedBot.agentSettings,
          agentType: updatedBot.agentType,
        }),
      });
      toast.success("Settings auto-saved successfully", { id: "autosave" });
    } catch (err) {
      toast.error("Failed to auto-save settings", { id: "autosave" });
    }
  };

  if (!bot) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-zinc-500">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[var(--accent-primary)] mb-3" />
        <span className="text-xs font-light">Loading Laboratory...</span>
      </div>
    );
  }

  const activeTools = (() => {
    try {
      return JSON.parse(bot.aiTools || "[]");
    } catch {
      return [];
    }
  })();

  const toggleTool = (toolId: string) => {
    const updated = activeTools.includes(toolId)
      ? activeTools.filter((t: string) => t !== toolId)
      : [...activeTools, toolId];
    const updatedBot = { ...bot, aiTools: JSON.stringify(updated) };
    setBot(updatedBot);
    autoSaveConfig(updatedBot);
  };

  const activeCapabilities = (() => {
    if (!bot.agentSettings) return {};
    if (typeof bot.agentSettings === "object") return bot.agentSettings;
    try {
      return JSON.parse(bot.agentSettings);
    } catch {
      return {};
    }
  })();

  const handleCapabilitiesChange = (newCapabilities: Record<string, any>) => {
    const updatedBot = { ...bot, agentSettings: newCapabilities };
    setBot(updatedBot);
    autoSaveConfig(updatedBot);
  };

  const handleAgentTypeChange = (newType: string) => {
    const updatedBot = { ...bot, agentType: newType };
    setBot(updatedBot);
    autoSaveConfig(updatedBot);
  };

  const handleGuardrailsChange = (val: string) => {
    setBot({ ...bot, aiGuardrails: val });
  };

  const handleKnowledgeBaseChange = (val: string) => {
    setBot({ ...bot, aiKnowledgeBase: val });
  };

  const tabs = [
    { id: "identity", label: "Identity & Type", icon: <Sparkles className="w-4 h-4" /> },
    { id: "capabilities", label: "Capabilities", icon: <Cpu className="w-4 h-4" /> },
    { id: "tools", label: "Skills / Tools", icon: <Settings className="w-4 h-4" /> },
    { id: "memory", label: "Memory (RAG)", icon: <Database className="w-4 h-4" /> },
    { id: "guardrails", label: "Safety / Policy", icon: <ShieldAlert className="w-4 h-4" /> },
    { id: "testbench", label: "Test Simulator", icon: <Terminal className="w-4 h-4" /> },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto pb-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)]">
              🧪 Agent Studio
            </h2>
            <span className="text-[10px] bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/20 text-[var(--accent-primary)] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {bot.agentType || "CONVERSATIONAL"}
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-light">
            Model, optimize, and simulate your enterprise autonomous AI agent workspace.
          </p>
        </div>

        <div className="flex gap-3 shrink-0">
          <button
            onClick={saveConfig}
            disabled={isSaving}
            className="btn-primary shadow-lg shadow-[var(--accent-primary)]/10 px-8 py-3 text-xs font-bold flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {isSaving ? "Saving..." : saved ? "Config Updated!" : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Tabs list */}
      <div className="flex border-b border-white/5 mb-8 overflow-x-auto custom-scrollbar">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-6 py-3 border-b-2 text-xs font-bold transition-all whitespace-nowrap ${
                isActive
                  ? "border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[rgba(6,182,212,0.02)]"
                  : "border-transparent text-zinc-400 hover:text-white"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="space-y-6">
        {activeTab === "identity" && (
          <div className="space-y-6 animate-fade-in">
            {/* Identity Form */}
            <div className="glass-card p-6">
              <h3 className="text-base font-bold text-white mb-5 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[var(--accent-primary)]" />
                🎭 Identity & System Directives
              </h3>
              
              <div className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">Agent Name</label>
                    <input
                      className="input"
                      value={bot.name || ""}
                      onChange={(e) => setBot({ ...bot, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">Tone of Voice</label>
                    <input
                      className="input"
                      placeholder="e.g. Helpful, professional, concise, empathetic..."
                      value={bot.aiTone || ""}
                      onChange={(e) => setBot({ ...bot, aiTone: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">Primary LLM Model</label>
                  <select
                    className="input"
                    value={bot.aiModel || ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      const model = dynamicModels.find((m) => m.id === val);
                      if (model) {
                        if (model.tier === "ENTERPRISE" && userTier !== "ENTERPRISE") {
                          onUpgradeClick?.();
                          return;
                        }
                        if (model.tier === "PRO" && userTier === "FREE") {
                          onUpgradeClick?.();
                          return;
                        }
                      }
                      const updatedBot = { ...bot, aiModel: val };
                      setBot(updatedBot);
                      autoSaveConfig(updatedBot);
                    }}
                  >
                    {dynamicModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.provider}) {m.tier !== "FREE" ? `🔒 ${m.tier}` : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">Core Instruction (System Prompt)</label>
                  <textarea
                    className="input font-mono text-xs leading-relaxed"
                    rows={8}
                    placeholder="Enter the core identity prompt instructions for the agent..."
                    value={bot.aiSystemPrompt || ""}
                    onChange={(e) => setBot({ ...bot, aiSystemPrompt: e.target.value })}
                  />
                </div>
              </div>
            </div>

            {/* Agent Type selector */}
            <div className="glass-card p-6">
              <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                <Settings className="w-4 h-4 text-[var(--accent-primary)]" />
                Workload Specialization
              </h3>
              <p className="text-xs text-zinc-400 font-light mb-6">
                Assign the architectural paradigm of this agent. This controls default prompt bindings, response structure validations, and available execution modules.
              </p>
              <AgentTypeSelector
                selectedType={bot.agentType || "CONVERSATIONAL"}
                onChange={handleAgentTypeChange}
              />
            </div>

            {/* API Credentials */}
            <div className="glass-card p-6">
              <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-[var(--accent-primary)]" />
                API Credentials (BYOK)
              </h3>
              <p className="text-xs text-zinc-400 font-light mb-6">
                Configure your own API keys. These are encrypted and stored securely inside the tenant's settings database.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">OpenRouter API Key</label>
                  <input
                    type="password"
                    className="input w-full bg-zinc-900 border border-zinc-800 text-white rounded p-2 text-xs"
                    placeholder={activeCapabilities.openrouter_api_key === "********" ? "********" : "sk-or-v1-..."}
                    value={activeCapabilities.openrouter_api_key === "********" ? "********" : (activeCapabilities.openrouter_api_key || "")}
                    onChange={(e) => {
                      const updatedCap = { ...activeCapabilities, openrouter_api_key: e.target.value };
                      handleCapabilitiesChange(updatedCap);
                    }}
                  />
                </div>
                
                <div>
                  <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">OpenAI API Key</label>
                  <input
                    type="password"
                    className="input w-full bg-zinc-900 border border-zinc-800 text-white rounded p-2 text-xs"
                    placeholder={activeCapabilities.openai_api_key === "********" ? "********" : "sk-..."}
                    value={activeCapabilities.openai_api_key === "********" ? "********" : (activeCapabilities.openai_api_key || "")}
                    onChange={(e) => {
                      const updatedCap = { ...activeCapabilities, openai_api_key: e.target.value };
                      handleCapabilitiesChange(updatedCap);
                    }}
                  />
                </div>

                <div>
                  <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">Gemini API Key</label>
                  <input
                    type="password"
                    className="input w-full bg-zinc-900 border border-zinc-800 text-white rounded p-2 text-xs"
                    placeholder={activeCapabilities.gemini_api_key === "********" ? "********" : "AIzaSy..."}
                    value={activeCapabilities.gemini_api_key === "********" ? "********" : (activeCapabilities.gemini_api_key || "")}
                    onChange={(e) => {
                      const updatedCap = { ...activeCapabilities, gemini_api_key: e.target.value };
                      handleCapabilitiesChange(updatedCap);
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "capabilities" && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[var(--accent-primary)]" />
              Autonomous Capabilities
            </h3>
            <p className="text-xs text-zinc-400 font-light mb-6">
              Toggle background checkers and safety agents that run concurrently with the core LLM execution stack.
            </p>
            <CapabilitiesPanel
              settings={activeCapabilities}
              onChange={handleCapabilitiesChange}
            />
          </div>
        )}

        {activeTab === "tools" && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
              <Settings className="w-4 h-4 text-[var(--accent-primary)]" />
              Connector Hub & Skills
            </h3>
            <p className="text-xs text-zinc-400 font-light mb-6">
              Grant the agent specialized functional tools to interact with web APIs, calendar systems, and numeric calculators.
            </p>
            <ToolBindingPanel
              activeTools={activeTools}
              onToggleTool={toggleTool}
            />
          </div>
        )}

        {activeTab === "memory" && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
              <Database className="w-4 h-4 text-[var(--accent-primary)]" />
              Memory & Knowledge (RAG)
            </h3>
            <MemoryConfigPanel
              botId={botId}
              knowledgeDocs={knowledgeDocs}
              aiKnowledgeBase={bot.aiKnowledgeBase || ""}
              onKnowledgeBaseChange={handleKnowledgeBaseChange}
              onRefreshDocs={fetchDocs}
              onOpenScrape={() => setShowScrapeModal(true)}
            />
          </div>
        )}

        {activeTab === "guardrails" && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[var(--accent-primary)]" />
              Safety Guardrails & Compliance Policies
            </h3>
            <GuardrailsPanel
              aiGuardrails={bot.aiGuardrails || ""}
              onGuardrailsChange={handleGuardrailsChange}
              settings={activeCapabilities}
              onSettingsChange={handleCapabilitiesChange}
            />
          </div>
        )}

        {activeTab === "testbench" && (
          <div className="glass-card p-6 animate-fade-in">
            <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[var(--accent-primary)]" />
              Real-time Simulation Bench
            </h3>
            <AgentTestBench
              botId={botId}
              agentModel={bot.aiModel || "gpt-4o-mini"}
            />
          </div>
        )}
      </div>

      <ScrapeModal
        isOpen={showScrapeModal}
        onClose={() => setShowScrapeModal(false)}
        botId={botId}
        bot={bot}
        setBot={setBot}
      />
    </div>
  );
}
