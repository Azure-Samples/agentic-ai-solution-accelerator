import { useState } from "react";
import type { ResearchRequest } from "../types/research";

const DEFAULTS: ResearchRequest = {
  company_name: "Contoso Hardware",
  domain: "contoso.com",
  seller_intent:
    "Open a conversation about replacing their legacy on-prem ERP with a cloud-native option.",
  persona: "VP of Operations",
  icp_definition:
    "Mid-market manufacturer, 200–2000 employees, multi-site, currently on legacy ERP, "
    + "active digital transformation budget.",
  our_solution:
    "Cloud ERP suite with prebuilt manufacturing modules, embedded analytics, and "
    + "phased migration accelerators.",
  context_hints: ["recent funding round", "expansion into APAC"],
};

interface Props {
  busy: boolean;
  onSubmit: (req: ResearchRequest) => void;
  onCancel: () => void;
}

export function ResearchForm({ busy, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<ResearchRequest>(DEFAULTS);
  const [hintsRaw, setHintsRaw] = useState<string>(DEFAULTS.context_hints.join(", "));

  function update<K extends keyof ResearchRequest>(key: K, value: ResearchRequest[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const hints = hintsRaw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    onSubmit({ ...form, context_hints: hints });
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Research request</h2>
      <p className="muted">
        Fields mirror <code>ResearchRequest</code> in
        <code> src/scenarios/sales_research/schema.py</code>.
      </p>

      <div className="grid">
        <label>
          <span>Company name *</span>
          <input
            type="text"
            required
            value={form.company_name}
            onChange={(e) => update("company_name", e.target.value)}
          />
        </label>
        <label>
          <span>Domain</span>
          <input
            type="text"
            value={form.domain}
            placeholder="contoso.com"
            onChange={(e) => update("domain", e.target.value)}
          />
        </label>
        <label>
          <span>Persona</span>
          <input
            type="text"
            value={form.persona}
            onChange={(e) => update("persona", e.target.value)}
          />
        </label>
        <label className="full">
          <span>Seller intent *</span>
          <textarea
            required
            rows={2}
            value={form.seller_intent}
            onChange={(e) => update("seller_intent", e.target.value)}
          />
        </label>
        <label className="full">
          <span>ICP definition *</span>
          <textarea
            required
            rows={3}
            value={form.icp_definition}
            onChange={(e) => update("icp_definition", e.target.value)}
          />
        </label>
        <label className="full">
          <span>Our solution *</span>
          <textarea
            required
            rows={3}
            value={form.our_solution}
            onChange={(e) => update("our_solution", e.target.value)}
          />
        </label>
        <label className="full">
          <span>Context hints (comma-separated)</span>
          <input
            type="text"
            value={hintsRaw}
            onChange={(e) => setHintsRaw(e.target.value)}
            placeholder="recent funding, M&A activity, ..."
          />
        </label>
      </div>

      <div className="actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Running…" : "Run research"}
        </button>
        {busy && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
