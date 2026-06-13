import React, { useState } from "react";
import { X, Globe, Link as LinkIcon, List, Loader2, Play } from "lucide-react";
import { toast } from "sonner";

interface ScrapeModalProps {
  isOpen: boolean;
  onClose: () => void;
  botId: string;
  bot: any;
  setBot: (b: any) => void;
}

export default function ScrapeModal({ isOpen, onClose, botId, bot, setBot }: ScrapeModalProps) {
  const [mode, setMode] = useState<"SINGLE" | "MULTI" | "DOMAIN">("SINGLE");
  const [singleUrl, setSingleUrl] = useState("");
  const [multiUrls, setMultiUrls] = useState("");
  const [domainUrl, setDomainUrl] = useState("");
  const [excludeMedia, setExcludeMedia] = useState(true);
  const [excludeBlogs, setExcludeBlogs] = useState(true);
  const [excludeTaxonomies, setExcludeTaxonomies] = useState(true);
  const [excludeSocial, setExcludeSocial] = useState(true);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, status: "" });

  if (!isOpen) return null;

  const appendToKnowledge = (markdown: string, url: string) => {
    setBot((prev: any) => {
      const currentText = String(prev.aiKnowledgeBase || "");
      const separator = currentText ? "\n\n" : "";
      return { 
        ...prev, 
        aiKnowledgeBase: currentText + separator + `--- Extraído de: ${url} ---\n` + markdown 
      };
    });
  };

  const processUrl = async (url: string) => {
    try {
      const res = await fetch(`/api/bots/${botId}/crawl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (data.markdown) {
        appendToKnowledge(data.markdown, url);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  };

  const handleStart = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setProgress({ current: 0, total: 0, status: "Iniciando..." });

    try {
      if (mode === "SINGLE") {
        if (!singleUrl) throw new Error("Introduce una URL");
        setProgress({ current: 0, total: 1, status: "Extrayendo URL..." });
        await processUrl(singleUrl);
        toast.success("Página extraída con éxito");
        onClose();
      } 
      else if (mode === "MULTI") {
        const urls = multiUrls.split("\\n").map(u => u.trim()).filter(u => u);
        if (urls.length === 0) throw new Error("Introduce al menos una URL");
        
        setProgress({ current: 0, total: urls.length, status: "Preparando cola de extracción..." });
        for (let i = 0; i < urls.length; i++) {
          setProgress({ current: i + 1, total: urls.length, status: `Extrayendo ${urls[i]}...` });
          await processUrl(urls[i]);
        }
        toast.success(`${urls.length} páginas extraídas con éxito`);
        onClose();
      } 
      else if (mode === "DOMAIN") {
        if (!domainUrl) throw new Error("Introduce un dominio");
        setProgress({ current: 0, total: 0, status: "Descubriendo páginas internas (esto puede tardar)..." });
        
        const res = await fetch(`/api/bots/${botId}/crawl/discover`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: domainUrl, excludeMedia, excludeBlogs, excludeTaxonomies, excludeSocial })
        });
        
        const data = await res.json();
        if (!res.ok || !data.urls) throw new Error(data.error || "Error descubriendo enlaces");
        
        const urls = data.urls as string[];
        if (urls.length === 0) {
          toast.info("No se encontraron páginas internas para extraer.");
          setIsProcessing(false);
          return;
        }

        setProgress({ current: 0, total: urls.length, status: `Se encontraron ${urls.length} páginas. Iniciando extracción...` });
        
        let successCount = 0;
        for (let i = 0; i < urls.length; i++) {
          setProgress({ current: i + 1, total: urls.length, status: `Extrayendo ${urls[i]}...` });
          const ok = await processUrl(urls[i]);
          if (ok) successCount++;
        }
        toast.success(`Se extrajeron ${successCount} de ${urls.length} páginas.`);
        onClose();
      }
    } catch (e: any) {
      toast.error(e.message || "Error durante la extracción");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#18181b] border border-zinc-800 rounded-2xl w-full max-w-xl overflow-hidden flex flex-col shadow-2xl">
        <div className="flex justify-between items-center p-6 border-b border-zinc-800">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Globe className="w-5 h-5 text-indigo-400" />
              Extracción Web Inteligente
            </h2>
            <p className="text-sm text-zinc-400 mt-1">Extrae información directamente a la base de conocimientos.</p>
          </div>
          <button onClick={onClose} disabled={isProcessing} className="p-2 hover:bg-zinc-800 rounded-full transition-colors disabled:opacity-50 text-zinc-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 flex flex-col gap-6">
          {!isProcessing && (
            <div className="flex bg-zinc-900 p-1 rounded-lg">
              <button 
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${mode === "SINGLE" ? "bg-indigo-600/20 text-indigo-400" : "text-zinc-400 hover:text-white"}`}
                onClick={() => setMode("SINGLE")}
              >
                <LinkIcon className="w-4 h-4" /> Única
              </button>
              <button 
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${mode === "MULTI" ? "bg-indigo-600/20 text-indigo-400" : "text-zinc-400 hover:text-white"}`}
                onClick={() => setMode("MULTI")}
              >
                <List className="w-4 h-4" /> Múltiples
              </button>
              <button 
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${mode === "DOMAIN" ? "bg-indigo-600/20 text-indigo-400" : "text-zinc-400 hover:text-white"}`}
                onClick={() => setMode("DOMAIN")}
              >
                <Globe className="w-4 h-4" /> Dominio
              </button>
            </div>
          )}

          {!isProcessing && mode === "SINGLE" && (
            <div className="animate-in fade-in slide-in-from-bottom-2">
              <label className="label text-sm text-zinc-300">URL Específica</label>
              <input 
                type="text" 
                className="input w-full" 
                placeholder="https://ejemplo.com/faq"
                value={singleUrl}
                onChange={e => setSingleUrl(e.target.value)}
              />
              <p className="text-xs text-zinc-500 mt-2">Extrae el contenido de texto de una única página web.</p>
            </div>
          )}

          {!isProcessing && mode === "MULTI" && (
            <div className="animate-in fade-in slide-in-from-bottom-2">
              <label className="label text-sm text-zinc-300">Lista de URLs (Una por línea)</label>
              <textarea 
                className="input w-full font-mono text-xs leading-relaxed" 
                rows={5}
                placeholder={"https://ejemplo.com/faq\\nhttps://ejemplo.com/precios"}
                value={multiUrls}
                onChange={e => setMultiUrls(e.target.value)}
              ></textarea>
              <p className="text-xs text-zinc-500 mt-2">Extrae múltiples páginas en secuencia.</p>
            </div>
          )}

          {!isProcessing && mode === "DOMAIN" && (
            <div className="animate-in fade-in slide-in-from-bottom-2">
              <label className="label text-sm text-zinc-300">Dominio Raíz</label>
              <input 
                type="text" 
                className="input w-full" 
                placeholder="ejemplo.com"
                value={domainUrl}
                onChange={e => setDomainUrl(e.target.value)}
              />
              <p className="text-xs text-zinc-500 mt-2">
                Descubre automáticamente páginas internas y extrae hasta un máximo de 20 subpáginas.
              </p>
              
              <div className="mt-4 space-y-2 border border-zinc-800 rounded-lg p-3 bg-zinc-900/50">
                <p className="text-xs font-medium text-zinc-400 mb-2">Filtros de exclusión automática:</p>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={excludeMedia} onChange={e => setExcludeMedia(e.target.checked)} className="rounded border-zinc-700 bg-zinc-800 text-indigo-500" />
                  <span className="text-xs text-zinc-300">Excluir archivos multimedia (.pdf, .jpg, .zip, etc)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={excludeBlogs} onChange={e => setExcludeBlogs(e.target.checked)} className="rounded border-zinc-700 bg-zinc-800 text-indigo-500" />
                  <span className="text-xs text-zinc-300">Excluir artículos de blog y noticias (/blog/, /news/)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={excludeTaxonomies} onChange={e => setExcludeTaxonomies(e.target.checked)} className="rounded border-zinc-700 bg-zinc-800 text-indigo-500" />
                  <span className="text-xs text-zinc-300">Excluir etiquetas y categorías (/tag/, /category/)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={excludeSocial} onChange={e => setExcludeSocial(e.target.checked)} className="rounded border-zinc-700 bg-zinc-800 text-indigo-500" />
                  <span className="text-xs text-zinc-300">Excluir enlaces a redes sociales</span>
                </label>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="py-8 flex flex-col items-center justify-center animate-in fade-in">
              <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">{progress.status}</h3>
              {progress.total > 0 && (
                <div className="w-full max-w-md">
                  <div className="flex justify-between text-xs text-zinc-400 mb-1">
                    <span>Progreso</span>
                    <span>{progress.current} / {progress.total}</span>
                  </div>
                  <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 transition-all duration-300"
                      style={{ width: `${(progress.current / progress.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-zinc-800 bg-zinc-900/50 flex justify-end gap-3">
          <button 
            onClick={onClose}
            disabled={isProcessing}
            className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button 
            onClick={handleStart}
            disabled={isProcessing || (mode === "SINGLE" && !singleUrl) || (mode === "MULTI" && !multiUrls) || (mode === "DOMAIN" && !domainUrl)}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <>Procesando...</>
            ) : (
              <><Play className="w-4 h-4 fill-current" /> Iniciar Extracción</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
