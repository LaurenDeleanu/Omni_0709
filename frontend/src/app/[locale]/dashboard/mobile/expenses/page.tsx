"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Camera, CheckCircle2, Receipt, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api/client";
import { useUser } from "@/hooks/use-user";

export default function MobileExpenses() {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [ocrData, setOcrData] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePhotoCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setPhoto(file);
      toast.info("Analizando ticket con IA...");
      setLoading(true);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const token = localStorage.getItem("local_access_token");
        const res = await fetch(`${API_BASE}/finance/expenses/ocr`, {
          method: "POST",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          body: formData,
        });

        if (!res.ok) throw new Error("Error procesando imagen");
        
        const data = await res.json();
        setOcrData(data.data);
        toast.success("Datos extraídos correctamente");
      } catch (err: any) {
        toast.error(err.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleSubmitExpense = async () => {
    if (!ocrData) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/finance/expenses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          user_id: user?.id || user?.user_id || (user?.sub?.includes('|') ? user?.sub?.split('|')[1] : user?.sub) || "test",
          merchant: ocrData.merchant,
          date: ocrData.date,
          total_amount: ocrData.total_amount,
          tax_amount: ocrData.tax_amount,
          category: ocrData.category,
          comments: ocrData.comments,
          receipt_url: "mobile_upload.jpg"
        })
      });

      if (!res.ok) throw new Error("Error enviando gasto");
      toast.success("Nota de gastos enviada para aprobación");
      setPhoto(null);
      setOcrData(null);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto space-y-6">
      <Card className="border-border/50 bg-card/40 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5 text-primary" />
            Gastos Móvil
          </CardTitle>
          <CardDescription>
            Escanea un ticket o factura con tu cámara
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <input 
            type="file" 
            accept="image/*" 
            capture="environment" 
            ref={fileInputRef} 
            className="hidden" 
            onChange={handlePhotoCapture} 
          />
          
          {!ocrData ? (
            <div 
              className="border-2 border-dashed border-border rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <Camera className="w-8 h-8" />
              </div>
              <p className="font-medium text-center">Toca para abrir la cámara</p>
            </div>
          ) : (
            <div className="space-y-4 bg-muted/30 p-4 rounded-xl border border-border/50">
              <div className="flex items-center gap-2 text-green-500 font-medium mb-2">
                <CheckCircle2 className="w-5 h-5" />
                IA Extracción Exitosa
              </div>
              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-muted-foreground">Comercio:</span>
                <span className="font-medium text-right">{ocrData.merchant}</span>
                <span className="text-muted-foreground">Total:</span>
                <span className="font-bold text-right">${ocrData.total_amount}</span>
                <span className="text-muted-foreground">Categoría:</span>
                <span className="font-medium text-right">{ocrData.category}</span>
              </div>
              
              <Button 
                className="w-full mt-4" 
                onClick={handleSubmitExpense}
                disabled={loading}
              >
                {loading ? "Enviando..." : "Enviar Gasto"}
              </Button>
              <Button 
                variant="ghost" 
                className="w-full text-muted-foreground" 
                onClick={() => { setOcrData(null); setPhoto(null); }}
              >
                Escanear Otro
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
