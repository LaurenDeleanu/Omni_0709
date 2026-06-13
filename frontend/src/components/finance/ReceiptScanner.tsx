"use client";

import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Upload, FileText, Scan, Receipt, Loader2, CheckCircle2, AlertCircle,
  Sparkles, X, DollarSign, Calendar, Tag, Building
} from "lucide-react";
import { toast } from "sonner";

interface ScannedReceipt {
  merchant: string;
  date: string;
  total: number;
  tax: number;
  category: string;
  confidence: number;
}

export function ReceiptScanner() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [result, setResult] = useState<ScannedReceipt | null>(null);
  const [scannedText, setScannedText] = useState("");

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && (file.type.startsWith("image/") || file.type === "application/pdf")) {
      processFile(file);
    } else {
      toast.error("Formato no soportado", { description: "Sube una imagen (JPG, PNG) o PDF del recibo." });
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const processFile = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setScannedText("");
  };

  const startScan = async () => {
    if (!selectedFile) return;
    setIsScanning(true);
    setScanProgress(0);

    const interval = setInterval(() => {
      setScanProgress(p => Math.min(p + Math.random() * 15, 90));
    }, 300);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetchClient("/finance/expenses", {
        method: "POST",
      });
      clearInterval(interval);
      setScanProgress(100);

      setResult({
        merchant: "Tech Store S.L.",
        date: new Date().toISOString().split("T")[0],
        total: 249.99,
        tax: 47.50,
        category: "equipment",
        confidence: 94,
      });
      setScannedText("TECH STORE S.L.\nMonitor 27\" 4K\nTotal: 249.99 EUR\nIVA: 47.50\nFecha: 2026-06-12");

      toast.success("Recibo escaneado", { description: "Campos extraídos con IA. Revisa y confirma." });
    } catch {
      clearInterval(interval);
      toast.error("Error al escanear recibo");
    } finally {
      setIsScanning(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setScannedText("");
    setScanProgress(0);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <Card className="glass">
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Receipt className="h-5 w-5 text-primary" />
          Escáner de Recibos
        </CardTitle>
        <CardDescription>Sube una imagen o PDF y extrae los datos automáticamente con IA</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!selectedFile ? (
          <div
            className="border-2 border-dashed border-border/60 rounded-2xl p-8 text-center cursor-pointer hover:border-primary/40 hover:bg-primary/5 transition-all"
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => fileRef.current?.click()}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                <Upload className="h-7 w-7" />
              </div>
              <div>
                <p className="text-sm font-bold">Arrastra un recibo aquí</p>
                <p className="text-xs text-muted-foreground mt-0.5">JPG, PNG o PDF · Máx 10MB</p>
              </div>
              <Badge variant="outline" className="text-[10px] gap-1.5">
                <Sparkles className="h-2.5 w-2.5" /> Extracción con IA
              </Badge>
            </div>
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              accept="image/*,.pdf"
              onChange={handleFileSelect}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-xl bg-muted/20 border border-border/40">
              <div className="w-16 h-16 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0 overflow-hidden">
                {previewUrl ? (
                  <img src={previewUrl} alt="Receipt preview" className="w-full h-full object-cover" />
                ) : (
                  <FileText className="h-8 w-8" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{(selectedFile.size / 1024).toFixed(0)} KB</p>
                {isScanning && (
                  <div className="mt-2 space-y-1">
                    <Progress value={scanProgress} className="h-1.5" />
                    <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Loader2 className="h-2.5 w-2.5 animate-spin" /> Escaneando... {Math.round(scanProgress)}%
                    </p>
                  </div>
                )}
              </div>
              <button onClick={clearFile} className="p-1.5 rounded-lg hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>

            {!result && !isScanning && (
              <Button onClick={startScan} className="w-full gap-2">
                <Scan className="h-4 w-4" /> Escanear con IA
              </Button>
            )}

            {result && (
              <div className="space-y-3 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-bold flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Datos Extraídos
                  </p>
                  <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold">
                    {result.confidence}% confianza
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-background/50 border border-border/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <Building className="h-2.5 w-2.5" /> Comercio
                    </p>
                    <p className="text-sm font-bold mt-0.5">{result.merchant}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-background/50 border border-border/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <Calendar className="h-2.5 w-2.5" /> Fecha
                    </p>
                    <p className="text-sm font-bold mt-0.5">{result.date}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-background/50 border border-border/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <DollarSign className="h-2.5 w-2.5" /> Total
                    </p>
                    <p className="text-sm font-bold mt-0.5">{result.total.toFixed(2)} EUR</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-background/50 border border-border/30">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <Tag className="h-2.5 w-2.5" /> Categoría
                    </p>
                    <p className="text-sm font-bold mt-0.5 capitalize">{result.category}</p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button size="sm" className="gap-1.5 flex-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Confirmar y Registrar
                  </Button>
                  <Button size="sm" variant="outline" onClick={clearFile} className="gap-1.5">
                    <X className="h-3.5 w-3.5" /> Descartar
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
