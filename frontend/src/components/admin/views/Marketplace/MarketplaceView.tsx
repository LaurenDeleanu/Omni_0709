"use client";
import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import { fetchClient } from "@/lib/api";
import CategoryBrowser from "./CategoryBrowser";
import AgentTemplateCard, { AgentTemplate } from "./AgentTemplateCard";
import TemplateDetailModal from "./TemplateDetailModal";
import PublishAgentModal from "./PublishAgentModal";

const MARKETPLACE_CATEGORIES = [
  { id: "all", label: "Todo", icon: "🌐" },
  { id: "crm", label: "Sales & CRM", icon: "👥" },
  { id: "ecommerce", label: "E-Commerce & Pagos", icon: "🛍️" },
  { id: "workflows", label: "Automatización", icon: "⚡" },
  { id: "support", label: "Atención & RAG", icon: "🎧" },
];

export default function MarketplaceView({ botId }: { botId: string }) {
  const [bots, setBots] = useState<any[]>([]);
  const [activeBotId, setActiveBotId] = useState<string | null>(botId);
  const fetchBots = async () => {
    try {
      const data = await fetchClient("/agents");
      setBots(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<AgentTemplate[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [search, setSearch] = useState("");
  
  // Modals
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [showPublishModal, setShowPublishModal] = useState(false);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Active agent name for publishing reference
  const activeAgent = bots.find((b: any) => b.id === botId);
  const activeAgentName = activeAgent?.name || "Agente IA";

  const fetchTemplates = async () => {
    setIsLoading(true);
    try {
      const mockTemplates: AgentTemplate[] = [
        {
          id: "support_agent",
          name: "Soporte de Nivel 1 (RAG)",
          tagline: "Responde preguntas frecuentes a partir de tus PDFs indexados.",
          description: "Este agente de IA preconfigurado está optimizado para responder a dudas frecuentes. Incluye base de conocimientos indexada y derivación.",
          category: "support",
          rating: 4.8,
          installs: 340,
          priceType: "FREE",
          priceValue: 0,
          icon: "🎧",
          features: [
            "Soporte RAG de nivel 1 con IA",
            "Derivación inteligente a agente humano",
            "Consulta y reserva de citas (Google Calendar)",
            "Triaje y pre-calificación médica/legal"
          ],
          stepsCount: 5,
          author: "SuccessCore Core"
        },
        {
          id: "crm_agent",
          name: "Calificador de Oportunidades CRM",
          tagline: "Califica leads en base a interacciones y los mueve en el Kanban.",
          description: "Este agente interactúa con tus prospectos, extrae sus presupuestos y necesidades, y los califica en tu CRM de forma autónoma.",
          category: "crm",
          rating: 4.7,
          installs: 215,
          priceType: "FREE",
          priceValue: 0,
          icon: "👥",
          features: [
            "Calificación de oportunidades B2B",
            "Sincronización bidireccional CRM",
            "Asignación automática de asesores",
            "Embudo visual en Kanban"
          ],
          stepsCount: 6,
          author: "SuccessCore Core"
        },
        {
          id: "workflow_agent",
          name: "Asistente de Automatización de Flujos",
          tagline: "Dispara webhooks y conecta APIs de terceros sin código.",
          description: "Automatiza la ejecución de flujos condicionales condicionados por las respuestas del usuario o eventos programados.",
          category: "workflows",
          rating: 4.9,
          installs: 489,
          priceType: "FREE",
          priceValue: 0,
          icon: "⚡",
          features: [
            "Flujo de conversación autónomo",
            "Integración de base de conocimientos",
            "Análisis de sentimientos",
            "Tratamiento automático de leads"
          ],
          stepsCount: 8,
          author: "SuccessCore Core"
        }
      ];
      setTemplates(mockTemplates);
      setFilteredTemplates(mockTemplates);
    } catch (e) {
      console.error("Error setting templates:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
    fetchBots();
  }, []);

  useEffect(() => {
    let filtered = templates;

    if (search) {
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(search.toLowerCase()) ||
          t.tagline.toLowerCase().includes(search.toLowerCase())
      );
    }

    if (selectedCategory !== "all") {
      filtered = filtered.filter((t) => t.category === selectedCategory);
    }

    setFilteredTemplates(filtered);
  }, [search, selectedCategory, templates]);

  // Deploy / Clone template
  const handleDeployTemplate = async (templateId: string) => {
    setIsSaving(true);
    try {
      const selected = templates.find((t) => t.id === templateId);
      const data = await fetchClient("/agents", {
        method: "POST",
        body: JSON.stringify({
          name: `${selected?.name || "Clon"} Nuevo`,
          agentType: selected?.category?.toUpperCase() || "CONVERSATIONAL",
          aiModel: "gpt-4o-mini",
          aiSystemPrompt: selected?.description || "Eres un agente preconfigurado.",
          aiTemperature: 0.7,
          aiTone: "Profesional",
          agentSettings: {},
        }),
      });

      toast.success("¡Agente creado exitosamente a partir de la plantilla!");
      await fetchBots();
      if (data.id) {
        setActiveBotId(data.id);
      }
      setSelectedTemplate(null);
    } catch (e: any) {
      toast.error(e.message || "Error al crear el agente.");
    } finally {
      setIsSaving(false);
    }
  };

  // Publish dynamic template simulation
  const handlePublishTemplate = (templateData: any) => {
    setIsSaving(true);
    setTimeout(() => {
      const mockNewTemplate: AgentTemplate = {
        id: `custom_template_${Math.random().toString(36).substr(2, 9)}`,
        name: templateData.name,
        tagline: templateData.tagline,
        description: templateData.description,
        category: templateData.category,
        rating: 5.0,
        installs: 0,
        priceType: templateData.priceType,
        priceValue: templateData.priceValue,
        icon: "🛡️",
        features: [
          "Configuración activa del Agente",
          "Memoria RAG estructurada",
          "Conectores de API de Salesforce/Slack",
        ],
        stepsCount: 8,
        author: "Personalizado"
      };

      setTemplates([mockNewTemplate, ...templates]);
      toast.success("¡Agente publicado con éxito en el catálogo de tu organización!");
      setIsSaving(false);
      setShowPublishModal(false);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0c] text-white overflow-hidden font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-8 py-6 border-b border-white/5 gap-4">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            Catálogo de Agentes (Marketplace)
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Instancia plantillas B2B listas para producción o comparte tus flujos lógicos con tu organización.
          </p>
        </div>

        <button
          onClick={() => setShowPublishModal(true)}
          className="px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 rounded-xl text-xs font-bold shadow-lg shadow-indigo-500/25 transition-all self-start sm:self-auto"
        >
          📤 Publicar Agente Actual
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar Category Switch */}
        <CategoryBrowser
          categories={MARKETPLACE_CATEGORIES}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        {/* Main Templates Grid */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-8 flex flex-col gap-6 bg-[#09090b]">
          {/* Search bar */}
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 text-sm">🔍</span>
            <input
              type="text"
              placeholder="Buscar plantillas por nombre o descripción..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#18181b] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center flex-1 py-20 text-zinc-500">
              <span className="animate-spin text-3xl mb-3">🏪</span>
              <p className="text-sm">Cargando catálogo de plantillas...</p>
            </div>
          ) : (
            <div className="flex-1">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTemplates.map((template) => (
                  <AgentTemplateCard
                    key={template.id}
                    template={template}
                    onSelect={() => setSelectedTemplate(template)}
                  />
                ))}
              </div>

              {filteredTemplates.length === 0 && (
                <div className="text-center py-20 text-zinc-500 text-sm">
                  No se encontraron plantillas en esta categoría.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Details Modal */}
      {selectedTemplate && (
        <TemplateDetailModal
          template={selectedTemplate}
          onCancel={() => setSelectedTemplate(null)}
          onUseTemplate={handleDeployTemplate}
          isSaving={isSaving}
        />
      )}

      {/* Publish Modal */}
      {showPublishModal && (
        <PublishAgentModal
          botName={activeAgentName}
          onCancel={() => setShowPublishModal(false)}
          onPublish={handlePublishTemplate}
        />
      )}
    </div>
  );
}
