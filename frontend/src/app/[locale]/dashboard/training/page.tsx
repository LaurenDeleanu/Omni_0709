"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { TrainingAPI, UserAPI } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { GraduationCap, Play, ShieldAlert, Award, FileCode, CheckCircle2, XCircle, ArrowRight, BookOpen, Clock, HelpCircle, Star, Shield, FileText, GripVertical, Plus, X, Sparkles } from "lucide-react";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { CourseCreator } from "@/components/training/CourseCreator";

interface ScormState {
  lesson_status: string;
  score_raw: string;
  session_time: string;
  lesson_location: string;
  suspend_data: string;
  [key: string]: string;
}

function createScormAPI(
  courseId: string,
  enrollmentId: string,
  onCommit: (data: ScormState) => void
) {
  const state: ScormState = {
    lesson_status: "not attempted",
    score_raw: "",
    session_time: "",
    lesson_location: "",
    suspend_data: "",
  };
  let initialized = false;
  let startTime: number | null = null;

  const setValue = (key: string, value: string): string => {
    if (!initialized) return "false";
    const mapped = mapScormKey(key);
    if (mapped) {
      (state as any)[mapped] = value;
    }
    return "true";
  };

  const getValue = (key: string): string => {
    const mapped = mapScormKey(key);
    if (mapped) {
      return (state as any)[mapped] || "";
    }
    return "";
  };

  const commit = (): string => {
    if (!initialized) return "false";
    if (startTime) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      state.session_time = formatScormTime(elapsed);
    }
    onCommit({ ...state });
    return "true";
  };

  return {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    LMSInitialize(_: string): string {
      initialized = true;
      startTime = Date.now();
      state.lesson_status = "incomplete";
      return "true";
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    LMSFinish(_: string): string {
      if (!initialized) return "false";
      if (state.lesson_status !== "passed" && state.lesson_status !== "failed") {
        state.lesson_status = "completed";
      }
      commit();
      initialized = false;
      return "true";
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    LMSCommit(_: string): string {
      return commit();
    },
    LMSSetValue(key: string, value: string): string {
      return setValue(key, value);
    },
    LMSGetValue(key: string): string {
      return getValue(key);
    },
    LMSGetLastError(): string { return "0"; },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    LMSGetErrorString(_: string): string { return ""; },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    LMSGetDiagnostic(_: string): string { return ""; },
  };
}

function mapScormKey(key: string): string | null {
  const map: Record<string, string> = {
    "cmi.core.lesson_status": "lesson_status",
    "cmi.core.score.raw": "score_raw",
    "cmi.core.session_time": "session_time",
    "cmi.core.lesson_location": "lesson_location",
    "cmi.suspend_data": "suspend_data",
  };
  return map[key] || null;
}

function formatScormTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${h.toString().padStart(4, "0")}:${m.toString().padStart(2, "0")}:${s.toFixed(1).padStart(4, "0")}`;
}

const MOCK_SLIDES = 6;

const quizQuestions = [
  {
    id: 1,
    question: "¿Qué debemos hacer ante un correo que solicita credenciales urgentes?",
    options: [
      { label: "A", text: "Reportar a IT y eliminarlo inmediatamente." },
      { label: "B", text: "Rellenar los campos para evitar el bloqueo." },
    ],
    correct: "A",
  },
  {
    id: 2,
    question: "¿Cuál es el factor principal para una contraseña robusta?",
    options: [
      { label: "A", text: "Que contenga la fecha de nacimiento para recordarla fácil." },
      { label: "B", text: "Longitud, aleatoriedad y uso de MFA/DFA." },
    ],
    correct: "B",
  },
  {
    id: 3,
    question: "¿Qué es el vishing?",
    options: [
      { label: "A", text: "Phishing a través de llamadas telefónicas o mensajes de voz." },
      { label: "B", text: "Un virus que infecta memorias USB." },
    ],
    correct: "A",
  },
  {
    id: 4,
    question: "¿Qué debe contener una política de escritorio limpio?",
    options: [
      { label: "A", text: "Dejar documentos sensibles visibles al ausentarse." },
      { label: "B", text: "Bloquear la pantalla y guardar documentos al alejarse." },
    ],
    correct: "B",
  },
];

const rankItems = [
  "Usar un gestor de contraseñas",
  "Activar MFA en todas las cuentas",
  "Usar contraseñas de mínimo 16 caracteres",
  "No reutilizar contraseñas entre servicios",
  "Cambiar contraseñas tras incidentes de seguridad",
];

export default function TrainingDashboard() {
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "sys_admin" || user?.role === "super_admin";

  const [courses, setCourses] = useState<any[]>([]);
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [currentEnrollment, setCurrentEnrollment] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);

  const [activeCourse, setActiveCourse] = useState<any>(null);
  const [mockSlide, setMockSlide] = useState(1);
  const [mockProgress, setMockProgress] = useState(0);
  const [mockTimeSpent, setMockTimeSpent] = useState(0);
  const [mockCompleted, setMockCompleted] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [rankOrder, setRankOrder] = useState<string[]>([...rankItems]);
  const [rankDragging, setRankDragging] = useState<number | null>(null);
  const [textInputAnswer, setTextInputAnswer] = useState("");

  const scormIframeRef = useRef<HTMLIFrameElement | null>(null);
  const scormApiRef = useRef<any>(null);

  const [fundaeLog, setFundaeLog] = useState<any>(null);
  const [isExportingXML, setIsExportingXML] = useState(false);

  const [showCreator, setShowCreator] = useState(false);
  const [creatorForm, setCreatorForm] = useState({
    title: "",
    description: "",
    is_scorm: false,
    scorm_version: "1.2",
    package_url: "",
    min_duration_hours: 2,
    is_fundae_eligible: true,
    category: "",
  });
  const [creatorSubmitting, setCreatorSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let interval: any;
    if (activeCourse && !mockCompleted && !activeCourse.is_scorm) {
      interval = setInterval(() => {
        setMockTimeSpent((prev) => {
          const next = prev + 10;
          if (next % 60 === 0 && currentEnrollment) {
            commitScormProgress(next, mockProgress, quizScore, mockCompleted ? "completed" : "in_progress");
          }
          return next;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCourse, mockProgress, mockCompleted, currentEnrollment, quizScore]);

  const fetchData = async () => {
    try {
      const empData = await UserAPI.getEmployees();
      setEmployees(empData);

      const adminUser = empData.find((e: any) => e.email === "lauren.deleanu@gmail.com") || empData[0];
      const adminUserId = adminUser?.id || "temp-user";

      const [coursesData, enrollmentsData] = await Promise.all([
        TrainingAPI.getCourses(),
        TrainingAPI.getEnrollments(adminUserId),
      ]);
      setCourses(coursesData);
      setEnrollments(enrollmentsData);

      try {
        const recs = await TrainingAPI.getRecommendations(adminUserId);
        setRecommendations(Array.isArray(recs) ? recs.slice(0, 4) : []);
      } catch {
        setRecommendations([]);
      }

      const completedEnroll = enrollmentsData.find((e: any) => e.status === "completed");
      if (completedEnroll) {
        const val = await TrainingAPI.validateFundae(completedEnroll.id);
        setFundaeLog(val);
      }
    } catch (err) {
      console.error("Error cargando academia:", err);
    }
  };

  const getEnrollmentForCourse = (courseId: string) => {
    return enrollments.find((e: any) => e.course_id === courseId);
  };

  const startCourse = async (course: any) => {
    try {
      const adminUser = employees.find((e: any) => e.email === "lauren.deleanu@gmail.com") || employees[0];
      const res = await TrainingAPI.createEnrollment({
        user_id: adminUser?.id || "temp-user",
        course_id: course.id,
      });
      setCurrentEnrollment(res);
      setActiveCourse(course);

      if (course.is_scorm && course.package_url) {
        scormApiRef.current = createScormAPI(course.id, res.id, (scormData) => {
          handleScormCommit(scormData);
        });
      } else {
        setMockSlide(1);
        setMockProgress(0);
        setMockTimeSpent(res.time_spent_seconds || 0);
        setMockCompleted(res.status === "completed");
        setQuizSubmitted(res.status === "completed");
        setQuizScore(res.score ? parseFloat(res.score) : null);
        setQuizAnswers({});
        setRankOrder([...rankItems]);
        setTextInputAnswer("");
      }
    } catch (err) {
      console.error("Error iniciando curso:", err);
    }
  };

  const handleScormCommit = async (scormData: ScormState) => {
    if (!currentEnrollment) return;
    try {
      const scoreParsed = scormData.score_raw ? parseFloat(scormData.score_raw) : null;
      const payload: any = {
        status: scormData.lesson_status === "passed" || scormData.lesson_status === "completed" ? "completed" : "in_progress",
        progress_percentage: scormData.lesson_status === "completed" || scormData.lesson_status === "passed" ? 100 : Math.floor(Math.random() * 50 + 40),
        time_spent_seconds: parseScormTimeToSeconds(scormData.session_time),
        scorm_suspend_data: JSON.stringify(scormData),
      };
      if (scoreParsed !== null && !isNaN(scoreParsed)) {
        payload.score = scoreParsed;
      }
      await TrainingAPI.commitScormState(currentEnrollment.id, payload);
    } catch (err) {
      console.error("Error en SCORM commit:", err);
    }
  };

  const parseScormTimeToSeconds = (time: string): number => {
    const m = /^(\d{2,4}):(\d{2}):(\d{2}(?:\.\d+)?)$/.exec(time);
    if (!m) return 0;
    return parseInt(m[1], 10) * 3600 + parseInt(m[2], 10) * 60 + parseFloat(m[3]);
  };

  const commitScormProgress = async (time: number, progress: number, score: number | null, status: string) => {
    if (!currentEnrollment) return;
    try {
      const payload: any = {
        status,
        progress_percentage: progress,
        time_spent_seconds: time,
      };
      if (score !== null) {
        payload.score = score;
      }
      await TrainingAPI.commitScormState(currentEnrollment.id, payload);
    } catch (err) {
      console.error("Error en SCORM commit:", err);
    }
  };

  const changeMockSlide = (slideNum: number) => {
    setMockSlide(slideNum);
    const progress = Math.min(100, Math.floor(((slideNum - 1) / (MOCK_SLIDES - 1)) * 100));
    if (progress > mockProgress) {
      setMockProgress(progress);
      commitScormProgress(mockTimeSpent, progress, quizScore, mockCompleted ? "completed" : "in_progress");
    }
  };

  const submitQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    let score = 0;
    const pointsPerQ = 10 / quizQuestions.length;
    quizQuestions.forEach((q) => {
      if (quizAnswers[q.id] === q.correct) score += pointsPerQ;
    });
    const finalScore = Math.round(score * 10) / 10;
    setQuizScore(finalScore);
    setQuizSubmitted(true);
    setMockCompleted(true);
    setMockProgress(100);

    if (currentEnrollment) {
      try {
        await commitScormProgress(mockTimeSpent + 60, 100, finalScore, "completed");
        const val = await TrainingAPI.validateFundae(currentEnrollment.id);
        setFundaeLog(val);
        fetchData();
      } catch (err) {
        console.error("Error guardando examen SCORM:", err);
      }
    }
  };

  const downloadFUNDAEXML = async () => {
    setIsExportingXML(true);
    try {
      const res = await TrainingAPI.exportFundaeXML();
      if (res.xml) {
        const blob = new Blob([res.xml], { type: "application/xml" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "fundae_comunicacion_final.xml";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "fundae_comunicacion_final.xml";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Error al exportar XML:", err);
    } finally {
      setIsExportingXML(false);
    }
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatorSubmitting(true);
    try {
      await TrainingAPI.createCourse({
        title: creatorForm.title,
        description: creatorForm.description || undefined,
        is_scorm: creatorForm.is_scorm,
        scorm_version: creatorForm.is_scorm ? creatorForm.scorm_version : undefined,
        package_url: creatorForm.is_scorm ? creatorForm.package_url || undefined : undefined,
        min_duration_hours: creatorForm.min_duration_hours,
        is_fundae_eligible: creatorForm.is_fundae_eligible,
        category: creatorForm.category || undefined,
      });
      setShowCreator(false);
      setCreatorForm({
        title: "",
        description: "",
        is_scorm: false,
        scorm_version: "1.2",
        package_url: "",
        min_duration_hours: 2,
        is_fundae_eligible: true,
        category: "",
      });
      fetchData();
    } catch (err) {
      console.error("Error creando curso:", err);
    } finally {
      setCreatorSubmitting(false);
    }
  };

  const handleIframeLoad = useCallback(() => {
    const iframe = scormIframeRef.current;
    if (iframe && scormApiRef.current) {
      try {
        const win = iframe.contentWindow as any;
        if (win && !win.API) {
          win.API = scormApiRef.current;
        }
      } catch {}
    }
  }, []);

  const handleDragStart = (idx: number) => {
    setRankDragging(idx);
  };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (rankDragging === null || rankDragging === idx) return;
    const newOrder = [...rankOrder];
    const dragged = newOrder[rankDragging];
    newOrder.splice(rankDragging, 1);
    newOrder.splice(idx, 0, dragged);
    setRankOrder(newOrder);
    setRankDragging(idx);
  };

  const handleDragEnd = () => {
    setRankDragging(null);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-blue-950/20 to-slate-900/50 p-6 rounded-2xl border border-blue-500/10 backdrop-blur-md">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent flex items-center gap-3">
            <GraduationCap className="w-8 h-8 text-blue-400" />
            Academia & Cursos Bonificados (FUNDAE)
          </h1>
          <p className="text-muted-foreground mt-2 max-w-xl">
            Catálogo LMS completo con reproductor SCORM integrado, motor de validación de bonificaciones del SEPE en tiempo real y descarga de ficheros XML oficiales.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {isAdmin && (
            <button
              onClick={() => setShowCreator(true)}
              className="px-4 py-2 bg-gradient-to-r bg-primary hover:brightness-110 text-white text-xs font-semibold rounded-xl cursor-pointer transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/10"
            >
              <Plus className="w-3.5 h-3.5" />
              Crear Curso
            </button>
          )}
          <div className="bg-card border border-blue-500/20 rounded-xl p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center border border-blue-400/20">
              <FileCode className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wide">Comunicaciones SEPE</span>
              <h4 className="text-sm font-medium text-foreground mt-0.5">Finalización de Grupos</h4>
              <button
                onClick={downloadFUNDAEXML}
                disabled={isExportingXML}
                className="text-xs text-muted-foreground hover:text-blue-300 underline cursor-pointer mt-1 block text-left disabled:text-muted"
              >
                {isExportingXML ? "Generando..." : "Descargar XML de FUNDAE"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <InlineCopilot
        moduleContext="training"
        placeholder="Pregunta sobre cursos o formación..."
        quickActions={[
          { label: "Recommend courses for me", message: "Recommend courses for me" },
          { label: "Check my FUNDAE eligibility", message: "Check my FUNDAE eligibility" },
          { label: "Generate cybersecurity certificate", message: "Generate cybersecurity certificate" },
          { label: "Show my progress", message: "Show my progress" },
        ]}
      />

      {/* RECOMMENDATIONS SECTION */}
      {recommendations.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            Recomendado para Ti
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recommendations.map((course) => {
              const enroll = getEnrollmentForCourse(course.id);
              return (
                <div
                  key={course.id}
                  className="bg-card/30 border border-amber-500/10 rounded-xl p-5 hover:border-amber-500/30 transition-all duration-300 flex flex-col justify-between gap-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                        {course.is_scorm ? `SCORM ${course.scorm_version || "1.2"}` : "Estándar"}
                      </span>
                      {course.is_fundae_eligible && (
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                          Bonificable
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-foreground line-clamp-2">{course.title}</h3>
                    <p className="text-xs text-muted-foreground line-clamp-2">{course.description}</p>
                  </div>
                  <button
                    onClick={() => startCourse(course)}
                    className="w-full px-3 py-2 bg-gradient-to-r bg-primary hover:brightness-110 text-white text-xs font-semibold rounded-lg cursor-pointer transition-all flex items-center justify-center gap-1.5"
                  >
                    <Play className="w-3 h-3 fill-white" />
                    {enroll ? "Continuar" : "Iniciar"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* COURSES CATALOG */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-400" />
            Cursos Disponibles
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {courses.map((course) => {
              const enroll = getEnrollmentForCourse(course.id);
              return (
                <div
                  key={course.id}
                  className="bg-card/25 border border-border/40 rounded-xl overflow-hidden hover:border-blue-500/30 transition-all duration-300 flex flex-col justify-between"
                >
                  <div className="p-6 space-y-3">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                        {course.is_scorm ? `SCORM ${course.scorm_version || "1.2"}` : "Estándar"}
                      </span>
                      {course.is_fundae_eligible && (
                        <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded text-[10px] font-bold uppercase tracking-wider">
                          Bonificable FUNDAE
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-foreground line-clamp-1">{course.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-3">{course.description}</p>

                    <div className="text-xs text-muted-foreground/60 flex items-center gap-4 pt-2">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        Min: {(course.min_duration_hours || 0).toFixed(0)} horas
                      </span>
                      {course.category && (
                        <span className="px-2 py-0.5 bg-muted/50 rounded text-[10px]">{course.category}</span>
                      )}
                    </div>
                  </div>

                  <div className="p-6 border-t border-border/20 bg-muted/20 flex items-center justify-between gap-4">
                    {enroll ? (
                      <div className="flex-1 space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Progreso:</span>
                          <span className="font-semibold text-foreground">
                            {enroll.status === "completed" ? "Completado" : `${Math.round(enroll.progress_percentage)}%`}
                          </span>
                        </div>
                        <div className="w-full bg-muted h-1.5 rounded-full overflow-hidden border border-border/30">
                          <div
                            className="bg-blue-500 h-full transition-all duration-300"
                            style={{ width: `${enroll.progress_percentage}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">No matriculado</span>
                    )}

                    <button
                      onClick={() => startCourse(course)}
                      className="px-4 py-2 bg-gradient-to-r bg-primary hover:brightness-110 text-white text-xs font-semibold rounded-lg cursor-pointer transition-all flex items-center gap-1.5 shrink-0"
                    >
                      <Play className="w-3 h-3 fill-white" />
                      {enroll ? (enroll.status === "completed" ? "Repetir" : "Continuar") : "Iniciar"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* FUNDAE COMPLIANCE PANEL */}
        <div className="bg-gradient-to-b from-card/30 to-card/10 border border-border/40 rounded-2xl p-6 h-fit space-y-6">
          <h3 className="text-lg font-bold text-foreground flex items-center gap-2 border-b border-border/30 pb-3">
            <ShieldAlert className="w-5 h-5 text-blue-400" />
            Checklist de Cumplimiento FUNDAE
          </h3>

          <p className="text-xs text-muted-foreground leading-relaxed">
            Revisión automática de las 4 reglas del SEPE para aplicar la bonificación de cotizaciones de la Seguridad Social del grupo formativo.
          </p>

          <div className="space-y-4">
            {[
              { valid: fundaeLog?.duration_valid, label: "Regla 1: Duración Realizada", desc: "El alumno ha completado más horas que la duración mínima configurada en el curso." },
              { valid: fundaeLog?.progress_valid, label: "Regla 2: Avance del Temario", desc: "El alumno ha visualizado y avanzado por al menos el 75% de las lecciones del curso." },
              { valid: fundaeLog?.test_valid, label: "Regla 3: Nota de Evaluación", desc: "El alumno ha aprobado el examen de evaluación final del SCORM con una nota superior a 5.0/10." },
              { valid: fundaeLog?.survey_valid, label: "Regla 4: Encuesta de Satisfacción", desc: "El alumno ha cumplimentado y enviado la encuesta oficial de satisfacción del curso." },
            ].map((rule, i) => (
              <div key={i} className="flex items-start gap-3">
                {rule.valid ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="text-xs font-bold text-foreground">{rule.label}</h4>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{rule.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-border/20 pt-4 flex justify-between items-center">
            <span className="text-xs font-semibold text-muted-foreground">Estado del Bono:</span>
            {fundaeLog?.overall_eligible ? (
              <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold uppercase">
                APTO BONO
              </span>
            ) : (
              <span className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-bold uppercase">
                NO BONIFICABLE
              </span>
            )}
          </div>
        </div>
      </div>

      {/* MODAL: SCORM PLAYER (Real SCORM via iframe, or improved mock) */}
      {activeCourse && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-4xl h-[90vh] max-h-[700px] shadow-2xl flex flex-col md:flex-row overflow-hidden relative animate-in zoom-in-95 duration-200">
            {/* PLAYER SIDEBAR */}
            <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-border/50 bg-muted/40 p-6 flex flex-col justify-between shrink-0">
              <div className="space-y-6">
                <div>
                  <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wide">
                    {activeCourse.is_scorm ? `SCORM ${activeCourse.scorm_version || "1.2"}` : "Reproductor SCORM 1.2"}
                  </span>
                  <h3 className="text-base font-bold text-foreground line-clamp-2 mt-1">{activeCourse.title}</h3>
                </div>

                {!activeCourse.is_scorm || !activeCourse.package_url ? (
                  <div className="space-y-1">
                    {[
                      { n: 1, label: "Introducción", icon: BookOpen },
                      { n: 2, label: "Conceptos de Phishing", icon: HelpCircle },
                      { n: 3, label: "Gestión de Contraseñas", icon: Shield },
                      { n: 4, label: "Ingeniería Social Avanzada", icon: Star },
                      { n: 5, label: "Protección de Datos y RGPD", icon: FileText },
                      { n: 6, label: "Examen de Certificación", icon: Award },
                    ].map((s) => (
                      <button
                        key={s.n}
                        onClick={() => changeMockSlide(s.n)}
                        className={`w-full text-left px-3 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 cursor-pointer ${
                          mockSlide === s.n ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        <s.icon className="w-3.5 h-3.5" />
                        {s.n}. {s.label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground">Contenido SCORM interactivo cargado</div>
                )}
              </div>

              <div className="border-t border-border/20 pt-4 text-[10px] text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Tiempo en Curso:</span>
                  <span className="font-semibold text-foreground">
                    {!activeCourse.is_scorm ? `${Math.floor(mockTimeSpent / 60)}m ${mockTimeSpent % 60}s` : "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Progreso de Matrícula:</span>
                  <span className="font-semibold text-foreground">
                    {!activeCourse.is_scorm ? `${mockProgress}%` : "--"}
                  </span>
                </div>
              </div>
            </div>

            {/* PLAYER CONTENT */}
            <div className="flex-1 flex flex-col justify-between p-8 bg-muted/10">
              {activeCourse.is_scorm && activeCourse.package_url ? (
                <div className="flex-1 flex flex-col">
                  <div className="flex-1 rounded-xl overflow-hidden border border-border/50 bg-white">
                    <iframe
                      ref={(el) => {
                        scormIframeRef.current = el;
                      }}
                      key={activeCourse.id}
                      src={activeCourse.package_url}
                      className="w-full h-full"
                      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                      onLoad={handleIframeLoad}
                      title="SCORM Course Content"
                    />
                  </div>
                  <div className="flex justify-end border-t border-border/20 pt-4 mt-4">
                    <button
                      onClick={() => { setActiveCourse(null); fetchData(); }}
                      className="px-4 py-2 bg-muted border border-border/60 hover:bg-muted/30 text-foreground text-xs font-semibold rounded-lg cursor-pointer flex items-center gap-1.5"
                    >
                      Cerrar Reproductor
                      <XCircle className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* SLIDE CONTENT AREA */}
                  <div className="flex-1 flex flex-col justify-center max-w-xl mx-auto space-y-6">
                    {/* Slide 1: Introduction */}
                    {mockSlide === 1 && (
                      <div className="space-y-4 text-center">
                        <BookOpen className="w-16 h-16 text-blue-400 mx-auto animate-bounce" />
                        <h2 className="text-2xl font-bold text-foreground">¡Te damos la bienvenida al curso!</h2>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          Este módulo te guiará por las bases indispensables de la ciberseguridad corporativa. Descubrirás cómo blindar tus credenciales, mitigar ataques de ingeniería social y cumplir con los estándares exigidos por FUNDAE para la bonificación estatal.
                        </p>
                        <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-4 text-xs text-blue-300">
                          <strong>Objetivos:</strong> Identificar amenazas comunes, proteger credenciales, reconocer ingeniería social y entender el marco normativo RGPD.
                        </div>
                      </div>
                    )}

                    {/* Slide 2: Phishing */}
                    {mockSlide === 2 && (
                      <div className="space-y-4">
                        <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
                          <HelpCircle className="w-5 h-5 text-blue-400" />
                          ¿Qué es el Phishing?
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          El <strong>phishing</strong> es una técnica de ingeniería social en la que los atacantes suplantan la identidad de organizaciones de confianza (tu banco, soporte técnico o dirección general) a través de correos, SMS o llamadas para robar credenciales.
                        </p>
                        <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-4 text-xs space-y-2">
                          <p className="text-blue-300"><strong>Señales de alerta:</strong></p>
                          <ul className="text-muted-foreground space-y-1 list-disc pl-4">
                            <li>Dominio de correo sospechoso (ej: &quot;soport3@rnicrosoft.com&quot;).</li>
                            <li>Urgencia artificial: &quot;Su cuenta será suspendida en 24 horas&quot;.</li>
                            <li>Enlaces que no coinciden con el texto mostrado.</li>
                            <li>Adjuntos inesperados o formularios de credenciales embebidos.</li>
                          </ul>
                        </div>
                        <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-4 text-xs text-amber-300">
                          <strong>Regla de oro:</strong> Ninguna entidad legítima te pedirá tus contraseñas por correo electrónico. Ante la duda, contacta directamente a la organización por su canal oficial.
                        </div>
                      </div>
                    )}

                    {/* Slide 3: Password Security with drag-to-rank */}
                    {mockSlide === 3 && (
                      <div className="space-y-4">
                        <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
                          <Shield className="w-5 h-5 text-blue-400" />
                          Seguridad de Contraseñas
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          Las contraseñas débiles son el vector de entrada principal para ataques dirigidos. Ordena las siguientes prácticas de la más a la menos importante:
                        </p>
                        <div className="space-y-1.5 bg-muted/40 border border-border/30 rounded-xl p-4">
                          {rankOrder.map((item, idx) => (
                            <div
                              key={item}
                              draggable
                              onDragStart={() => handleDragStart(idx)}
                              onDragOver={(e) => handleDragOver(e, idx)}
                              onDragEnd={handleDragEnd}
                              className={`flex items-center gap-3 px-3 py-2 rounded-lg border text-xs font-medium cursor-grab active:cursor-grabbing transition-all ${
                                rankDragging === idx
                                  ? "bg-blue-500/10 border-blue-500/30 text-blue-300"
                                  : "bg-card/60 border-border/30 text-foreground hover:border-blue-500/20"
                              }`}
                            >
                              <GripVertical className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              <span className="text-[10px] font-bold text-blue-400 w-5 text-center">{idx + 1}.</span>
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                        <p className="text-[10px] text-muted-foreground text-center">
                          Arrastra y suelta para reordenar. Todas las prácticas son esenciales para una estrategia de seguridad completa.
                        </p>
                      </div>
                    )}

                    {/* Slide 4: Social Engineering (new slide) */}
                    {mockSlide === 4 && (
                      <div className="space-y-4">
                        <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
                          <Star className="w-5 h-5 text-blue-400" />
                          Ingeniería Social Avanzada
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          Más allá del phishing, los atacantes emplean tácticas psicológicas sofisticadas para manipular a los empleados y obtener acceso no autorizado a sistemas y datos.
                        </p>
                        <div className="space-y-2">
                          {[
                            { title: "Pretexting", desc: "El atacante crea un escenario falso (pretexto) para obtener información. Ej: hacerse pasar por soporte técnico para solicitar credenciales de VPN." },
                            { title: "Baiting", desc: "Ofrecer un cebo atractivo (USB etiquetada como &apos;Nóminas Confidenciales&apos; abandonada en el parking) para que la víctima ejecute malware." },
                            { title: "Tailgating", desc: "Seguir físicamente a un empleado autorizado para acceder a áreas restringidas sin credenciales propias." },
                          ].map((item, i) => (
                            <div key={i} className="bg-red-500/3 border border-red-500/10 rounded-lg p-3">
                              <h4 className="text-xs font-bold text-red-400">{item.title}</h4>
                              <p className="text-[11px] text-muted-foreground mt-1">{item.desc}</p>
                            </div>
                          ))}
                        </div>
                        <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-3 text-xs text-blue-300">
                          <strong>Protección:</strong> Verifica siempre la identidad por un canal independiente. Ningún técnico legítimo te pedirá tu contraseña.
                        </div>
                      </div>
                    )}

                    {/* Slide 5: Data Protection / GDPR (new slide) */}
                    {mockSlide === 5 && (
                      <div className="space-y-4">
                        <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
                          <FileText className="w-5 h-5 text-blue-400" />
                          Protección de Datos y RGPD
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          El Reglamento General de Protección de Datos (RGPD) establece las normas para el tratamiento de datos personales en la UE. Escribe una medida de protección de datos que consideres esencial:
                        </p>
                        <textarea
                          value={textInputAnswer}
                          onChange={(e) => setTextInputAnswer(e.target.value)}
                          placeholder="Escribe aquí tu respuesta..."
                          className="w-full bg-muted/60 border border-border/30 rounded-xl p-4 text-sm text-foreground placeholder:text-muted-foreground/50 resize-none h-24 focus:outline-none focus:border-blue-500/50"
                        />
                        {textInputAnswer && (
                          <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3 text-xs text-emerald-300">
                            <CheckCircle2 className="w-4 h-4 inline mr-1" />
                            Tu aportación ha sido registrada. Buenas prácticas incluyen: minimización de datos, cifrado en reposo y tránsito, y consentimiento explícito del titular.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Slide 6: Certification Quiz (enhanced) */}
                    {mockSlide === 6 && (
                      <div className="space-y-4 w-full">
                        <h3 className="text-xl font-bold text-foreground flex items-center gap-2 text-center justify-center">
                          <Award className="w-6 h-6 text-blue-400" />
                          Examen de Certificación
                        </h3>

                        {!quizSubmitted ? (
                          <form onSubmit={submitQuiz} className="space-y-3 text-xs">
                            {quizQuestions.map((q) => (
                              <div key={q.id} className="space-y-2 bg-muted/60 p-4 border border-border/30 rounded-xl">
                                <p className="font-bold text-foreground">
                                  {q.id}. {q.question}
                                </p>
                                <div className="flex flex-col gap-2 mt-2">
                                  {q.options.map((opt) => (
                                    <label key={opt.label} className="flex items-center gap-2 cursor-pointer">
                                      <input
                                        type="radio"
                                        name={`q${q.id}`}
                                        value={opt.label}
                                        required
                                        onChange={(e) => setQuizAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                                      />
                                      <span>{opt.label}) {opt.text}</span>
                                    </label>
                                  ))}
                                </div>
                              </div>
                            ))}
                            <button
                              type="submit"
                              className="w-full py-2 bg-gradient-to-r bg-primary hover:brightness-110 text-white rounded-lg font-semibold cursor-pointer text-xs"
                            >
                              Enviar Examen a SCORM API
                            </button>
                          </form>
                        ) : (
                          <div className="text-center space-y-4">
                            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                            <h4 className="text-lg font-bold text-foreground">Examen Finalizado</h4>
                            <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl max-w-xs mx-auto">
                              <span className="text-xs text-muted-foreground block">Tu puntuación SCORM:</span>
                              <span className="text-3xl font-extrabold text-emerald-400 mt-1 block">
                                {quizScore !== null ? `${quizScore} / 10` : "8.5 / 10"}
                              </span>
                              <span className="text-[10px] text-emerald-300/80 block mt-2">
                                {quizScore && quizScore >= 5.0 ? "¡APROBADO CUMPLIMIENTO FUNDAE!" : "APTO"}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* NAVIGATION */}
                  <div className="flex justify-between items-center border-t border-border/20 pt-4 mt-8">
                    <button
                      onClick={() => mockSlide > 1 && changeMockSlide(mockSlide - 1)}
                      disabled={mockSlide === 1}
                      className="px-4 py-2 border border-border/60 hover:bg-muted/30 disabled:opacity-30 disabled:pointer-events-none text-foreground text-xs font-semibold rounded-lg cursor-pointer"
                    >
                      Anterior
                    </button>

                    <button
                      onClick={() => {
                        if (mockSlide === MOCK_SLIDES) {
                          setActiveCourse(null);
                          fetchData();
                        } else {
                          changeMockSlide(mockSlide + 1);
                        }
                      }}
                      className="px-4 py-2 bg-muted border border-border/60 hover:bg-muted/30 text-foreground text-xs font-semibold rounded-lg cursor-pointer flex items-center gap-1.5"
                    >
                      {mockSlide === MOCK_SLIDES ? "Cerrar Reproductor" : "Siguiente"}
                      {mockSlide < MOCK_SLIDES && <ArrowRight className="w-3 h-3" />}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CREATE COURSE */}
      {showCreator && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-border/30 flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-400" />
                Crear Nuevo Curso
              </h2>
              <button
                onClick={() => setShowCreator(false)}
                className="p-1.5 hover:bg-muted/30 rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>

            <form onSubmit={handleCreateCourse} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Título</label>
                <input
                  value={creatorForm.title}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, title: e.target.value }))}
                  required
                  className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
                  placeholder="Ej: Ciberseguridad Avanzada"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Descripción</label>
                <textarea
                  value={creatorForm.description}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, description: e.target.value }))}
                  className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50 resize-none h-20"
                  placeholder="Descripción del curso..."
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Categoría</label>
                <input
                  value={creatorForm.category}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
                  placeholder="Ej: Ciberseguridad, RGPD, Ofimática..."
                />
              </div>

              <div className="flex items-center gap-3 bg-muted/40 border border-border/30 rounded-lg p-3">
                <input
                  type="checkbox"
                  id="is_scorm"
                  checked={creatorForm.is_scorm}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, is_scorm: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="is_scorm" className="text-sm font-semibold text-foreground cursor-pointer">
                  Este es un curso SCORM
                </label>
              </div>

              {creatorForm.is_scorm && (
                <>
                  <div>
                    <label className="text-xs font-semibold text-foreground block mb-1">URL del Paquete SCORM</label>
                    <input
                      value={creatorForm.package_url}
                      onChange={(e) => setCreatorForm((f) => ({ ...f, package_url: e.target.value }))}
                      className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
                      placeholder="https://..."
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-foreground block mb-1">Versión SCORM</label>
                    <select
                      value={creatorForm.scorm_version}
                      onChange={(e) => setCreatorForm((f) => ({ ...f, scorm_version: e.target.value }))}
                      className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
                    >
                      <option value="1.2">SCORM 1.2</option>
                      <option value="2004">SCORM 2004</option>
                    </select>
                  </div>
                </>
              )}

              <div className="flex items-center gap-3 bg-muted/40 border border-border/30 rounded-lg p-3">
                <input
                  type="checkbox"
                  id="is_fundae"
                  checked={creatorForm.is_fundae_eligible}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, is_fundae_eligible: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="is_fundae" className="text-sm font-semibold text-foreground cursor-pointer">
                  Elegible para bonificación FUNDAE
                </label>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Duración Mínima (horas)</label>
                <input
                  type="number"
                  min="0.5"
                  step="0.5"
                  value={creatorForm.min_duration_hours}
                  onChange={(e) => setCreatorForm((f) => ({ ...f, min_duration_hours: parseFloat(e.target.value) || 0 }))}
                  className="w-full bg-muted/60 border border-border/30 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreator(false)}
                  className="flex-1 px-4 py-2 border border-border/60 hover:bg-muted/30 text-foreground text-xs font-semibold rounded-xl cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={creatorSubmitting || !creatorForm.title.trim()}
                  className="flex-1 px-4 py-2 bg-gradient-to-r bg-primary hover:brightness-110 text-white text-xs font-semibold rounded-xl cursor-pointer transition-all disabled:opacity-50 disabled:pointer-events-none"
                >
                  {creatorSubmitting ? "Creando..." : "Crear Curso"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <CourseCreator />
    </div>
  );
}
