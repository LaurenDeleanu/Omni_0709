"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MapPin, Camera, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";
import { useUser } from "@/hooks/use-user";
import { NotificationAPI } from "@/lib/api/notifications"; // Mock fetching / client
// To call actual endpoint we should add to a finance/ops api client, but for now we'll use raw fetch
import { API_BASE } from "@/lib/api/client";

export default function MobileTimeClock() {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [location, setLocation] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const requestLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocalización no soportada");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation(`${pos.coords.latitude},${pos.coords.longitude}`);
        toast.success("Ubicación obtenida");
      },
      (err) => {
        toast.error("Error obteniendo ubicación: " + err.message);
      }
    );
  };

  const handlePhotoCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPhoto(e.target.files[0]);
      toast.success("Foto capturada");
    }
  };

  const handleClockIn = async () => {
    if (!location) {
      toast.error("Debes permitir la ubicación primero");
      return;
    }
    if (!photo) {
      toast.error("Debes tomarte un selfie para verificar identidad");
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/finance/time-logs/clock-in`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          user_id: user?.id || user?.user_id || (user?.sub?.includes('|') ? user?.sub?.split('|')[1] : user?.sub) || "test",
          geolocation_in: location,
          ip_address: "192.168.1.1", // would be set by backend ideally
          device_info: navigator.userAgent,
          notes: "Clock-in from mobile app",
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error fichando");
      }

      toast.success("Fichaje de entrada exitoso");
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
            <Clock className="w-5 h-5 text-primary" />
            Fichaje Móvil
          </CardTitle>
          <CardDescription>
            Registra tu entrada con verificación de ubicación y selfie
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col gap-3">
            <Button 
              variant={location ? "outline" : "default"} 
              className="w-full h-12 flex justify-between"
              onClick={requestLocation}
            >
              <span className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                {location ? "Ubicación verificada" : "Compartir Ubicación"}
              </span>
              {location && <CheckCircle2 className="w-4 h-4 text-green-500" />}
            </Button>

            <input 
              type="file" 
              accept="image/*" 
              capture="user" 
              ref={fileInputRef} 
              className="hidden" 
              onChange={handlePhotoCapture} 
            />
            
            <Button 
              variant={photo ? "outline" : "default"} 
              className="w-full h-12 flex justify-between"
              onClick={() => fileInputRef.current?.click()}
            >
              <span className="flex items-center gap-2">
                <Camera className="w-4 h-4" />
                {photo ? "Selfie capturado" : "Tomar Selfie"}
              </span>
              {photo && <CheckCircle2 className="w-4 h-4 text-green-500" />}
            </Button>
          </div>

          <Button 
            className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700" 
            onClick={handleClockIn}
            disabled={loading || !location || !photo}
          >
            {loading ? "Registrando..." : "Fichar Entrada"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
