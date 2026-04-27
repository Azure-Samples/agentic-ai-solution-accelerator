import { useEffect, useState } from "react";

export type SectionStatus = "waiting" | "live" | "ready" | "skipped";

export interface NavSection {
  id: string;
  label: string;
  status: SectionStatus;
}

interface Props {
  sections: NavSection[];
}

// Sticky horizontal nav with status chips. Clicking a chip
// scrolls the matching section into view (the section IDs
// must be applied to the actual section elements as ``id={...}``).
//
// Status chips communicate progress at-a-glance during streaming —
// "live" pulses, "ready" is solid, "waiting" is muted, "skipped" is
// warn-toned. We deliberately do NOT use tabs (which would hide
// in-progress sections) or a vertical rail (which doesn't work well
// on mid-width laptop screens).
export function SectionNav({ sections }: Props) {
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const els = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);
    if (els.length === 0) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length > 0) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: [0, 0.25, 0.5, 1] },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [sections]);

  function handleClick(id: string) {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <nav className="section-nav" aria-label="Briefing sections">
      {sections.map((s) => (
        <button
          key={s.id}
          type="button"
          className={[
            "section-chip",
            `chip-${s.status}`,
            active === s.id ? "chip-active" : "",
          ].filter(Boolean).join(" ")}
          onClick={() => handleClick(s.id)}
          aria-current={active === s.id ? "true" : undefined}
        >
          <span className="chip-dot" aria-hidden="true" />
          <span className="chip-label">{s.label}</span>
        </button>
      ))}
    </nav>
  );
}
