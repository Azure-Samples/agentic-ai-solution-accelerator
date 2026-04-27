import { useEffect, useState } from "react";
import { JOKE_ROTATE_MS, PARTNER_JOKES } from "../data/jokes";

interface Props {
  // Short label for the section that's loading, e.g. "Account profile".
  label: string;
  // Optional sub-label describing which worker is producing this section.
  subLabel?: string;
}

// Pick a starting index so different sections don't all show the same
// joke at the same moment. The hash is deterministic per label so a
// section keeps a stable starting joke (no jarring jumps on rerender).
function startIndex(label: string): number {
  let h = 0;
  for (let i = 0; i < label.length; i++) {
    h = (h * 31 + label.charCodeAt(i)) | 0;
  }
  return Math.abs(h) % PARTNER_JOKES.length;
}

/**
 * Placeholder card shown for a briefing section whose source worker
 * hasn't completed yet. Rotates a partner-audience joke every
 * ``JOKE_ROTATE_MS`` so the user has something to read during the
 * 30-60s gpt-5-mini call. The joke list is in ``data/jokes.ts``.
 */
export function SectionLoader({ label, subLabel }: Props) {
  const [idx, setIdx] = useState(() => startIndex(label));
  useEffect(() => {
    const t = window.setInterval(() => {
      setIdx((prev) => (prev + 1) % PARTNER_JOKES.length);
    }, JOKE_ROTATE_MS);
    return () => window.clearInterval(t);
  }, []);

  return (
    <div className="section-loader" role="status" aria-live="polite">
      <div className="section-loader-head">
        <span className="pulse" aria-hidden="true" />
        <span className="section-loader-label">
          {label} <span className="muted">— pending{subLabel ? ` · ${subLabel}` : ""}</span>
        </span>
      </div>
      <div className="joke-line" aria-label="loading joke">
        <span className="joke-prefix">While you wait …</span>{" "}
        <span className="joke-text" key={idx}>{PARTNER_JOKES[idx]}</span>
      </div>
    </div>
  );
}
