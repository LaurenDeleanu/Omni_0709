"use client";

import React, { useState } from "react";
import { Users, DollarSign, Settings, Plus, FileSpreadsheet } from "lucide-react";
import ContactsTable from "./ContactsTable";
import DealsBoard from "./DealsBoard";
import PipelineConfigView from "./PipelineConfigView";

export default function CRMView({ botId }: { botId: string }) {
  const activeOrgId = "default";
  const t = (key: string) => {
    const map: Record<string, string> = {
      "crm.title": "CRM & Contacts",
      "crm.add_contact": "Add Contact",
      "crm.add_deal": "Add Deal",
      "crm.contacts": "Contacts",
      "crm.deals": "Deals",
      "crm.pipelines": "Pipelines",
    };
    return map[key] || key;
  };
  const [activeSubTab, setActiveSubTab] = useState<"contacts" | "deals" | "pipeline">("contacts");

  const [refreshContactsTrigger, setRefreshContactsTrigger] = useState(0);
  const [refreshDealsTrigger, setRefreshDealsTrigger] = useState(0);

  const [isAddContactOpen, setIsAddContactOpen] = useState(false);
  const [isAddDealOpen, setIsAddDealOpen] = useState(false);

  if (!activeOrgId) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-zinc-500">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[var(--color-primary)] mb-3" />
        <span className="text-xs font-light">Loading CRM workspace...</span>
      </div>
    );
  }

  const handleContactAdded = () => {
    setRefreshContactsTrigger(prev => prev + 1);
  };

  const handleDealAdded = () => {
    setRefreshDealsTrigger(prev => prev + 1);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-secondary)]">
              💼 {t("crm.title")}
            </h2>
            <span className="text-[10px] bg-[var(--color-primary)]/10 border border-[var(--color-primary)]/20 text-[var(--color-primary)] font-mono font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              CRM Engine
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-light">
            Manage your leads, tracks deal progress on the Kanban boards, and inspect customer timelines.
          </p>
        </div>

        <div className="flex gap-3 shrink-0">
          {activeSubTab === "contacts" && (
            <button
              onClick={() => setIsAddContactOpen(true)}
              className="btn-primary shadow-lg shadow-[var(--color-primary)]/10 px-6 py-2.5 text-xs font-bold flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {t("crm.add_contact")}
            </button>
          )}
          {activeSubTab === "deals" && (
            <button
              onClick={() => setIsAddDealOpen(true)}
              className="btn-primary shadow-lg shadow-[var(--color-primary)]/10 px-6 py-2.5 text-xs font-bold flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {t("crm.add_deal")}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/5 mb-8 overflow-x-auto custom-scrollbar">
        <button
          onClick={() => setActiveSubTab("contacts")}
          className={`flex items-center gap-2 px-6 py-3 border-b-2 text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === "contacts"
              ? "border-[var(--color-primary)] text-[var(--color-primary)] bg-[rgba(6,182,212,0.02)]"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <Users className="w-4 h-4" />
          {t("crm.contacts")}
        </button>
        <button
          onClick={() => setActiveSubTab("deals")}
          className={`flex items-center gap-2 px-6 py-3 border-b-2 text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === "deals"
              ? "border-[var(--color-primary)] text-[var(--color-primary)] bg-[rgba(6,182,212,0.02)]"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <DollarSign className="w-4 h-4" />
          {t("crm.deals")}
        </button>
        <button
          onClick={() => setActiveSubTab("pipeline")}
          className={`flex items-center gap-2 px-6 py-3 border-b-2 text-xs font-bold transition-all whitespace-nowrap ${
            activeSubTab === "pipeline"
              ? "border-[var(--color-primary)] text-[var(--color-primary)] bg-[rgba(6,182,212,0.02)]"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <Settings className="w-4 h-4" />
          {t("crm.pipelines")}
        </button>
      </div>

      {/* Content Container */}
      <div className="space-y-6">
        {activeSubTab === "contacts" && (
          <div className="animate-fade-in">
            <ContactsTable
              orgId={activeOrgId}
              refreshTrigger={refreshContactsTrigger}
              isAddOpen={isAddContactOpen}
              onCloseAdd={() => setIsAddContactOpen(false)}
              onContactAdded={handleContactAdded}
            />
          </div>
        )}
        {activeSubTab === "deals" && (
          <div className="animate-fade-in">
            <DealsBoard
              orgId={activeOrgId}
              refreshTrigger={refreshDealsTrigger}
              refreshContactsTrigger={refreshContactsTrigger}
              isAddOpen={isAddDealOpen}
              onCloseAdd={() => setIsAddDealOpen(false)}
              onDealAdded={handleDealAdded}
            />
          </div>
        )}
        {activeSubTab === "pipeline" && (
          <div className="animate-fade-in">
            <PipelineConfigView
              orgId={activeOrgId}
              onPipelineUpdated={() => setRefreshDealsTrigger(prev => prev + 1)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
