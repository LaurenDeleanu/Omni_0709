"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  Building2,
  MapPin,
  Briefcase,
  Clock,
  Search,
  ChevronRight,
  Send,
  X,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

interface PublicJob {
  id: string;
  title: string;
  department?: string;
  location?: string;
  employment_type?: string;
  description?: string;
  posted_at?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";

const typeLabels: Record<string, string> = {
  "full-time": "Tiempo completo",
  "part-time": "Tiempo parcial",
  contract: "Contrato",
  freelance: "Freelance",
  internship: "Prácticas",
};

export default function CareersPage() {
  const [jobs, setJobs] = useState<PublicJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const [selectedJob, setSelectedJob] = useState<PublicJob | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  const [formModal, setFormModal] = useState(false);
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    cover_letter: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState("");
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnimIn(true), 50);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/hire/public/jobs`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to fetch jobs");
        return r.json();
      })
      .then((data) => {
        setJobs(data || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const departments = useMemo(() => {
    const set = new Set(jobs.map((j) => j.department).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [jobs]);

  const locations = useMemo(() => {
    const set = new Set(jobs.map((j) => j.location).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [jobs]);

  const employmentTypes = useMemo(() => {
    const set = new Set(jobs.map((j) => j.employment_type).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    return jobs.filter((j) => {
      if (search) {
        const s = search.toLowerCase();
        if (
          !j.title.toLowerCase().includes(s) &&
          !(j.department || "").toLowerCase().includes(s) &&
          !(j.location || "").toLowerCase().includes(s)
        )
          return false;
      }
      if (deptFilter && j.department !== deptFilter) return false;
      if (locationFilter && j.location !== locationFilter) return false;
      if (typeFilter && j.employment_type !== typeFilter) return false;
      return true;
    });
  }, [jobs, search, deptFilter, locationFilter, typeFilter]);

  const openDetail = async (job: PublicJob) => {
    setSelectedJob(null);
    setShowDetail(true);
    try {
      const r = await fetch(`${API_BASE}/hire/public/jobs/${job.id}`);
      if (!r.ok) throw new Error("Not found");
      const detail = await r.json();
      setSelectedJob(detail);
    } catch {
      setSelectedJob(job);
    }
  };

  const closeDetail = () => {
    setShowDetail(false);
    setSelectedJob(null);
  };

  const openApply = (job: PublicJob) => {
    setSelectedJob(job);
    setFormModal(true);
    setFormData({ first_name: "", last_name: "", email: "", phone: "", cover_letter: "" });
    setSubmitted(false);
    setFormError("");
  };

  const handleApplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!formData.first_name || !formData.last_name || !formData.email) {
      setFormError("First name, last name, and email are required.");
      return;
    }
    setSubmitting(true);
    try {
      const r = await fetch(`${API_BASE}/hire/public/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: selectedJob?.id,
          ...formData,
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || "Submission failed");
      }
      setSubmitted(true);
    } catch (err: any) {
      setFormError(err.message || "Error submitting application");
    } finally {
      setSubmitting(false);
    }
  };

  const displayJob = selectedJob;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* ── NAV ──────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-white" />
              </div>
              <span className="text-white font-bold text-lg">SuccessCore</span>
              <span className="text-indigo-400 text-xs font-semibold hidden sm:inline ml-1">Careers</span>
            </Link>
            <Link
              href="/login"
              className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              Employee login
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────── */}
      <section className="relative pt-16 pb-8 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-[500px] h-[500px] bg-indigo-600/8 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div
            className={`transition-all duration-700 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 mb-6">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span className="text-indigo-300 text-sm font-medium">We are hiring</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold mb-4">
              Build the future{" "}
              <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                with us
              </span>
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Explore open positions at SuccessCore and join a team that is redefining
              HR technology with AI agents.
            </p>
          </div>
        </div>
      </section>

      {/* ── FILTERS ─────────────────────────────────────────── */}
      <section className="pb-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row gap-3 bg-white/3 border border-white/5 rounded-xl p-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search jobs..."
                className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="">All departments</option>
              {departments.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <select
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="">All locations</option>
              {locations.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="">All types</option>
              {employmentTypes.map((t) => (
                <option key={t} value={t}>{typeLabels[t] || t}</option>
              ))}
            </select>
            {(search || deptFilter || locationFilter || typeFilter) && (
              <button
                onClick={() => {
                  setSearch("");
                  setDeptFilter("");
                  setLocationFilter("");
                  setTypeFilter("");
                }}
                className="text-slate-400 hover:text-white text-sm transition-colors px-3"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </section>

      {/* ── JOB LIST ────────────────────────────────────────── */}
      <section className="pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="text-center py-20">
              <p className="text-slate-400 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="text-indigo-400 hover:text-indigo-300 text-sm"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && filteredJobs.length === 0 && (
            <div className="text-center py-20">
              <Briefcase className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg mb-2">No positions found</p>
              <p className="text-slate-600 text-sm">
                {jobs.length === 0
                  ? "There are no open positions at this time. Check back soon."
                  : "Try adjusting your search or filters."}
              </p>
            </div>
          )}

          {!loading && !error && filteredJobs.length > 0 && (
            <div className="space-y-3">
              <p className="text-slate-500 text-sm mb-4">{filteredJobs.length} position{filteredJobs.length !== 1 ? "s" : ""} found</p>
              {filteredJobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-white/3 border border-white/5 hover:border-white/10 rounded-xl p-5 transition-all duration-200 group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <h3 className="text-white font-semibold text-lg group-hover:text-indigo-300 transition-colors">
                        {job.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3">
                        {job.department && (
                          <span className="inline-flex items-center gap-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-2.5 py-0.5 text-indigo-300 text-xs font-medium">
                            <Briefcase className="h-3 w-3" />
                            {job.department}
                          </span>
                        )}
                        {job.location && (
                          <span className="inline-flex items-center gap-1.5 text-slate-400 text-xs">
                            <MapPin className="h-3 w-3" />
                            {job.location}
                          </span>
                        )}
                        {job.employment_type && (
                          <span className="inline-flex items-center gap-1.5 text-slate-400 text-xs">
                            <Clock className="h-3 w-3" />
                            {typeLabels[job.employment_type] || job.employment_type}
                          </span>
                        )}
                      </div>
                      {job.description && (
                        <p className="text-slate-500 text-sm leading-relaxed line-clamp-2">{job.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => openApply(job)}
                        className="py-2.5 px-5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-indigo-500/25"
                      >
                        Apply
                      </button>
                      <button
                        onClick={() => openDetail(job)}
                        className="py-2.5 px-4 bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 text-sm rounded-lg transition-colors flex items-center gap-1"
                      >
                        Details
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── DETAIL MODAL ────────────────────────────────────── */}
      {showDetail && displayJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={closeDetail}>
          <div
            className="bg-slate-900 border border-white/10 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-2xl font-bold text-white">{displayJob.title}</h2>
              <button onClick={closeDetail} className="text-slate-400 hover:text-white transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex flex-wrap items-center gap-3 mb-6">
              {displayJob.department && (
                <span className="inline-flex items-center gap-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3 py-1 text-indigo-300 text-sm font-medium">
                  <Briefcase className="h-3.5 w-3.5" />
                  {displayJob.department}
                </span>
              )}
              {displayJob.location && (
                <span className="inline-flex items-center gap-1.5 text-slate-400 text-sm">
                  <MapPin className="h-3.5 w-3.5" />
                  {displayJob.location}
                </span>
              )}
              {displayJob.employment_type && (
                <span className="inline-flex items-center gap-1.5 text-slate-400 text-sm">
                  <Clock className="h-3.5 w-3.5" />
                  {typeLabels[displayJob.employment_type] || displayJob.employment_type}
                </span>
              )}
            </div>
            {displayJob.description && (
              <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap mb-6">
                {displayJob.description}
              </div>
            )}
            <button
              onClick={() => {
                closeDetail();
                openApply(displayJob);
              }}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/25"
            >
              Apply for this position
            </button>
          </div>
        </div>
      )}

      {/* ── APPLY MODAL ─────────────────────────────────────── */}
      {formModal && displayJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setFormModal(false)}>
          <div
            className="bg-slate-900 border border-white/10 rounded-2xl max-w-md w-full max-h-[85vh] overflow-y-auto p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-white">Apply</h2>
                <p className="text-slate-400 text-sm mt-0.5">{displayJob.title}</p>
              </div>
              <button onClick={() => setFormModal(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>

            {submitted ? (
              <div className="text-center py-8">
                <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto mb-4" />
                <h3 className="text-white font-bold text-lg mb-2">Application submitted</h3>
                <p className="text-slate-400 text-sm mb-6">We will review your application and get back to you soon.</p>
                <button
                  onClick={() => setFormModal(false)}
                  className="w-full py-2.5 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            ) : (
              <form onSubmit={handleApplySubmit} className="space-y-4">
                {formError && (
                  <div className="bg-red-500/10 border border-red-500/20 text-red-300 text-xs rounded-xl px-3 py-2">
                    {formError}
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-slate-300 text-xs font-medium">First name *</label>
                    <input
                      type="text"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      required
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                      placeholder="John"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-slate-300 text-xs font-medium">Last name *</label>
                    <input
                      type="text"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      required
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                      placeholder="Doe"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 text-xs font-medium">Email *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    placeholder="john@example.com"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 text-xs font-medium">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    placeholder="+34 600 000 000"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 text-xs font-medium">Cover letter</label>
                  <textarea
                    value={formData.cover_letter}
                    onChange={(e) => setFormData({ ...formData, cover_letter: e.target.value })}
                    rows={4}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                    placeholder="Tell us why you are interested in this role..."
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      Submit application
                      <Send className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── FOOTER ──────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-10 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 text-slate-600 text-sm mb-2">
            <Building2 className="h-3.5 w-3.5" />
            <span>Powered by SuccessCore</span>
          </div>
          <p className="text-slate-700 text-xs">SuccessCore HR © 2026 · HR platform with AI agents</p>
        </div>
      </footer>
    </div>
  );
}
