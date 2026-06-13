"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  GraduationCap, Plus, Upload, Clock, BookOpen, Users, CheckSquare,
  FileText, Loader2, Sparkles, ChevronRight, CheckCircle2
} from "lucide-react";
import { toast } from "sonner";

const FUNDAE_CATEGORIES = [
  "Informática y comunicaciones",
  "Administración y gestión",
  "Idiomas",
  "Prevención de riesgos laborales",
  "Habilidades directivas",
  "Comercial y marketing",
];

const COURSE_TYPES = ["Presencial", "Online", "Mixto"] as const;

export function CourseCreator() {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [durationHours, setDurationHours] = useState(8);
  const [courseType, setCourseType] = useState<typeof COURSE_TYPES[number]>("Online");
  const [category, setCategory] = useState(FUNDAE_CATEGORIES[0]);
  const [fundaeEligible, setFundaeEligible] = useState(true);
  const [maxStudents, setMaxStudents] = useState(20);
  const [scormFile, setScormFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsOpen(false);
      toast.success("Curso creado", { description: `${name} añadido al catálogo de formación.` });
      resetForm();
    }, 800);
  };

  const resetForm = () => {
    setName(""); setDescription(""); setDurationHours(8); setCourseType("Online");
    setCategory(FUNDAE_CATEGORIES[0]); setFundaeEligible(true); setMaxStudents(20); setScormFile(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger
        className="w-full"
        render={
          <Button className="w-full gap-2" size="lg">
            <Plus className="h-5 w-5" />
            <GraduationCap className="h-5 w-5" />
            Crear Nuevo Curso
          </Button>
        }
      />
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            Crear Nuevo Curso
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
              <BookOpen className="h-3 w-3 inline mr-1" /> Nombre del Curso
            </Label>
            <Input
              className="bg-card/60"
              placeholder="Ej: Fundamentos de Python para Data Science"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Descripción</Label>
            <Textarea
              className="bg-card/60 h-16"
              placeholder="Objetivos, contenidos, metodología..."
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
                <Clock className="h-3 w-3 inline mr-1" /> Duración (horas)
              </Label>
              <Input type="number" className="bg-card/60" value={durationHours} onChange={e => setDurationHours(parseInt(e.target.value) || 8)} min={1} max={200} />
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Modalidad</Label>
              <div className="flex gap-1">
                {COURSE_TYPES.map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setCourseType(t)}
                    className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all ${
                      courseType === t ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Categoría</Label>
            <div className="flex flex-wrap gap-1.5">
              {FUNDAE_CATEGORIES.map(cat => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategory(cat)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                    category === cat ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">
              <Users className="h-3 w-3 inline mr-1" /> Plazas Máximas
            </Label>
            <Input type="number" className="bg-card/60 w-24" value={maxStudents} onChange={e => setMaxStudents(parseInt(e.target.value) || 20)} min={1} max={500} />
          </div>

          <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80 flex items-center justify-between">
              <span className="flex items-center gap-1"><CheckSquare className="h-3 w-3 inline mr-1" /> Bonificable FUNDAE</span>
              <button
                type="button"
                onClick={() => setFundaeEligible(!fundaeEligible)}
                className={`relative w-10 h-5 rounded-full transition-colors ${fundaeEligible ? "bg-emerald-500" : "bg-muted"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${fundaeEligible ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </Label>
            {fundaeEligible && (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <p className="text-xs text-muted-foreground">Este curso será elegible para bonificación FUNDAE. Se generará el XML automáticamente.</p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80 flex items-center gap-1">
              <Upload className="h-3 w-3 inline mr-1" /> Paquete SCORM (opcional)
            </Label>
            <div className="border-2 border-dashed border-border/60 rounded-xl p-4 text-center cursor-pointer hover:border-primary/40 hover:bg-primary/5 transition-all"
              onClick={() => document.getElementById("scorm-upload")?.click()}
            >
              {scormFile ? (
                <div className="flex items-center gap-2 justify-center">
                  <FileText className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">{scormFile.name}</span>
                  <Badge className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20">{(scormFile.size / 1024 / 1024).toFixed(1)} MB</Badge>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  <Sparkles className="h-5 w-5 mx-auto mb-1 text-primary/50" />
                  Arrastra un archivo SCORM (.zip) o haz clic para subir
                </div>
              )}
              <input id="scorm-upload" type="file" accept=".zip" className="hidden" onChange={e => setScormFile(e.target.files?.[0] || null)} />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()} className="gap-2">
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {isSubmitting ? "Creando..." : "Crear Curso"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
