"use client";

import React, { useRef, useState } from "react";
import { Database, FileText, Globe, Upload, Trash2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { fetchClient } from "@/lib/api";

interface Doc {
  id: string;
  filename: string;
  createdAt: string;
}

interface MemoryConfigPanelProps {
  botId: string;
  knowledgeDocs: Doc[];
  aiKnowledgeBase: string;
  onKnowledgeBaseChange: (val: string) => void;
  onRefreshDocs: () => void;
  onOpenScrape: () => void;
}

export default function MemoryConfigPanel({
  botId,
  knowledgeDocs,
  aiKnowledgeBase,
  onKnowledgeBaseChange,
  onRefreshDocs,
  onOpenScrape,
}: MemoryConfigPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const toastId = toast.loading(`Uploading & vectorizing: ${file.name}...`);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await fetchClient(`/agents/${botId}/knowledge`, {
        method: "POST",
        body: formData,
      });
      toast.success("Document vectorized and added successfully!", { id: toastId });
      onRefreshDocs();
    } catch (err) {
      toast.error("Failed to vectorize document.", { id: toastId });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document and purge its vectors?")) return;

    const toastId = toast.loading("Purging vectors...");
    try {
      await fetchClient(`/agents/${botId}/knowledge/${docId}`, {
        method: "DELETE",
      });
      toast.success("Document purged successfully!", { id: toastId });
      onRefreshDocs();
    } catch (err) {
      toast.error("Failed to delete document.", { id: toastId });
    }
  };

  return (
    <div className="space-y-6">
      {/* Short/Long Term Memory configuration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl border border-border/10 bg-muted/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Database className="w-4 h-4" />
            </div>
            <span className="text-sm font-bold text-foreground">Conversation Memory</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed font-light mb-4">
            Holds direct conversational exchanges. Short-term dialogue context length.
          </p>
          <div className="flex gap-2">
            <span className="text-[10px] bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-mono px-2.5 py-1 rounded">
              Window: 20 turns
            </span>
            <span className="text-[10px] bg-secondary text-muted-foreground font-mono px-2.5 py-1 rounded">
              Summarized storage
            </span>
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-border/10 bg-muted/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <FileText className="w-4 h-4" />
            </div>
            <span className="text-sm font-bold text-foreground">Vector Storage (RAG)</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed font-light mb-4">
            Long-term semantic retrieval. Matches knowledge documents to customer query vector embeddings.
          </p>
          <div className="flex gap-2">
            <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono px-2.5 py-1 rounded">
              TopK: 5 chunks
            </span>
            <span className="text-[10px] bg-secondary text-muted-foreground font-mono px-2.5 py-1 rounded">
              pgvector indexed
            </span>
          </div>
        </div>
      </div>

      {/* RAG Vector Files List */}
      <div className="p-6 rounded-2xl border border-border/10 bg-muted/30">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-sm font-bold text-foreground">Vector Knowledge Base</h3>
            <p className="text-[11px] text-muted-foreground font-light mt-0.5">Upload text, markdown, or PDF files. The engine splits and embeds chunks.</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onOpenScrape}
              className="text-xs bg-muted hover:bg-secondary border border-border/20 text-foreground font-medium py-1.5 px-3 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-muted-foreground" />
              Scrape URL
            </button>
            <label className="text-xs bg-[var(--color-primary)] hover:bg-[var(--color-primary)]/80 text-black font-bold py-1.5 px-3 rounded-lg flex items-center gap-1.5 cursor-pointer transition-colors">
              <Upload className="w-3.5 h-3.5" />
              Upload PDF / TXT
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".txt,.md,.pdf"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </label>
          </div>
        </div>

        {knowledgeDocs.length > 0 ? (
          <div className="space-y-2 max-h-56 overflow-y-auto custom-scrollbar border border-border/10 bg-muted/20 rounded-xl p-3">
            {knowledgeDocs.map((doc) => (
              <div
                key={doc.id}
                className="flex justify-between items-center bg-card/50 hover:bg-muted/60 border border-border/10 py-2 px-3 rounded-xl group transition-all"
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-[var(--color-primary)]" />
                  <span className="text-xs text-foreground truncate max-w-[250px] font-mono">{doc.filename}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[10px] text-muted-foreground font-light">
                    {new Date(doc.createdAt).toLocaleDateString()}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteDoc(doc.id)}
                    className="opacity-0 group-hover:opacity-100 text-rose-500 hover:text-destructive transition-opacity p-0.5"
                    title="Delete document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center p-8 border border-dashed border-border/20 rounded-xl text-muted-foreground text-xs font-light">
            No vectorized documents found. Drag and drop file or scrape url.
          </div>
        )}
      </div>

      {/* Global static information base */}
      <div className="p-6 rounded-2xl border border-border/10 bg-muted/30">
        <h3 className="text-sm font-bold text-foreground mb-1">Global Core Context (Static FAQs / Pricing)</h3>
        <p className="text-[11px] text-muted-foreground font-light mb-4">
          This system information will be loaded for every user instruction in the system prompt. Do not exceed 8,000 characters.
        </p>
        <textarea
          className="input font-mono text-xs leading-relaxed bg-card/60 border-border"
          rows={10}
          placeholder="Paste FAQs, price matrixes, address descriptions, or company details here..."
          value={aiKnowledgeBase}
          onChange={(e) => onKnowledgeBaseChange(e.target.value)}
        />
        <div className="flex justify-between items-center mt-2">
          <span className="text-[10px] text-muted-foreground">Always appended to System Prompt</span>
          <span className={`text-[10px] ${aiKnowledgeBase.length > 8000 ? "text-destructive font-bold" : "text-muted-foreground"}`}>
            {aiKnowledgeBase.length} / 8000 chars
          </span>
        </div>
      </div>
    </div>
  );
}
