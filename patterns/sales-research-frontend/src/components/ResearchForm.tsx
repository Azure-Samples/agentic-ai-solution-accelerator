import { useState } from "react";
import type { ResearchRequest } from "../types/research";

const DEFAULTS: ResearchRequest = {
  company_name: "Contoso Hardware",
  domain: "contoso.com",
  seller_intent:
    "Open a conversation about replacing their legacy on-prem ERP with a cloud-native option.",
  persona: "VP of Operations",
  icp_definition:
    "Mid-market manufacturer, 200-2000 employees, multi-site, currently on legacy ERP, "
    + "active digital transformation budget.",
  our_solution:
    "Cloud ERP suite with prebuilt manufacturing modules, embedded analytics, and "
    + "phased migration accelerators.",
  context_hints: ["recent funding round", "expansion into APAC"],
};

interface SectorArchetype {
  id: string;
  label: string;
  hint: string;
  preset: ResearchRequest;
}

// Sector archetypes (not real companies) keep the examples reusable
// for partners adapting the starter to their own customer engagements.
// Each archetype exercises a different shape of the briefing — useful
// for demo'ing edge cases (e.g., commercial cloud vs regulated, etc.).
const ARCHETYPES: SectorArchetype[] = [
  {
    id: "manufacturer",
    label: "Mid-market manufacturer",
    hint: "ERP modernization, multi-site",
    preset: DEFAULTS,
  },
  {
    id: "saas",
    label: "SaaS scale-up",
    hint: "Series B, expanding GTM",
    preset: {
      company_name: "Northwind SaaS",
      domain: "northwind.example",
      seller_intent:
        "Help them consolidate cloud spend and add observability across their AKS estate.",
      persona: "VP Engineering",
      icp_definition:
        "Series B-D B2B SaaS, 100-500 employees, multi-region AKS or EKS, "
        + "spending USD 50k-200k/month on cloud, looking to mature platform engineering.",
      our_solution:
        "Azure Kubernetes Service with managed Prometheus/Grafana, "
        + "FinOps tooling, and a partner-led platform engineering accelerator.",
      context_hints: ["recent fundraising", "platform team hiring"],
    },
  },
  {
    id: "fsi",
    label: "Regional bank / FSI",
    hint: "Compliance-first modernization",
    preset: {
      company_name: "Fabrikam Regional Bank",
      domain: "fabrikambank.example",
      seller_intent:
        "Position our regulated-cloud landing zone for their core banking modernization program.",
      persona: "Chief Information Security Officer",
      icp_definition:
        "Regional bank or credit union, USD 5-50B AUM, FFIEC/PCI scope, "
        + "currently on mainframe or legacy core, board-level digital mandate.",
      our_solution:
        "Sovereign-cloud landing zone on Azure with confidential compute, "
        + "Defender for Cloud baseline, and a regulated-industry partner pod.",
      context_hints: ["new CISO", "regulator examination cycle"],
    },
  },
  {
    id: "retail",
    label: "Omnichannel retailer",
    hint: "Inventory + AI personalization",
    preset: {
      company_name: "Wide World Retail",
      domain: "wideworldretail.example",
      seller_intent:
        "Open a conversation about an AI-powered inventory + personalization stack for peak season.",
      persona: "Chief Digital Officer",
      icp_definition:
        "Omnichannel retailer, USD 500M-5B revenue, 50-500 stores, "
        + "underperforming digital channel, exploring AI for forecasting and personalization.",
      our_solution:
        "Azure OpenAI + Fabric for unified merchandising data; "
        + "partner-led implementation and a peak-season readiness review.",
      context_hints: ["holiday peak prep", "loyalty program relaunch"],
    },
  },
];

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

  function loadArchetype(id: string) {
    const a = ARCHETYPES.find((x) => x.id === id);
    if (!a) return;
    setForm(a.preset);
    setHintsRaw(a.preset.context_hints.join(", "));
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
    <form className="research-form" onSubmit={handleSubmit} aria-label="Research request">
      <header className="form-header">
        <h2>Research request</h2>
        <p className="muted">
          Configure once per customer. The form persists across runs — refine and re-submit
          to iterate.
        </p>
      </header>

      <div className="archetype-picker" role="group" aria-label="Load example">
        <span className="archetype-label">Load example:</span>
        {ARCHETYPES.map((a) => (
          <button
            key={a.id}
            type="button"
            className="archetype-btn"
            onClick={() => loadArchetype(a.id)}
            disabled={busy}
            title={a.hint}
          >
            {a.label}
          </button>
        ))}
      </div>

      <fieldset className="form-fieldset" disabled={busy}>
        <legend>Account</legend>
        <label>
          <span>Company name *</span>
          <input
            type="text"
            required
            value={form.company_name}
            onChange={(e) => update("company_name", e.target.value)}
          />
          <small className="field-help">Used as the primary entity for retrieval and prompts.</small>
        </label>
        <label>
          <span>Domain</span>
          <input
            type="text"
            value={form.domain}
            placeholder="contoso.com"
            onChange={(e) => update("domain", e.target.value)}
          />
          <small className="field-help">Optional. Improves citation grounding.</small>
        </label>
      </fieldset>

      <fieldset className="form-fieldset" disabled={busy}>
        <legend>Engagement</legend>
        <label>
          <span>Persona</span>
          <input
            type="text"
            value={form.persona}
            onChange={(e) => update("persona", e.target.value)}
            placeholder="VP of Operations"
          />
          <small className="field-help">Decision-maker the outreach will be tailored to.</small>
        </label>
        <label>
          <span>Seller intent *</span>
          <textarea
            required
            rows={2}
            value={form.seller_intent}
            onChange={(e) => update("seller_intent", e.target.value)}
            maxLength={500}
          />
          <small className="field-help">
            One sentence. {form.seller_intent.length}/500
          </small>
        </label>
      </fieldset>

      <fieldset className="form-fieldset" disabled={busy}>
        <legend>Targeting</legend>
        <label>
          <span>ICP definition *</span>
          <textarea
            required
            rows={3}
            value={form.icp_definition}
            onChange={(e) => update("icp_definition", e.target.value)}
            maxLength={1000}
          />
          <small className="field-help">
            Industry, segment, size, technology, signals. {form.icp_definition.length}/1000
          </small>
        </label>
        <label>
          <span>Our solution *</span>
          <textarea
            required
            rows={3}
            value={form.our_solution}
            onChange={(e) => update("our_solution", e.target.value)}
            maxLength={1000}
          />
          <small className="field-help">
            Capabilities, partner motion, accelerators. {form.our_solution.length}/1000
          </small>
        </label>
        <label>
          <span>Context hints</span>
          <input
            type="text"
            value={hintsRaw}
            onChange={(e) => setHintsRaw(e.target.value)}
            placeholder="recent funding, M&A activity, ..."
          />
          <small className="field-help">Comma-separated. Steer the planner toward fresh signals.</small>
        </label>
      </fieldset>

      <div className="form-actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Researching..." : "Run research"}
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
