"""One-shot builder for the four partner-walkthrough Excalidraw source diagrams.

Run once: writes JSON into docs/assets/diagrams/. Re-runnable; overwrites.
The JSON files are hand-edited from then on (or in https://aka.ms/excalidraw).
Kept in scripts/ for traceability of how the originals were generated.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = ("#1864ab", "#a5d8ff")
TEAL = ("#0c8599", "#99e9f2")
ORANGE = ("#e67700", "#fff3bf")
GREEN = ("#2f9e44", "#b2f2bb")
PURPLE = ("#862e9c", "#f3d9fa")
GRAY = ("#495057", "#dee2e6")


_uid = 0


def uid(prefix: str) -> str:
    global _uid
    _uid += 1
    return f"{prefix}_{_uid}"


def labeled_box(x, y, w, h, text, colors, *, font_size=16, dashed=False, transparent=False):
    """Returns [rectangle, text] pair with bound-text wiring."""
    box_id = uid("box")
    txt_id = uid("txt")
    stroke, fill = colors
    rect = {
        "type": "rectangle",
        "id": box_id,
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke,
        "backgroundColor": "transparent" if transparent else fill,
        "fillStyle": "solid" if transparent else "hachure",
        "strokeWidth": 2,
        "strokeStyle": "dashed" if dashed else "solid",
        "roundness": {"type": 3},
        "boundElements": [{"type": "text", "id": txt_id}],
    }
    txt = {
        "type": "text",
        "id": txt_id,
        "x": x, "y": y, "width": w, "height": h,
        "text": text,
        "fontSize": font_size,
        "fontFamily": 1,
        "strokeColor": "#000000",
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": box_id,
    }
    return rect, txt, box_id


def free_text(x, y, w, text, font_size=14, *, lines=None):
    n = lines if lines is not None else (text.count("\n") + 1)
    h = int(font_size * 2.5 * n)
    return {
        "type": "text",
        "id": uid("ftxt"),
        "x": x, "y": y, "width": w, "height": h,
        "text": text,
        "fontSize": font_size,
        "fontFamily": 1,
        "strokeColor": "#000000",
        "textAlign": "left",
        "verticalAlign": "top",
    }


def arrow(src, dst, *, dx=0, dy=0):
    """Arrow between two box ids using horizontal layout with bindings."""
    return {
        "type": "arrow",
        "id": uid("arr"),
        "x": 0, "y": 0,
        "width": 1, "height": 1,
        "strokeColor": "#495057",
        "strokeWidth": 2,
        "points": [[0, 0], [1, 0]],
        "startBinding": {"elementId": src, "focus": 0, "gap": 4},
        "endBinding": {"elementId": dst, "focus": 0, "gap": 4},
    }


def free_arrow(x, y, points, color="#495057", width=2):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {
        "type": "arrow",
        "id": uid("arr"),
        "x": x, "y": y,
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
        "strokeColor": color,
        "strokeWidth": width,
        "points": points,
    }


def write(name: str, elements: list) -> None:
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "agentic-ai-solution-accelerator",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
    }
    (OUT / name).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {name} ({len(elements)} elements)")


# ---------------------------------------------------------------------------
# Diagram 1 — 10-step partner walkthrough flow
# ---------------------------------------------------------------------------
def build_flow():
    els = []
    title = free_text(40, 20, 1500,
                      "Partner walkthrough — 10 steps from clone to operate",
                      font_size=24, lines=1)
    title["height"] = 50
    els.append(title)

    ready = ["1. Get oriented", "2. Set up your machine", "3. Rehearse in a sandbox"]
    deliver = ["1. Clone for the customer", "2. Discover with the customer",
               "3. Scaffold from the brief", "4. Provision the customer's Azure",
               "5. Iterate & evaluate", "6. UAT & handover", "7. Operate (Day 2)"]

    bw, bh, gap = 180, 80, 20
    track_x = 30

    # Get ready row
    track_label, track_txt, _ = labeled_box(track_x, 110, 160, bh,
                                            "Get ready\n(once)", BLUE, transparent=True)
    els.extend([track_label, track_txt])
    prev_id = None
    x = track_x + 160 + gap + 20
    ready_ids = []
    for label in ready:
        rect, txt, bid = labeled_box(x, 110, bw, bh, label, BLUE, font_size=14)
        els.extend([rect, txt])
        ready_ids.append(bid)
        if prev_id:
            els.append(arrow(prev_id, bid))
        prev_id = bid
        x += bw + gap

    # Deliver row
    track2, track2_txt, _ = labeled_box(track_x, 240, 160, bh,
                                        "Deliver\n(per customer)", TEAL, transparent=True)
    els.extend([track2, track2_txt])
    prev_id = None
    x = track_x + 160 + gap + 20
    deliver_ids = []
    for label in deliver:
        rect, txt, bid = labeled_box(x, 240, bw, bh, label, TEAL, font_size=12)
        els.extend([rect, txt])
        deliver_ids.append(bid)
        if prev_id:
            els.append(arrow(prev_id, bid))
        prev_id = bid
        x += bw + gap

    # Bridge: Rehearse → Clone (drops down)
    els.append(arrow(ready_ids[-1], deliver_ids[0]))

    # Loop-back annotation: Operate → Discover (per next engagement)
    last_x = 30 + 180 + 20 + (bw + gap) * 7
    loop = free_text(last_x - 600, 350, 600,
                     "↺ Next engagement: loop back to step 2 (Discover) — "
                     "Get-ready stays done.",
                     font_size=13, lines=1)
    loop["height"] = 30
    els.append(loop)

    write("10-step-flow.excalidraw", els)


# ---------------------------------------------------------------------------
# Diagram 2 — Supervisor + workers shape
# ---------------------------------------------------------------------------
def build_supervisor():
    els = []
    els.append({**free_text(40, 20, 1100,
                            "Supervisor + specialist workers — the flagship shape",
                            font_size=22, lines=1), "height": 40})

    user_box = labeled_box(60, 100, 220, 80,
                           "Customer request\n(API / chat)", GRAY)
    els.extend([user_box[0], user_box[1]])

    sup_box = labeled_box(440, 100, 280, 80,
                          "Supervisor agent\n(routes intent → worker(s))", PURPLE)
    els.extend([sup_box[0], sup_box[1]])

    hitl_box = labeled_box(900, 100, 220, 80,
                           "HITL gate\n(approves side effects)", ORANGE)
    els.extend([hitl_box[0], hitl_box[1]])

    workers = [
        ("Researcher\n(retrieval-only)", 60),
        ("Drafter\n(LLM-only)", 340),
        ("Tool-using worker\n(side effects)", 620),
        ("Custom worker N\n(specialist)", 900),
    ]
    worker_ids = []
    for label, x in workers:
        b = labeled_box(x, 280, 220, 90, label, GREEN, font_size=13)
        els.extend([b[0], b[1]])
        worker_ids.append(b[2])

    obs_box = labeled_box(60, 430, 1060, 70,
                          "Telemetry · App Insights traces · KPI events · evals (quality + redteam)",
                          BLUE, font_size=14)
    els.extend([obs_box[0], obs_box[1]])

    els.append(arrow(user_box[2], sup_box[2]))
    for wid in worker_ids:
        els.append(arrow(sup_box[2], wid))
    els.append(arrow(worker_ids[2], hitl_box[2]))

    note = free_text(740, 200, 380,
                     "Side-effect tools always pass through HITL\n"
                     "(see hitl.checkpoint in src/accelerator_baseline/).",
                     font_size=12, lines=2)
    els.append(note)

    write("supervisor-workers.excalidraw", els)


# ---------------------------------------------------------------------------
# Diagram 3 — Solution brief → generated artifacts
# ---------------------------------------------------------------------------
def build_brief():
    els = []
    els.append({**free_text(40, 20, 1100,
                            "solution-brief.md is the source of truth — "
                            "scaffolding fans out from it",
                            font_size=22, lines=1), "height": 40})

    center = labeled_box(440, 260, 280, 110,
                         "docs/discovery/\nsolution-brief.md", PURPLE, font_size=16)
    els.extend([center[0], center[1]])

    spokes = [
        ("Prompts &\nworker agents",        60,   80, GREEN),
        ("Retrieval &\ntools",              440,  60, GREEN),
        ("Infra (Bicep)\n+ landing zone",   820,  80, BLUE),
        ("accelerator.yaml\n(KPIs · HITL · gates)", 60, 280, ORANGE),
        ("Eval cases\n(quality + redteam)", 820,  280, TEAL),
        ("Telemetry events\n+ dashboard panels", 60, 460, BLUE),
        ("Acceptance gate\n(CI must pass)",  820, 460, ORANGE),
    ]
    spoke_ids = []
    for label, x, y, colors in spokes:
        b = labeled_box(x, y, 240, 90, label, colors, font_size=13)
        els.extend([b[0], b[1]])
        spoke_ids.append(b[2])

    for sid in spoke_ids:
        els.append(arrow(center[2], sid))

    note = free_text(40, 600, 1100,
                     "Run /scaffold-from-brief once the brief has zero TBD. "
                     "Re-run any time the brief changes.",
                     font_size=13, lines=1)
    note["height"] = 30
    els.append(note)

    write("brief-to-artifacts.excalidraw", els)


# ---------------------------------------------------------------------------
# Diagram 4 — OIDC topology for customer Azure provisioning
# ---------------------------------------------------------------------------
def build_oidc():
    els = []
    els.append({**free_text(40, 20, 1200,
                            "OIDC trust path — GitHub Actions ➜ customer Azure (no secrets)",
                            font_size=22, lines=1), "height": 40})

    # Left side: GitHub
    gh_outer = labeled_box(40, 100, 480, 380,
                           "GitHub repo · <customer-short-name>-agents",
                           BLUE, font_size=14, transparent=True)
    els.extend([gh_outer[0], gh_outer[1]])

    env = labeled_box(80, 170, 400, 80,
                      "GitHub Environment\n(per customer · gates approvals)", BLUE)
    els.extend([env[0], env[1]])

    fed = labeled_box(80, 280, 400, 80,
                      "Federated credential\n(subject = environment + branch)", ORANGE)
    els.extend([fed[0], fed[1]])

    job = labeled_box(80, 390, 400, 70,
                      "deploy.yml job · azd up", GREEN)
    els.extend([job[0], job[1]])

    # Right side: Azure / Customer tenant
    az_outer = labeled_box(620, 100, 540, 460,
                           "Customer Azure tenant",
                           TEAL, font_size=14, transparent=True)
    els.extend([az_outer[0], az_outer[1]])

    entra = labeled_box(660, 170, 460, 80,
                        "Entra app registration\n(trusts the GitHub federated subject)", PURPLE)
    els.extend([entra[0], entra[1]])

    sp = labeled_box(660, 280, 460, 80,
                     "Service principal · scoped RBAC\n(Contributor on resource group)", PURPLE)
    els.extend([sp[0], sp[1]])

    rg = labeled_box(660, 390, 460, 80,
                     "Resource group · Foundry · App Insights · Key Vault", TEAL)
    els.extend([rg[0], rg[1]])

    handover = labeled_box(660, 480, 460, 60,
                           "Handover: federated cred re-pointed to customer's repo at UAT",
                           ORANGE, font_size=13)
    els.extend([handover[0], handover[1]])

    els.append(arrow(env[2], fed[2]))
    els.append(arrow(fed[2], job[2]))
    els.append(arrow(fed[2], entra[2]))
    els.append(arrow(entra[2], sp[2]))
    els.append(arrow(sp[2], rg[2]))
    els.append(arrow(job[2], rg[2]))

    note = free_text(40, 580, 1100,
                     "Provisioned by /deploy-to-env. Never hand-edit deploy.yml — "
                     "deploy/environments.yaml is the contract.",
                     font_size=13, lines=1)
    note["height"] = 30
    els.append(note)

    write("oidc-topology.excalidraw", els)


if __name__ == "__main__":
    build_flow()
    build_supervisor()
    build_brief()
    build_oidc()
    print(f"\nAll diagrams written to {OUT.relative_to(ROOT)}/")
