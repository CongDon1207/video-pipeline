# 🚀 CODE RULES — Solo Vibe, Fix Nhan

> **Hard requirement:**  outputs (comments,explanations) **must be in Vietnamese**. The rules below are written in English for precise parsing.

---

## 📏 Core Principles

* **Code only what was asked.** Follow PRD/ticket strictly. No extra features.
* **Minimum viable change.** Choose **one** simplest approach that works; do **not** implement multiple solutions.
* **Short code only.** Keep code concise and readable; avoid over-engineering and deep nesting.
* **Reuse before rewrite.** Always reuse existing modules or utilities before writing new ones; avoid duplicate code at all costs.
* **One-off scripts stay out of main.** Put them in `scripts/` with run instructions.
* **File length limit:** 200–300 LOC. If exceeded → refactor/split.
* **Naming & logging:** clear names; logs short with context.
* **Config & secrets:** from **env** only. Never hardcode. Keep secrets out of VCS.

---

## 🎯 Philosophy (Non‑negotiables)

No unnecessary files/modules.

No architecture/pattern changes unless strictly required and justified.

Prefer readability & maintainability over clever tricks.

---

## 🔧 Environment & Server

* After every **major change** → **restart a fresh server**.
* Before starting new → **kill all related old processes**.
* **Do not overwrite `.env`** accidentally. Keep `.env.sample` for reference. If replacing `.env`, **delete the old one** (no duplicates).


## 🧩 Structure & Pattern

* **Reuse-first.** Avoid new modules unless necessary.
* If replacing tech/pattern while fixing a bug → **remove the old version completely** after migration; no parallel duplicates.
* **Repo layout** (adapt to current standard):
  * `scripts/` — one-off utilities
  * `docs/` — documentation
  * `fixes/` — bug notes

---

## 🛡️ Change Guardrails

* Modify **only** code directly related to the task.
* Implement **exactly** what’s requested; nothing more.
* Make the **minimal** change that passes requirements and tests.

---

## 📑 Before You Start

1. Read PRD → confirm scope & success criteria.
2. Read project docs → flows, constraints, data contracts.
3. Check README.md → patterns, stack, run steps.

---

## 🔍 Issue Handling

* **Simple bug:** apply minimal fix → restart server → test end-to-end.
* **Complex bug (requires iterations):** after fix, write a note in `fixes/`.

**Note template:**

```
fixes/YYYY-MM-DD-<short-slug>.md
1) Context
2) Symptoms
3) Root cause
4) Fix
5) Impact
6) Next steps
```

---

## 📁 Creating New Files — only if truly needed

Create a new file/module only if:

1. No suitable place exists to reuse.
2. Adding to the current file would push it >300 LOC **or** make it unreadable.
3. It’s a general utility reused multiple times (put in `scripts/` or `utils/`).

If creating **to replace** an old file:

* **Delete the old file** immediately after successful replacement.
* **Update all imports/runners** accordingly.

---
## 🌐 MCP

1. **Web Search:** Use when you need fresh/updated information (news, prices, releases, API changes) or authoritative sources for citation. Do not use for stable knowledge.

2. **DeepWiki (mcp-remote):** Use for a quick overview of open topics (wikis, long articles, summaries). Do not use for real-time figures.

3. **Context7 (mcp):** Use to query official docs (API, SDK, specific errors). Do not use for news or broad overviews.

**General principles:**
- Choose one suitable tool per task.
- Only fallback to another tool if the primary one is insufficient.
__
## ⏰ Solo Work Loop (10–20 minutes)

1. **Re-read requirement** (quote 1–2 lines from PRD).
2. **Ultra-short plan** (2–3 steps max).
3. **Minimal fix only** (or new file if rules above say so).
4. **Kill & restart server** → test end-to-end (health/log/IO).
5. **Clean up** (remove tmp/experiment code). Document in `fixes/` if complex.

---

## ✅ Definition of Done (DoD)

* [ ] Matches requirement **exactly**; **no extra** scope.
* [ ] Old processes killed; fresh server started; tests pass.
* [ ] Unrelated code untouched.
* [ ] No unnecessary files; replaced files **deleted**.
* [ ] `.env` safe; secrets not in VCS.
* [ ] Files >300 LOC reviewed/refactored.
* [ ] Complex bug has a `fixes/` note.

---

### 🔥 Emphasis for Agents

* **WRITE CODE ONLY TO THE SPEC.**
* **MINIMUM, NOT MAXIMUM.**
* **ONE simple solution.**
* **KEEP IT SHORT & CLEAR.**

> **Reminder:** Despite English rules, **all outputs must be in Vietnamese**.
