"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { ImportAPI, ImportStatus, EntityDefinition } from "@/lib/api";
import { getEntities } from "@/lib/api/imports";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Upload, FileUp, CheckCircle2, XCircle, Loader2, AlertCircle, DownloadCloud, ChevronDown, Users, UserPlus, GraduationCap, Receipt, History, ArrowUpDown, Zap } from "lucide-react";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

type UploadStatus = "idle" | "uploading" | "processing" | "success" | "error";

interface HistoryEntry {
  date: string;
  entityType: string;
  entityLabel: string;
  rows: number;
  status: "success" | "error";
  fileName: string;
}

interface ColumnMapping {
  csvHeader: string;
  targetField: string;
  autoMapped: boolean;
  sampleValue: string;
}

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  employees: <Users className="h-5 w-5" />,
  candidates: <UserPlus className="h-5 w-5" />,
  courses: <GraduationCap className="h-5 w-5" />,
  expenses: <Receipt className="h-5 w-5" />,
};

const MAPPING_HEURISTICS: Record<string, string[]> = {
  full_name: ["full_name", "nombre", "name", "nombre completo", "employee name", "full name"],
  first_name: ["first_name", "nombre", "first name", "given name"],
  last_name: ["last_name", "apellido", "apellidos", "last name", "surname"],
  email: ["email", "correo", "e-mail", "mail", "correo electronico"],
  department: ["department", "departamento", "dept", "area", "division"],
  role: ["role", "cargo", "rol", "position", "puesto", "job title"],
  phone: ["phone", "telefono", "phone number", "tel", "mobile", "celular", "movil"],
  hire_date: ["hire_date", "hire date", "fecha contratacion", "fecha ingreso", "start date", "fecha inicio"],
  manager_email: ["manager_email", "manager email", "email manager", "jefe", "manager"],
  job_id: ["job_id", "job id", "puesto_id", "position id"],
  stage: ["stage", "etapa", "estado", "status"],
  source: ["source", "fuente", "origen", "canal"],
  linkedin_url: ["linkedin_url", "linkedin url", "linkedin", "perfil linkedin"],
  title: ["title", "titulo", "curso", "course name", "nombre curso", "course title"],
  description: ["description", "descripcion", "desc", "overview", "resumen"],
  is_scorm: ["is_scorm", "scorm", "es scorm", "scorm_flag"],
  scorm_version: ["scorm_version", "scorm version", "version scorm"],
  package_url: ["package_url", "package url", "url paquete", "scorm url"],
  min_duration_hours: ["min_duration_hours", "min duration", "duracion minima", "horas minimas", "duration"],
  is_fundae_eligible: ["is_fundae_eligible", "fundae eligible", "bonificable", "fundae"],
  category: ["category", "categoria", "tipo", "category", "type"],
  merchant: ["merchant", "comercio", "proveedor", "vendor", "supplier", "establecimiento"],
  date: ["date", "fecha", "fecha gasto", "transaction date", "expense date"],
  total_amount: ["total_amount", "total amount", "importe", "amount", "total", "monto", "costo", "cost"],
  tax_amount: ["tax_amount", "tax amount", "impuestos", "tax", "iva", "vat"],
  status: ["status", "estado", "state"],
};

const HISTORY_STORAGE_KEY = "sas_import_history";

const loadHistory = (): HistoryEntry[] => {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
};

const saveHistory = (entries: HistoryEntry[]) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries.slice(0, 10)));
  } catch {}
};

function resolveMappings(csvHeaders: string[], targetFields: string[]): ColumnMapping[] {
  const normalizedTargets = targetFields.map((f) => f.toLowerCase().trim());
  return csvHeaders.map((header) => {
    const h = header.toLowerCase().trim();
    let bestMatch = "";
    let autoMapped = false;
    for (const [targetField, aliases] of Object.entries(MAPPING_HEURISTICS)) {
      if (!normalizedTargets.includes(targetField)) continue;
      if (aliases.includes(h)) {
        bestMatch = targetField;
        autoMapped = true;
        break;
      }
    }
    if (!bestMatch) {
      for (const [targetField, aliases] of Object.entries(MAPPING_HEURISTICS)) {
        if (!normalizedTargets.includes(targetField)) continue;
        for (const alias of aliases) {
          if (h.includes(alias) || alias.includes(h)) {
            bestMatch = targetField;
            autoMapped = true;
            break;
          }
        }
        if (bestMatch) break;
      }
    }
    return { csvHeader: header, targetField: bestMatch, autoMapped, sampleValue: "" };
  });
}

