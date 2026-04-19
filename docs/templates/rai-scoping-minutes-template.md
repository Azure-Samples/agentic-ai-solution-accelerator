# RAI Scoping Minutes Template

> Copy to `rai/scoping-minutes.md` in the engagement repo.
> Feeds the formal RAI Impact Assessment (IA). Required for Path B/C.

## Meeting metadata
- **Date:** YYYY-MM-DD
- **Duration:** <hh:mm>
- **Facilitator:** <MSFT field / partner delivery lead>
- **Attendees (role / org / GitHub ID):**
  - Customer sponsor — <name / org>
  - Customer security reviewer — <name / org>
  - Customer data owner — <name / org>
  - Customer CISO delegate — <name / org>
  - Partner delivery lead — <name / org>
  - Partner RAI owner — <name / org>
  - MSFT field CTO rep — <name / org>

## 1. Use case scope
- **Business problem:** <one-paragraph>
- **End-user population:** <who interacts with the system>
- **Expected usage volume:** <estimate>
- **Geographic scope:** <countries / regions>
- **Languages supported:** <list>

## 2. Agent topology (Spec-aligned)
- **Agent count:** <1 or 2>
- **Agents:**
  - `<agent-1>` — role / responsibilities
  - `<agent-2>` — role / responsibilities (if 2)
- **Edges:** <list>
- **HITL points:** <list>
- **a2a cap:** 2

## 3. Model + tool + grounding
- **Model(s):** <id + alias>
- **Tools (list each):**
  - Name / kind / `side_effect: true|false` / blast-radius summary
- **Grounding sources:**
  - Source ID / type / URL pattern / ACL model / classification / snapshot ref

## 4. Data classification + flow
- **Input data classification:** <public / internal / confidential / restricted>
- **Sign-off:** customer-CISO-delegate (signed via PR review)
- **Data residency constraint:** <region requirement>
- **PII / sensitive categories present:** <yes/no + categories>
- **Data flow diagram ref:** <link>

## 5. RAI risk categories assessed
For each category: risk level (low/medium/high) + mitigation + owner.
- **Prompt injection / XPIA** — <level> / mitigation: T1 content sanitization + baseline-hitl on side-effect / owner: <>
- **Hallucination / grounding failure** — <level> / groundedness threshold, eval suite / <>
- **Data leakage via grounding ACL mismatch** — <level> / ACL model + reconcile / <>
- **Over-action via side-effect tools** — <level> / HITL + kill switch / <>
- **Cost excursion** — <level> / cost ceiling + alerts / <>
- **Availability / DOS** — <level> / circuit breaker / <>
- **Bias / fairness** — <level> / eval suite + red-team / <>
- **Harmful content generation** — <level> / content filter lock + red-team / <>

## 6. Red-team evaluation plan
- **Eval set initial size:** <N prompts>
- **Coverage:** prompt injection / jailbreak / tool abuse / data exfiltration / bias probes
- **Owner:** <name>
- **Cadence:** per-release + on significant Spec change

## 7. HITL design
- **Which actions require HITL:** <list>
- **Who approves:** <role>
- **SLA for approval:** <time>
- **Fallback on SLA miss:** <behavior>

## 8. Operating model + ownership
- **Pager ownership:** <partner / customer / joint>
- **Waiver approval authority:** CODEOWNERS / partner delivery lead / governance board (per severity)
- **RAI IA owner for renewals:** <name>

## 9. RAI IA commitments
- [ ] Formal IA document drafted and submitted.
- [ ] Immutable UUID assigned.
- [ ] CODEOWNERS set on IA doc path.
- [ ] 180-day expiry noted.
- [ ] Summary added to Spec under `rai.impact_assessment_ref`.

## 10. Action items
- [ ] <owner> — <action> — <due>
- [ ] <owner> — <action> — <due>
