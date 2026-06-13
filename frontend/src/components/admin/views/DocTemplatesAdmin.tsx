"use client";

import { useState } from "react";
import { fetchClient } from "@/lib/api/client";
import { FileText, Download, Check } from "lucide-react";
import { toast } from "sonner";

const TEMPLATES = [
  { id: "offer_letter", name: "Job Offer Letter", fields: ["candidate_name", "position", "salary", "start_date", "company_name", "manager_name"] },
  { id: "vacation_approval", name: "Vacation Approval", fields: ["employee_name", "start_date", "end_date", "days", "approved_by"] },
  { id: "expense_report", name: "Expense Report", fields: ["employee_name", "period", "total_amount", "categories_summary", "approved_by"] },
];

export default function DocTemplatesAdmin() {
  const [selected, setSelected] = useState(TEMPLATES[0].id);
  const [data, setData] = useState<Record<string, string>>({});

  const template = TEMPLATES.find(t => t.id === selected)!;

  const generate = async () => {
    try {
      const resp = await fetch(`http://127.0.0.1:8080/api/v1/admin/document-templates/${selected}/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify(data),
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${selected}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF generated");
    } catch (e: any) { toast.error("Failed to generate PDF"); }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Document Templates</h1>
      <p className="text-sm text-muted-foreground mb-8">Generate PDF documents from templates</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3">
          {TEMPLATES.map(t => (
            <button key={t.id} onClick={() => { setSelected(t.id); setData({}); }} className={`w-full rounded-lg border p-4 text-left transition-colors ${selected === t.id ? "border-primary bg-primary/5" : "bg-card hover:bg-muted/50"}`}>
              <div className="flex items-center gap-2"><FileText size={16} className="text-muted-foreground" /><span className="font-medium">{t.name}</span></div>
              <p className="text-xs text-muted-foreground mt-1">{t.fields.join(", ")}</p>
            </button>
          ))}
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-4">{template.name}</h3>
          <div className="space-y-3">
            {template.fields.map(f => (
              <div key={f}>
                <label className="block text-xs font-medium text-muted-foreground mb-1 capitalize">{f.replace(/_/g, " ")}</label>
                <input value={data[f] || ""} onChange={e => setData({...data, [f]: e.target.value})} className="w-full bg-background border rounded-lg px-3 py-2 text-sm" />
              </div>
            ))}
          </div>
          <button onClick={generate} className="mt-4 w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium flex items-center justify-center gap-2">
            <Download size={14} /> Generate PDF
          </button>
        </div>
      </div>
    </div>
  );
}
