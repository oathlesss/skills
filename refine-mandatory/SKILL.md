---
name: refine-mandatory
description: Structural guardrail ensuring every response follows REFINE → EXECUTE. Load this at the start of every Ruben session.
category: hermes
---

# REFINE → EXECUTE (mandatory)

Before ANY response — before tool calls, before substantive answers — output a REFINE block covering:

1. **Restated goal** — precise intent, scope, what "done" means
2. **Ordered steps** — concrete sequence (single step for simple requests)
3. **Assumptions** — environment, platform, constraints. Flag the ones that would change your approach if wrong
4. **Pulled context** — relevant facts from memory and any skills that might apply (load them now)

Then execute. Do not describe what you're doing — just do it.

**Skip REFINE only for pure social banter** that genuinely requires no reasoning. If there's any doubt, REFINE.

This must happen on EVERY response. Not ~60%. Not "when it seems complex." Every. Single. One.
