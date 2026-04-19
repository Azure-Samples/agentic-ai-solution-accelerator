# Knowledge Concierge — tertiary reference scenario (thin runnable)

> **Customer:** Contoso Internal (fictitious)
> **Bundle:** `retrieval-prod`
> **Focus:** ACL-respecting grounding across SharePoint + internal wiki.

## Business problem
Employees ask natural-language questions about internal policy / HR / IT / procurement. Agent answers with citations, respecting each user's SharePoint/wiki ACLs.

## Why smaller but real
The hard part here isn't orchestration — it's:
1. ACL-inheriting retrieval that never leaks a doc the asker can't read.
2. Grounding quality at citation level.
3. Declining to answer when no grounded answer exists.

## Agent topology (1 agent)
- `concierge` — receives question; calls ACL-aware retriever; answers with citations or declines.

## Grounding
- SharePoint: `/sites/*` — ACL inherit (user-token-based).
- Wiki: `internal-wiki-v2` — ACL inherit.

## Tools
Retrieval-only (user-context-aware).

## What to study
- ACL-inheriting retrieval pattern (see `patterns/architecture/acl-inheriting-retrieval.md` — Phase C).
- Groundedness thresholds + decline behavior.
- "No answer is a valid answer" eval probes.

## Phase A placeholder
Thin runnable impl ships in Phase D.
