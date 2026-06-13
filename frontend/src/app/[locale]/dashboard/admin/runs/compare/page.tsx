"use client";

import { useState } from "react";
import { fetchClient } from "@/lib/api/client";
import { SlidersHorizontal, Gauge } from "lucide-react";

export default function RunComparisonPage() {
  const [runA, setRunA] = useState("");
  const [runB, setRunB] = useState("");
  const [result, setResult] = useState<any>(null);

  const compare = async () => {
    try {
      const d = await fetchClient(`/monitoring/runs/compare?run_a=${runA}&run_b=${runB}`);
      setResult(d);
    } catch (e: any) { setResult({ error: e.message }); }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Run Comparison</h1>
      <p className="text-sm text-muted-foreground mb-8">Side-by-side agent execution analysis</p>

      <div className="rounded-lg border bg-card p-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Run A ID</label>
            <input value={runA} onChange={e => setRunA(e.target.value)} className="w-full bg-background border rounded-lg px-3 py-2 text-sm font-mono" placeholder="agent_execution_run id" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Run B ID</label>
            <input value={runB} onChange={e => setRunB(e.target.value)} className="w-full bg-background border rounded-lg px-3 py-2 text-sm font-mono" placeholder="agent_execution_run id" />
          </div>
        </div>
        <button onClick={compare} disabled={!runA || !runB} className="mt-3 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"><SlidersHorizontal size={14} className="inline mr-1" /> Compare</button>
      </div>

      {result && !result.error && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {["latency_ms", "cost_usd", "token_usage", "steps"].map(k => (
              <div key={k} className="rounded-lg border bg-card p-3 text-center">
                <div className="text-xs text-muted-foreground capitalize mb-1">{k.replace(/_/g, " ")}</div>
                <div className="text-xs"><span className="text-blue-400">{result.run_a[k]}</span> vs <span className="text-green-400">{result.run_b[k]}</span></div>
                <div className={`text-sm font-bold mt-1 ${result.comparison[k + "_diff"] > 0 ? "text-red-400" : result.comparison[k + "_diff"] < 0 ? "text-green-400" : ""}`}>
                  {result.comparison[k + "_diff"] > 0 ? "+" : ""}{result.comparison[k + "_diff"]}
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {["trace_a", "trace_b"].map((key, i) => (
              <div key={key} className="rounded-lg border bg-card p-4">
                <h3 className="font-semibold mb-2">Run {i ? "B" : "A"} Trace</h3>
                <div className="max-h-[400px] overflow-y-auto space-y-2">
                  {(result[key] || []).map((step: any, j: number) => (
                    <div key={j} className="text-xs p-2 rounded bg-muted/50">
                      <span className="font-mono text-muted-foreground">{step.step_name || step.step || `Step ${j+1}`}</span>
                      {step.duration_ms && <span className="ml-2 text-muted-foreground">{step.duration_ms}ms</span>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
