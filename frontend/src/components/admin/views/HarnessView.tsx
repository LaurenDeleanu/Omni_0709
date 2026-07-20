"use client";
import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { 
  Play, Trash2, Plus, ArrowRight, CheckCircle2, XCircle, Search, 
  Settings, Zap, FileText, Code, Database, ChevronRight, HelpCircle,
  Activity, ShieldAlert, Cpu, Sparkles, RefreshCw, BarChart2, MessageSquare
} from "lucide-react";

interface TestCase {
  id: string;
  name: string;
  inputPayload: string;
  expectedCriteria: string;
  mockCollectedData: string;
}

interface TestRun {
  id: string;
  status: string;
  passedCount: number;
  failedCount: number;
  totalCount: number;
  avgLatencyMs: number;
  createdAt: string;
  logDetails: string; // JSON Stringified array of case runs
}

interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  testCases: TestCase[];
  runs: TestRun[];
}

export default function HarnessView({ botId }: { botId: string }) {
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [activeSuiteId, setActiveSuiteId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState<string | null>(null); // holds suiteId being run
  const [isLoading, setIsLoading] = useState(true);

  // Modals state
  const [showSuiteModal, setShowSuiteModal] = useState(false);
  const [showCaseModal, setShowCaseModal] = useState(false);
  const [suiteName, setSuiteName] = useState("");
  const [suiteDesc, setSuiteDesc] = useState("");

  // TestCase form state
  const [caseName, setCaseName] = useState("");
  const [caseInput, setCaseInput] = useState("");
  const [caseCriteria, setCaseCriteria] = useState("");
  const [caseMockData, setCaseMockData] = useState("{}");

  // Selected run / drawer details
  const [selectedRun, setSelectedRun] = useState<TestRun | null>(null);
  const [selectedCaseResult, setSelectedCaseResult] = useState<any | null>(null);

  // Prompt Battler State
  const [showBattler, setShowBattler] = useState(false);
  const [draftPrompt, setDraftPrompt] = useState("");
  const [battlerModel, setBattlerModel] = useState("gpt-4o-mini");
  const [battlerResults, setBattlerResults] = useState<any[]>([]);
  const [isBattlerRunning, setIsBattlerRunning] = useState(false);

  const fetchSuites = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/bots/${botId}/harness`);
      if (res.ok) {
        const data = await res.json();
        setSuites(data.suites || []);
        if (data.suites?.length > 0 && !activeSuiteId) {
          setActiveSuiteId(data.suites[0].id);
        }
      }
    } catch (e) {
      toast.error("Error cargando suites de evaluación");
    } finally {
      setIsLoading(false);
    }
  }, [botId, activeSuiteId]);

  useEffect(() => {
    fetchSuites();
  }, [botId, fetchSuites]);

  const handleCreateSuite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!suiteName.trim()) return;

    try {
      const res = await fetch(`/api/bots/${botId}/harness`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: suiteName, description: suiteDesc }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Suite "${suiteName}" creada correctamente`);
        setSuiteName("");
        setSuiteDesc("");
        setShowSuiteModal(false);
        setActiveSuiteId(data.suite.id);
        fetchSuites();
      }
    } catch (e) {
      toast.error("Error al crear suite");
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSuiteId || !caseName.trim() || !caseInput.trim() || !caseCriteria.trim()) return;

    try {
      const res = await fetch(`/api/bots/${botId}/harness/${activeSuiteId}/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: caseName,
          inputPayload: caseInput,
          expectedCriteria: caseCriteria,
          mockCollectedData: caseMockData
        }),
      });
      if (res.ok) {
        toast.success("Caso de prueba añadido a la suite");
        setCaseName("");
        setCaseInput("");
        setCaseCriteria("");
        setCaseMockData("{}");
        setShowCaseModal(false);
        fetchSuites();
      }
    } catch (e) {
      toast.error("Error al crear caso de prueba");
    }
  };

  const handleDeleteSuite = async (suiteId: string) => {
    if (!confirm("¿Seguro que deseas eliminar esta suite y su historial de ejecuciones?")) return;

    try {
      const res = await fetch(`/api/bots/${botId}/harness/${suiteId}`, { method: "DELETE" });
      if (res.ok) {
        toast.success("Suite eliminada");
        if (activeSuiteId === suiteId) setActiveSuiteId(null);
        fetchSuites();
      }
    } catch (e) {
      toast.error("Error al eliminar suite");
    }
  };

  const handleDeleteCase = async (suiteId: string, caseId: string) => {
    if (!confirm("¿Eliminar este caso de prueba?")) return;

    try {
      const res = await fetch(`/api/bots/${botId}/harness/${suiteId}/cases/${caseId}`, { method: "DELETE" });
      if (res.ok) {
        toast.success("Caso de prueba eliminado");
        fetchSuites();
      }
    } catch (e) {
      toast.error("Error al eliminar caso");
    }
  };

  const handleRunSuite = async (suiteId: string) => {
    setIsRunning(suiteId);
    toast.loading("Ejecutando suite en sandbox...", { id: "evalrun" });

    try {
      const res = await fetch(`/api/bots/${botId}/harness/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ suiteId }),
      });
      const data = await res.json();
      if (res.ok) {
        if (data.passed) {
          toast.success("¡Pruebas exitosas! Todos los casos pasaron el criterio de evaluación.", { id: "evalrun" });
        } else {
          toast.warning(`Completado: ${data.passedCount} pasaron, ${data.failedCount} fallaron.`, { id: "evalrun" });
        }
        fetchSuites();
      } else {
        toast.error(data.error || "Error al ejecutar las pruebas", { id: "evalrun" });
      }
    } catch (e) {
      toast.error("Error de red al ejecutar suite", { id: "evalrun" });
    } finally {
      setIsRunning(null);
    }
  };

  const handleRunBattler = async () => {
    if (!activeSuite || activeSuite.testCases.length === 0 || !draftPrompt.trim()) return;
    setIsBattlerRunning(true);
    setBattlerResults([]);
    toast.loading("Lanzando batalla de prompts...", { id: "battlerun" });

    try {
      // Simula ejecución para los casos usando el prompt de borrador
      const res = await fetch(`/api/bots/${botId}/harness/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ suiteId: activeSuiteId, overridePrompt: draftPrompt, model: battlerModel }),
      });
      const data = await res.json();
      if (res.ok) {
        setBattlerResults(data.results || []);
        toast.success("Batalla completada. Compara los resultados abajo.", { id: "battlerun" });
      } else {
        toast.error("Error en la batalla de prompts", { id: "battlerun" });
      }
    } catch (e) {
      toast.error("Error de conexión", { id: "battlerun" });
    } finally {
      setIsBattlerRunning(false);
    }
  };

  const activeSuite = suites.find(s => s.id === activeSuiteId);

  return (
    <div className="p-8 max-w-6xl mx-auto pb-24 text-zinc-100">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-400 to-indigo-500 flex items-center gap-2">
            🔬 Eval Harness Console
          </h2>
          <p className="text-zinc-400 mt-2">Crea bancos de pruebas conversacionales y evalúa a tu agente con LLM-as-a-Judge.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => setShowBattler(!showBattler)} 
            className={`btn-secondary flex items-center gap-2 text-xs py-2.5 px-4 font-bold border transition-colors ${showBattler ? "border-purple-500 bg-purple-500/10 text-purple-300" : "border-white/5"}`}
          >
            <Sparkles className="w-4 h-4 text-purple-400" />
            Playground de Prompts
          </button>
          <button 
            onClick={() => setShowSuiteModal(true)} 
            className="btn-primary shadow-lg shadow-purple-500/15 flex items-center gap-2 text-xs font-bold py-2.5 px-4"
          >
            <Plus className="w-4 h-4" />
            Nueva Suite
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* LEFTPANE: Suites Selector */}
        <div className="flex flex-col gap-4">
          <h3 className="text-xs uppercase font-bold tracking-widest text-zinc-500">Suites de Evaluación</h3>
          {isLoading ? (
            <div className="text-zinc-500 text-xs italic py-4">Cargando suites...</div>
          ) : suites.length === 0 ? (
            <div className="glass-card p-6 text-center text-zinc-500 text-xs italic border border-white/5">
              No hay suites creadas. Añade una para empezar.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {suites.map(s => {
                const lastRun = s.runs[0];
                const statusColor = lastRun 
                  ? lastRun.status === "SUCCESS" ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400" : "border-rose-500/30 bg-rose-500/5 text-rose-400"
                  : "border-white/5 bg-white/5 text-zinc-400";
                
                return (
                  <div 
                    key={s.id} 
                    onClick={() => { setActiveSuiteId(s.id); setShowBattler(false); }}
                    className={`glass-card p-4 cursor-pointer transition-all border group flex flex-col gap-2 ${activeSuiteId === s.id ? "border-indigo-500 bg-indigo-500/5" : "border-white/5 hover:border-white/10"}`}
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-sm text-white group-hover:text-indigo-300 transition-colors truncate max-w-[150px]">{s.name}</span>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDeleteSuite(s.id); }}
                        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-rose-400 transition-opacity p-0.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {s.description && <p className="text-[11px] text-zinc-400 line-clamp-1">{s.description}</p>}
                    
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5 text-[10px]">
                      <span className="font-mono text-zinc-500">{s.testCases.length} casos</span>
                      <span className={`px-2 py-0.5 rounded-full border text-[9px] font-bold ${statusColor}`}>
                        {lastRun ? `${lastRun.passedCount}/${lastRun.totalCount} OK` : "Sin ejecutar"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHTPANE: Suite Detail & Evaluation Sandbox */}
        <div className="lg:col-span-3">
          {showBattler ? (
            /* PROMPT BATTLER PLAYGROUND */
            <div className="glass-card p-6 border-purple-500/20 bg-purple-950/5 flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-white/5 pb-4">
                <div>
                  <h3 className="text-lg font-bold text-purple-300 flex items-center gap-2">⚔️ Batalla de Prompts (Prompt Battler)</h3>
                  <p className="text-xs text-zinc-400 mt-1">Modifica tu system prompt en borrador y compáralo con el de producción.</p>
                </div>
                <button 
                  onClick={handleRunBattler} 
                  disabled={isBattlerRunning || !activeSuite || activeSuite.testCases.length === 0}
                  className="btn-primary bg-purple-600 hover:bg-purple-500 px-5 text-xs font-bold flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isBattlerRunning ? "animate-spin" : ""}`} />
                  {isBattlerRunning ? "Simulando..." : "Correr Batalla"}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2 block">System Prompt en Borrador (Draft)</label>
                  <textarea 
                    className="input font-mono text-xs leading-relaxed" 
                    rows={8} 
                    placeholder="Pega aquí el system prompt alternativo que deseas evaluar..." 
                    value={draftPrompt}
                    onChange={e => setDraftPrompt(e.target.value)}
                  ></textarea>
                </div>
                <div className="flex flex-col gap-4">
                  <div>
                    <label className="label text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2 block">Modelo Evaluador (Model Battler)</label>
                    <select className="input text-xs" value={battlerModel} onChange={e => setBattlerModel(e.target.value)}>
                      <option value="gpt-4o-mini">GPT-4o Mini (Veloz y Económico)</option>
                      <option value="google/gemini-1.5-flash">Gemini 1.5 Flash (Multimodal)</option>
                      <option value="meta-llama/llama-3.1-8b-instruct">Llama 3.1 8B (Groq)</option>
                    </select>
                  </div>
                  <div className="bg-black/20 rounded-xl p-4 border border-white/5 text-xs text-zinc-400 flex flex-col gap-2">
                    <h4 className="font-bold text-white uppercase text-[10px] tracking-wider">Instrucciones de Playground:</h4>
                    <p>1. Introduce la propuesta de prompt.</p>
                    <p>2. Se simulará la conversación en la suite activa y se evaluará con el evaluador LLM.</p>
                    <p>3. Compara si el borrador incrementa la tasa de éxito sin alterar el comportamiento deseado.</p>
                  </div>
                </div>
              </div>

              {battlerResults.length > 0 && (
                <div className="mt-4 space-y-3">
                  <h4 className="text-xs uppercase font-bold tracking-wider text-purple-300">Resultados de la Simulación Comparativa</h4>
                  <div className="flex flex-col gap-3">
                    {battlerResults.map((r, i) => (
                      <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 flex flex-col gap-2.5">
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-xs text-white">Caso: {r.caseName}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${r.passed ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"}`}>
                            {r.passed ? "PASSED" : "FAILED"}
                          </span>
                        </div>
                        <div className="text-[11px] grid grid-cols-2 gap-3 text-zinc-400">
                          <div>
                            <strong className="text-white">Salida (Output):</strong>
                            <p className="bg-black/10 p-2 rounded mt-1 font-mono text-[10.5px] whitespace-pre-wrap">{r.output}</p>
                          </div>
                          <div>
                            <strong className="text-white">Crítica de Evaluación:</strong>
                            <p className="bg-purple-950/10 p-2 rounded mt-1 border border-purple-500/5 whitespace-pre-wrap italic">{r.critique}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : activeSuite ? (
            /* TEST SUITE CONSOLE */
            <div className="flex flex-col gap-6">
              {/* SUITE HEADER */}
              <div className="glass-card p-6 border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold text-white">{activeSuite.name}</h3>
                    <span className="text-xs text-zinc-500 bg-white/5 px-2.5 py-0.5 rounded-full font-mono">{activeSuite.testCases.length} Casos</span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">{activeSuite.description || "Sin descripción proporcionada."}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button 
                    onClick={() => setShowCaseModal(true)} 
                    className="btn-secondary text-xs py-2 px-4 border border-white/5 flex items-center gap-1 hover:bg-white/5"
                  >
                    <Plus className="w-3.5 h-3.5 text-zinc-400" />
                    Añadir Caso
                  </button>
                  <button 
                    onClick={() => handleRunSuite(activeSuite.id)} 
                    disabled={isRunning !== null || activeSuite.testCases.length === 0}
                    className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5 shadow-md shadow-purple-500/10"
                  >
                    <Play className={`w-3.5 h-3.5 ${isRunning === activeSuite.id ? "animate-spin" : ""}`} />
                    {isRunning === activeSuite.id ? "Ejecutando..." : "Ejecutar Suite"}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* CASES LIST */}
                <div className="lg:col-span-2 flex flex-col gap-4">
                  <h4 className="text-xs uppercase font-bold tracking-widest text-zinc-500">Casos de Prueba (QA Boundary Tests)</h4>
                  {activeSuite.testCases.length === 0 ? (
                    <div className="glass-card p-8 text-center text-zinc-500 text-xs italic border border-white/5">
                      No hay casos de prueba en esta suite. Añade el primero para empezar a calificar.
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {activeSuite.testCases.map(tc => (
                        <div key={tc.id} className="glass-card p-5 border border-white/5 hover:border-white/10 transition-all flex flex-col gap-3 group relative">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="font-bold text-sm text-white">{tc.name}</span>
                            </div>
                            <button 
                              onClick={() => handleDeleteCase(activeSuite.id, tc.id)}
                              className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-rose-400 transition-opacity p-0.5 absolute top-4 right-4"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          
                          <div className="text-xs grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-black/10 rounded-lg p-3 border border-white/5">
                              <span className="font-semibold text-zinc-400 block mb-1">Entrada Simulada (Input Payload)</span>
                              <p className="font-mono text-zinc-300 text-[11px] whitespace-pre-wrap">{tc.inputPayload}</p>
                            </div>
                            <div className="bg-indigo-950/5 rounded-lg p-3 border border-indigo-500/10">
                              <span className="font-semibold text-indigo-300 block mb-1">Criterio de Aceptación (Acceptance Criteria)</span>
                              <p className="text-zinc-300 text-[11px] whitespace-pre-wrap">{tc.expectedCriteria}</p>
                            </div>
                          </div>
                          {tc.mockCollectedData && tc.mockCollectedData !== "{}" && (
                            <div className="text-[10px] text-zinc-500 font-mono">
                              🛠️ Pre-load State: <code className="bg-black/30 p-1 rounded px-1.5">{tc.mockCollectedData}</code>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* RUNS HISTORY & ANALYTICS */}
                <div className="flex flex-col gap-4">
                  <h4 className="text-xs uppercase font-bold tracking-widest text-zinc-500">Historial de Calificaciones</h4>
                  {activeSuite.runs.length === 0 ? (
                    <div className="glass-card p-6 text-center text-zinc-500 text-xs italic border border-white/5">
                      Sin ejecuciones previas.
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {activeSuite.runs.map(run => {
                        const scoreRate = run.passedCount / run.totalCount;
                        const cardBorder = run.status === "SUCCESS" ? "border-emerald-500/20 bg-emerald-950/5" : "border-rose-500/20 bg-rose-950/5";
                        const badgeColor = run.status === "SUCCESS" ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400";
                        
                        return (
                          <div 
                            key={run.id}
                            onClick={() => setSelectedRun(run)}
                            className={`glass-card p-4 border transition-all hover:scale-[1.01] cursor-pointer flex flex-col gap-2.5 ${cardBorder}`}
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-bold text-xs text-white">{new Date(run.createdAt).toLocaleString()}</span>
                              <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider ${badgeColor}`}>
                                {run.status}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[11px] border-t border-white/5 pt-2">
                              <div>
                                <span className="text-zinc-500 block">Tasa de Éxito:</span>
                                <strong className="text-white text-xs">{(scoreRate * 100).toFixed(0)}% ({run.passedCount}/{run.totalCount})</strong>
                              </div>
                              <div>
                                <span className="text-zinc-500 block">Latencia Media:</span>
                                <strong className="text-white text-xs">{run.avgLatencyMs ? `${run.avgLatencyMs.toFixed(0)}ms` : "N/A"}</strong>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 text-center border border-white/5 text-zinc-500 text-sm">
              Selecciona una suite de evaluación o crea una nueva para comenzar.
            </div>
          )}
        </div>
      </div>

      {/* DRAWER RESULTS INPECTOR */}
      {selectedRun && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-zinc-900 border-l border-white/10 shadow-2xl p-6 overflow-y-auto animate-slide-in text-zinc-200">
          <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
            <h3 className="text-base font-bold text-white">Detalles de Ejecución - Eval Harness</h3>
            <button onClick={() => { setSelectedRun(null); setSelectedCaseResult(null); }} className="text-zinc-400 hover:text-white">✕</button>
          </div>

          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <span className="text-zinc-500 block">Fecha:</span>
                <strong className="text-white font-mono text-[10px]">{new Date(selectedRun.createdAt).toLocaleDateString()}</strong>
              </div>
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <span className="text-zinc-500 block">Éxito:</span>
                <strong className="text-white text-sm">{selectedRun.passedCount}/{selectedRun.totalCount}</strong>
              </div>
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <span className="text-zinc-500 block">Estado:</span>
                <strong className={`text-xs ${selectedRun.status === "SUCCESS" ? "text-emerald-400" : "text-rose-400"}`}>{selectedRun.status}</strong>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-xs uppercase font-bold tracking-widest text-zinc-500">Reporte del LLM-as-a-Judge</h4>
              <div className="flex flex-col gap-3">
                {(() => {
                  try {
                    const casesArray = JSON.parse(selectedRun.logDetails || "[]");
                    return casesArray.map((c: any, idx: number) => (
                      <div 
                        key={idx} 
                        onClick={() => setSelectedCaseResult(c)}
                        className={`p-3.5 rounded-xl border cursor-pointer transition-all hover:bg-white/5 ${c.passed ? "border-emerald-500/20 bg-emerald-500/5" : "border-rose-500/20 bg-rose-500/5"}`}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-bold text-xs text-white">{c.caseName}</span>
                          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${c.passed ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
                            {c.passed ? "PASSED" : "FAILED"}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 line-clamp-1"><strong>Output:</strong> &quot;{c.output}&quot;</p>
                      </div>
                    ));
                  } catch (e) {
                    return <div className="text-xs text-rose-400">Error parseando logs de ejecución</div>;
                  }
                })()}
              </div>
            </div>
          </div>

          {/* SINGLE CASE RUN ANALYSIS EXPANSION PANEL */}
          {selectedCaseResult && (
            <div className="mt-8 border-t border-white/10 pt-6 space-y-4">
              <div className="flex justify-between items-center">
                <h4 className="text-xs uppercase font-bold tracking-widest text-indigo-400">Análisis Detallado</h4>
                <button onClick={() => setSelectedCaseResult(null)} className="text-[10px] text-zinc-500 hover:text-white">Limpiar selección</button>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <span className="text-zinc-500 block mb-1">Criterio de Evaluación (Expected Criteria):</span>
                  <p className="bg-black/10 p-3 rounded-lg border border-white/5 font-mono text-[11px] text-zinc-300">{selectedCaseResult.expected}</p>
                </div>
                <div>
                  <span className="text-zinc-500 block mb-1">Entrada Simulada (Input Payload):</span>
                  <p className="bg-black/10 p-3 rounded-lg border border-white/5 font-mono text-[11px] text-zinc-300">{selectedCaseResult.input}</p>
                </div>
                <div>
                  <span className="text-zinc-500 block mb-1">Respuesta del Agente (Assistant Response):</span>
                  <p className="bg-black/10 p-3 rounded-lg border border-white/5 font-mono text-[11px] text-white whitespace-pre-wrap">{selectedCaseResult.output}</p>
                </div>
                <div className="bg-indigo-950/10 p-4 rounded-xl border border-indigo-500/20">
                  <span className="text-indigo-400 block mb-1.5 font-bold uppercase tracking-wider text-[10px]">Crítica y Veredicto del Juez:</span>
                  <p className="text-zinc-200 text-[11.5px] italic leading-relaxed whitespace-pre-wrap">&quot;{selectedCaseResult.critique}&quot;</p>
                  <div className="mt-2.5 pt-2 border-t border-white/5 text-[10.5px] text-zinc-400 font-mono">
                    Score de calidad asignado: <strong className="text-white">{selectedCaseResult.score} / 1.0</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUITE MODAL */}
      {showSuiteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="glass-card p-6 w-full max-w-md animate-slide-up border border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">Nueva Suite de Pruebas</h3>
            <form onSubmit={handleCreateSuite} className="flex flex-col gap-4">
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Nombre</label>
                <input className="input text-sm" placeholder="Ej: Soporte Técnico..." value={suiteName} onChange={e => setSuiteName(e.target.value)} required />
              </div>
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Descripción</label>
                <textarea className="input text-sm" rows={3} placeholder="Describe el objetivo de este banco de pruebas..." value={suiteDesc} onChange={e => setSuiteDesc(e.target.value)}></textarea>
              </div>
              <div className="flex gap-3 mt-2">
                <button type="button" onClick={() => setShowSuiteModal(false)} className="btn-secondary flex-1">Cancelar</button>
                <button type="submit" className="btn-primary flex-1 font-bold">Crear Suite</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CASE MODAL */}
      {showCaseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="glass-card p-6 w-full max-w-lg animate-slide-up border border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">Añadir Caso de Prueba</h3>
            <form onSubmit={handleCreateCase} className="flex flex-col gap-4 text-sm">
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Nombre del Test Case</label>
                <input className="input text-sm" placeholder="Ej: Preguntar precio del plan Pro" value={caseName} onChange={e => setCaseName(e.target.value)} required />
              </div>
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Mensaje Simulador (User Input)</label>
                <input className="input text-sm" placeholder="Ej: Hola, ¿cuánto cuesta el plan Pro?" value={caseInput} onChange={e => setCaseInput(e.target.value)} required />
              </div>
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Criterio de Aceptación (Expected Criteria)</label>
                <textarea className="input text-sm font-mono text-xs" rows={3} placeholder="Ej: Debe mencionar que el precio es de $49 al mes y ofrecer una demo gratuita." value={caseCriteria} onChange={e => setCaseCriteria(e.target.value)} required></textarea>
              </div>
              <div>
                <label className="label text-zinc-400 text-xs uppercase mb-1">Mock collectedData variables (JSON String - Opcional)</label>
                <input className="input text-xs font-mono" placeholder='Ej: {"email": "test@mail.com", "name": "Juan"}' value={caseMockData} onChange={e => setCaseMockData(e.target.value)} />
              </div>
              <div className="flex gap-3 mt-2">
                <button type="button" onClick={() => setShowCaseModal(false)} className="btn-secondary flex-1">Cancelar</button>
                <button type="submit" className="btn-primary flex-1 font-bold">Añadir Caso</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
