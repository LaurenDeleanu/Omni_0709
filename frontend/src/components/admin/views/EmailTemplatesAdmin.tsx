"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Plus, Trash2, Save, Edit, Mail } from "lucide-react";
import { toast } from "sonner";

interface Template {
  id: string; name: string; subject: string; body_html: string; is_default: boolean;
  created_at: string; updated_at: string;
}

export default function EmailTemplatesAdmin() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", subject: "", body_html: "", is_default: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchTemplates(); }, []);

  const fetchTemplates = async () => {
    try { const d = await fetchClient("/email-templates"); setTemplates(d); } catch {}
    setLoading(false);
  };

  const saveTemplate = async () => {
    if (!form.name || !form.subject) return;
    try {
      if (editing) {
        await fetchClient(`/email-templates/${editing}`, { method: "PUT", body: JSON.stringify(form) });
        toast.success("Template updated");
      } else {
        await fetchClient("/email-templates", { method: "POST", body: JSON.stringify(form) });
        toast.success("Template created");
      }
      setForm({ name: "", subject: "", body_html: "", is_default: false });
      setEditing(null);
      fetchTemplates();
    } catch (e: any) { toast.error(e.message); }
  };

  const deleteTemplate = async (id: string) => {
    try { await fetchClient(`/email-templates/${id}`, { method: "DELETE" }); toast.success("Deleted"); fetchTemplates(); } catch (e: any) { toast.error(e.message); }
  };

  const editTemplate = (t: Template) => {
    setEditing(t.id);
    setForm({ name: t.name, subject: t.subject, body_html: t.body_html, is_default: t.is_default });
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Email Templates</h1>
      <p className="text-sm text-muted-foreground mb-8">Customize notification email templates with variable interpolation</p>

      <div className="rounded-lg border bg-card p-4 mb-6">
        <h2 className="font-semibold mb-4">{editing ? "Edit Template" : "New Template"}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input placeholder="Template name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
          <input placeholder="Subject line" value={form.subject} onChange={e => setForm({...form, subject: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
        </div>
        <textarea placeholder="HTML body (use {{variable}} for interpolation)" value={form.body_html} onChange={e => setForm({...form, body_html: e.target.value})} rows={6} className="w-full bg-background border rounded-lg px-3 py-2 text-sm font-mono mb-3" />
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_default} onChange={e => setForm({...form, is_default: e.target.checked})} className="rounded" /> Default template</label>
          <button onClick={saveTemplate} className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium flex items-center gap-1"><Save size={14} /> {editing ? "Update" : "Create"}</button>
          {editing && <button onClick={() => { setEditing(null); setForm({ name: "", subject: "", body_html: "", is_default: false }); }} className="px-4 py-2 bg-muted rounded-lg text-sm">Cancel</button>}
        </div>
      </div>

      <div className="space-y-3">
        {templates.map(t => (
          <div key={t.id} className="rounded-lg border bg-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail size={16} className="text-muted-foreground" />
              <div>
                <div className="flex items-center gap-2"><span className="font-medium">{t.name}</span>{t.is_default && <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">Default</span>}</div>
                <p className="text-xs text-muted-foreground mt-0.5">{t.subject}</p>
                <p className="text-xs text-muted-foreground font-mono truncate max-w-md mt-0.5">{t.body_html.slice(0, 80)}...</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => editTemplate(t)} className="p-2 hover:bg-muted rounded-lg" title="Edit"><Edit size={14} /></button>
              <button onClick={() => deleteTemplate(t.id)} className="p-2 hover:bg-red-500/10 rounded-lg text-red-400" title="Delete"><Trash2 size={14} /></button>
            </div>
          </div>
        ))}
        {templates.length === 0 && !loading && <p className="text-center text-muted-foreground py-12">No templates yet</p>}
      </div>
    </div>
  );
}
