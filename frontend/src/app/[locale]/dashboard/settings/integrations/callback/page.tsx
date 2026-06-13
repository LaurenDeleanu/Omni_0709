"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useRouter } from "@/i18n/routing";
import { API_BASE } from "@/lib/api/client";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [verifying, setVerifying] = useState(true);

  useEffect(() => {
    const code = searchParams.get("code");
    const provider = searchParams.get("provider");

    if (!code || !provider) {
      toast.error("Parámetros OAuth inválidos.");
      router.push("/dashboard/settings/integrations");
      return;
    }

    const exchangeCode = async () => {
      try {
        const token = localStorage.getItem("local_access_token");
        const res = await fetch(`${API_BASE}/integrations/${provider}/callback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ code })
        });

        if (res.ok) {
          toast.success("Integración conectada correctamente.");
        } else {
          toast.error("Fallo al autenticar con el proveedor.");
        }
      } catch (err) {
        toast.error("Error de red conectando integración.");
      } finally {
        router.push("/dashboard/settings/integrations");
      }
    };

    exchangeCode();
  }, [searchParams, router]);

  return (
    <div className="h-[50vh] flex flex-col items-center justify-center space-y-4">
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
      <p className="text-muted-foreground animate-pulse">
        Verificando conexión segura...
      </p>
    </div>
  );
}

export default function IntegrationsCallback() {
  return (
    <Suspense fallback={<div className="p-8">Cargando...</div>}>
      <CallbackContent />
    </Suspense>
  );
}