function parseCSVHeaders(text: string): string[] {
  const lines = text.trim().split("\n");
  if (lines.length === 0) return [];
  return lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
}

export default function ImportsPage() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [processedCount, setProcessedCount] = useState(0);
  const [entityType, setEntityType] = useState("employees");
  const [entities, setEntities] = useState<EntityDefinition[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory());
  const [showHistory, setShowHistory] = useState(false);

  // Column mapping state
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>([]);
  const [showMapping, setShowMapping] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const selectedEntity = entities.find((e) => e.type === entityType);

  useEffect(() => {
    getEntities()
      .then((data) => setEntities(data.entities || []))
      .catch(() => {});
  }, []);

  const pollStatus = useCallback((id: string) => {
    pollingRef.current = setInterval(async () => {
      try {
        const result: ImportStatus = await ImportAPI.getStatus(id);
        if (result.state === "PROCESSING") {
          setProgress(result.progress_percent ?? 0);
          setProcessedCount((result.inserted ?? 0) + (result.duplicates ?? 0));
        } else if (result.state === "SUCCESS" || result.state === "completed") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setProgress(100);
          setProcessedCount(result.inserted ?? 0);
          setStatus("success");
          const entry: HistoryEntry = {
            date: new Date().toISOString(),
            entityType,
            entityLabel: selectedEntity?.label || entityType,
            rows: result.inserted ?? 0,
            status: "success",
            fileName: selectedFile?.name || "unknown",
          };
          const updated = [entry, ...history].slice(0, 10);
          setHistory(updated);
          saveHistory(updated);
        } else if (result.state === "FAILURE" || result.state === "failed") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setErrorMsg(result.info ?? "Error desconocido al procesar el archivo.");
          setStatus("error");
        }
      } catch {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setStatus("error");
        setErrorMsg("No se pudo obtener el estado de la tarea.");
      }
    }, 1500);
  }, [entityType, selectedEntity, selectedFile, history]);

  const handleUpload = async (file: File) => {
    setSelectedFile(file);
    setStatus("uploading");
    setProgress(0);
    setErrorMsg(null);
    try {
      // Read file for preview and mapping
      const text = await file.text();
      const headers = parseCSVHeaders(text);

      const targetFields = [
        ...(selectedEntity?.required_columns || []),
        ...(selectedEntity?.optional_columns || []),
      ];
      const mappings = resolveMappings(headers, targetFields);

      // Fill sample values from first data row
      const lines = text.trim().split("\n");
      if (lines.length > 1) {
        const dataCols = lines[1].split(",").map((v) => v.trim().replace(/^"|"$/g, ""));
        for (let i = 0; i < mappings.length; i++) {
          mappings[i].sampleValue = dataCols[i] || "";
        }
      }

      setColumnMappings(mappings);
      setShowMapping(true);

      // Also do upload
      const res = await ImportAPI.uploadFile(entityType, file);
      setTaskId(res.task_id);
      setStatus("processing");
      pollStatus(res.task_id);
    } catch {
      setStatus("error");
      setErrorMsg("Error al subir el archivo. Verifica que sea CSV o Excel.");
    }
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  const updateMapping = (csvHeader: string, targetField: string) => {
    setColumnMappings((prev) =>
      prev.map((m) => (m.csvHeader === csvHeader ? { ...m, targetField, autoMapped: false } : m))
    );
  };

  const getMappingStatus = (mapping: ColumnMapping) => {
    if (mapping.autoMapped) return "mapped";
    if (!mapping.targetField) {
      const required = selectedEntity?.required_columns || [];
      const normalized = mapping.csvHeader.toLowerCase().trim();
      for (const alias of Object.values(MAPPING_HEURISTICS)) {
        if (alias.includes(normalized) || normalized.includes(alias[0])) {
          const matchedField = Object.entries(MAPPING_HEURISTICS).find(([, a]) => a === alias)?.[0];
          if (matchedField && required.includes(matchedField)) return "warning";
        }
      }
      return "unmapped";
    }
    return "mapped";
  };

  const reset = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setStatus("idle");
    setSelectedFile(null);
    setTaskId(null);
    setProgress(0);
    setErrorMsg(null);
    setProcessedCount(0);
    setShowMapping(false);
    setColumnMappings([]);
  };

  const unmappedRequired = columnMappings.filter((m) => {
    const req = selectedEntity?.required_columns || [];
    const h = m.csvHeader.toLowerCase().trim();
    for (const [field, aliases] of Object.entries(MAPPING_HEURISTICS)) {
      if (req.includes(field) && !m.targetField) {
        if (aliases.some((a) => h.includes(a) || a.includes(h))) return true;
      }
    }
    return false;
  });

  const allRequiredMapped = unmappedRequired.length === 0;

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Importacion Masiva</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Sube archivos CSV o Excel para importar registros en diferentes modulos.
        </p>
      </div>

      <InlineCopilot
        moduleContext="imports"
        placeholder="Pregunta sobre importaciones..."
        quickActions={[
          { label: "Validate my CSV file", message: "Validate my CSV file" },
          { label: "Import employee records", message: "Import employee records" },
          { label: "Import candidates", message: "Import candidates" },
          { label: "Check import history", message: "Check import history" },
        ]}
      />

      {/* Entity Selector */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4" /> Tipo de Entidad
          </CardTitle>
          <CardDescription>Selecciona que tipo de datos quieres importar.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {entities.map((entity) => (
              <button
                key={entity.type}
                onClick={() => { setEntityType(entity.type); reset(); }}
                className={`
                  flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 text-sm
                  ${entityType === entity.type
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border hover:border-primary/40 hover:bg-muted/30"
                  }
                `}
              >
                <span className={entityType === entity.type ? "text-primary" : "text-muted-foreground"}>
                  {ENTITY_ICONS[entity.type]}
                </span>
                <span className="font-medium">{entity.label}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Upload Zone */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileUp className="h-4 w-4" /> Subir Archivo
          </CardTitle>
          <CardDescription>
            {selectedEntity
              ? `Arrastra tu CSV/Excel aqui para importar ${selectedEntity.label.toLowerCase()}.`
              : "Selecciona un tipo de entidad primero."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status === "idle" && (
            <>
              <div
                id="drop-zone"
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
                  ${dragOver
                    ? "border-primary bg-primary/5 scale-[1.01]"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                  }
                `}
              >
                <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                <p className="font-medium text-sm">Arrastra aqui tu archivo</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Formatos soportados: <strong>.csv</strong> y <strong>.xlsx</strong>
                </p>
                <Button variant="outline" size="sm" className="mt-4" type="button">
                  Seleccionar archivo
                </Button>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".csv,.xlsx"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
              />
            </>
          )}

          {status === "uploading" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="font-medium">Subiendo <span className="text-primary">{selectedFile?.name}</span>...</p>
            </div>
          )}

          {status === "processing" && (
            <div className="space-y-6 py-4">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Procesando en background...</p>
                  <p className="text-xs text-muted-foreground">
                    {selectedFile?.name} &middot; {selectedEntity?.label} &middot; Task ID: <code className="text-xs">{taskId?.slice(0, 12)}...</code>
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Progreso</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <div className="w-full bg-muted/50 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {processedCount > 0 && (
                  <p className="text-xs text-muted-foreground text-right">
                    {processedCount.toLocaleString()} registros procesados
                  </p>
                )}
              </div>
            </div>
          )}

          {status === "success" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <CheckCircle2 className="h-12 w-12 text-emerald-500" />
              <div>
                <p className="font-semibold text-emerald-500">Importacion completada!</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {processedCount.toLocaleString()} registros nuevos insertados correctamente.
                </p>
              </div>
              <Button id="import-again-btn" variant="outline" onClick={reset}>Nueva importacion</Button>
            </div>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <XCircle className="h-12 w-12 text-destructive" />
              <div>
                <p className="font-semibold text-destructive">Error en la importacion</p>
                <p className="text-sm text-muted-foreground mt-1">{errorMsg}</p>
              </div>
              <Button id="retry-import-btn" variant="outline" onClick={reset}>Intentar de nuevo</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI Column Mapping */}
      {showMapping && columnMappings.length > 0 && (
        <Card className="glass border-primary/30">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" /> AI Column Mapping
            </CardTitle>
            {!allRequiredMapped && (
              <Badge variant="destructive" className="text-xs">
                {unmappedRequired.length} required column{unmappedRequired.length !== 1 ? "s" : ""} unmapped
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Mapeo automatico de columnas detectadas. Revisa y corrige si es necesario.
            </p>
            <div className="overflow-x-auto">
              <table className="text-sm w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 pr-4 font-medium">Status</th>
                    <th className="text-left py-2 pr-4 font-medium">CSV Header</th>
                    <th className="text-left py-2 pr-4 font-medium">Sample Value</th>
                    <th className="text-left py-2 font-medium">Target Field</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  {columnMappings.map((mapping) => {
                    const mapStatus = getMappingStatus(mapping);
                    const req = selectedEntity?.required_columns || [];
                    const isRequired = Object.entries(MAPPING_HEURISTICS).some(
                      ([field, aliases]) =>
                        req.includes(field) &&
                        aliases.some((a) => a === mapping.csvHeader.toLowerCase().trim() || a.includes(mapping.csvHeader.toLowerCase().trim()))
                    );

                    return (
                      <tr key={mapping.csvHeader} className="border-b border-border/30">
                        <td className="py-2 pr-4">
                          {mapStatus === "mapped" && mapping.autoMapped ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          ) : mapStatus === "warning" ? (
                            <AlertCircle className="h-4 w-4 text-amber-500" />
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="py-2 pr-4">
                          <code className="text-primary text-xs">{mapping.csvHeader}</code>
                          {isRequired && (
                            <Badge variant="destructive" className="ml-2 text-[10px] py-0 px-1">req</Badge>
                          )}
                        </td>
                        <td className="py-2 pr-4 text-xs">{mapping.sampleValue || "-"}</td>
                        <td className="py-2">
                          <select
                            className="text-xs border border-border rounded-md px-2 py-1 bg-background min-w-[140px]"
                            value={mapping.targetField}
                            onChange={(e) => updateMapping(mapping.csvHeader, e.target.value)}
                          >
                            <option value="">-- None --</option>
                            {(selectedEntity?.required_columns || []).map((col) => (
                              <option key={col} value={col}>&#x26D1; {col}</option>
                            ))}
                            {(selectedEntity?.optional_columns || []).map((col) => (
                              <option key={col} value={col}>{col}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Format Guide */}
      {selectedEntity && (
        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500" /> Formato requerido — {selectedEntity.label}
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => ImportAPI.downloadTemplate(entityType)}
            >
              <DownloadCloud className="w-4 h-4" /> Descargar Plantilla CSV
            </Button>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              Tu archivo CSV/Excel debe contener las siguientes columnas:
            </p>
            <div className="overflow-x-auto">
              <table className="text-sm w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 pr-4 font-medium">Columna</th>
                    <th className="text-left py-2 font-medium">Obligatorio</th>
                  </tr>
                </thead>
                <tbody className="text-muted-foreground">
                  {[...selectedEntity.required_columns, ...selectedEntity.optional_columns].map((col) => (
                    <tr key={col} className="border-b border-border/30">
                      <td className="py-2 pr-4"><code className="text-primary text-xs">{col}</code></td>
                      <td className="py-2">
                        <Badge
                          variant={selectedEntity.required_columns.includes(col) ? "default" : "secondary"}
                          className="text-xs"
                        >
                          {selectedEntity.required_columns.includes(col) ? "Si" : "No"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Import History */}
      <Card className="glass">
        <CardHeader
          className="flex flex-row items-center justify-between space-y-0 pb-2 cursor-pointer"
          onClick={() => setShowHistory(!showHistory)}
        >
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" /> Historial de Importaciones
          </CardTitle>
          <ChevronDown className={`h-4 w-4 transition-transform ${showHistory ? "rotate-180" : ""}`} />
        </CardHeader>
        {showHistory && (
          <CardContent>
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No hay importaciones recientes.
              </p>
            ) : (
              <div className="space-y-2">
                {history.map((entry, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 py-2 px-3 rounded-lg bg-muted/30 text-sm"
                  >
                    <span className="shrink-0">
                      {entry.status === "success" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-destructive" />
                      )}
                    </span>
                    <span className="font-medium shrink-0">{ENTITY_ICONS[entry.entityType] || null}</span>
                    <span className="flex-1 min-w-0">
                      <span className="font-medium">{entry.entityLabel}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {entry.rows.toLocaleString()} rows &middot; {entry.fileName}
                      </span>
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {new Date(entry.date).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
