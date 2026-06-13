"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Calendar, Clock, Video, MapPin, Send, Plus, CalendarPlus,
  CheckCircle2, Loader2, Sparkles, Mail
} from "lucide-react";
import { toast } from "sonner";

interface InterviewSchedulerProps {
  candidateId?: string;
  candidateName?: string;
  jobId?: string;
  jobTitle?: string;
}

const STAGES = ["Phone Screen", "Technical", "Culture Fit", "Final", "Offer Discussion"];
const DURATIONS = [30, 45, 60, 90];

export function InterviewScheduler({ candidateId, candidateName, jobId, jobTitle }: InterviewSchedulerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [stage, setStage] = useState("Phone Screen");
  const [scheduledDate, setScheduledDate] = useState("");
  const [scheduledTime, setScheduledTime] = useState("10:00");
  const [duration, setDuration] = useState(60);
  const [location, setLocation] = useState("");
  const [meetingLink, setMeetingLink] = useState("");
  const [notes, setNotes] = useState("");
  const [sendInvite, setSendInvite] = useState(true);

  const scheduleMutation = useMutation({
    mutationFn: (data: any) =>
      fetchClient("/hire/schedule-interview", { method: "POST", body: JSON.stringify(data) }).then(r => r),
    onSuccess: (result) => {
      setIsOpen(false);
      toast.success("Entrevista programada", {
        description: `${result.candidate_name} · ${new Date(result.scheduled_at).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}`
      });
      resetForm();
    },
    onError: () => toast.error("Error al programar entrevista"),
  });

  const resetForm = () => {
    setStage("Phone Screen");
    setScheduledDate("");
    setScheduledTime("10:00");
    setDuration(60);
    setLocation("");
    setMeetingLink("");
    setNotes("");
    setSendInvite(true);
  };

  const handleSchedule = () => {
    if (!scheduledDate || !scheduledTime) {
      toast.error("Selecciona fecha y hora");
      return;
    }
    const scheduledAt = `${scheduledDate}T${scheduledTime}:00`;
    scheduleMutation.mutate({
      candidate_id: candidateId,
      job_id: jobId,
      stage_name: stage,
      scheduled_at: scheduledAt,
      duration_minutes: duration,
      location: location || null,
      meeting_link: meetingLink || null,
      notes: notes || null,
      send_calendar_invite: sendInvite,
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger
        className="w-full"
        render={
          <Button variant="outline" size="sm" className="gap-1.5 w-full">
            <CalendarPlus className="h-4 w-4" /> Programar Entrevista
          </Button>
        }
      />
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            Programar Entrevista
          </DialogTitle>
        </DialogHeader>

        {candidateName && (
          <Badge className="bg-primary/10 text-primary border-primary/20 px-3 py-1.5 text-xs font-bold w-fit">
            <Sparkles className="h-3 w-3 mr-1" /> {candidateName}
            {jobTitle && <span className="mx-1">—</span>}
            {jobTitle}
          </Badge>
        )}

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Etapa de Entrevista</Label>
            <div className="flex gap-1.5 flex-wrap">
              {STAGES.map(s => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStage(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    stage === s
                      ? "bg-primary text-primary-foreground shadow-md"
                      : "bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
                <Calendar className="h-3 w-3 inline mr-1" /> Fecha
              </Label>
              <Input
                type="date"
                className="bg-card/60"
                value={scheduledDate}
                onChange={e => setScheduledDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
                <Clock className="h-3 w-3 inline mr-1" /> Hora
              </Label>
              <Input
                type="time"
                className="bg-card/60"
                value={scheduledTime}
                onChange={e => setScheduledTime(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Duración</Label>
            <div className="flex gap-1.5">
              {DURATIONS.map(d => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDuration(d)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    duration === d
                      ? "bg-indigo-500/20 text-indigo-500 border border-indigo-500/30"
                      : "bg-muted/40 text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {d} min
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
              <MapPin className="h-3 w-3 inline mr-1" /> Ubicación / Sala
            </Label>
            <Input
              className="bg-card/60"
              placeholder="Ej: Sala Reuniones 3 o Remoto"
              value={location}
              onChange={e => setLocation(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
              <Video className="h-3 w-3 inline mr-1" /> Link de Videollamada
            </Label>
            <Input
              className="bg-card/60"
              placeholder="https://meet.google.com/..."
              value={meetingLink}
              onChange={e => setMeetingLink(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Notas</Label>
            <Textarea
              className="bg-card/60 h-16"
              placeholder="Temas a tratar, preguntas, preparación..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={sendInvite}
              onChange={e => setSendInvite(e.target.checked)}
              className="rounded border-border/60"
            />
            <Mail className="h-3.5 w-3.5 text-indigo-500" />
            <span className="text-muted-foreground">Enviar invitación de calendario</span>
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
          <Button
            onClick={handleSchedule}
            disabled={scheduleMutation.isPending || !scheduledDate}
            className="gap-2"
          >
            {scheduleMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {scheduleMutation.isPending ? "Programando..." : "Programar Entrevista"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
