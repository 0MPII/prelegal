# CLAUDE.md — Prelegal

Instructions for Claude Code when working in this repository. Read this before making changes.

---

## What this project is

**Prelegal** is a FastAPI web app that lets people fill in and download standard legal agreement templates. It's a **self-serve document generator**, not a lawyer, not a review tool, not a contract negotiation product.

The value prop is boring on purpose: pick a template → fill a form → download a `.docx`.

## What this project is *not*

Hard non-goals. Do not drift into these without an explicit ticket:

- ❌ **Not legal advice.** The app does not tell users what to sign, what terms mean legally, or which template fits their situation.
- ❌ **Not a template author.** Templates are sourced from CommonPaper's standard agreement library. We fill them in; we do not rewrite the substantive clauses.
- ❌ **Not a redlining / negotiation tool.** No tracked changes, no comment threads, no counterparty workflow.
- ❌ **Not a signature platform.** The output is a `.docx` — where it goes next (DocuSign, print, email) is out of scope.
- ❌ **Not a SaaS with accounts.** No auth, no user data persistence, no cloud storage. Session-only.

If a feature request smells like it lands in one of these, flag it and ask before building.

---

## Architecture

```
Browser ── GET /                    ── catalog page (list of 11 templates)
        ── GET /template/{fname}    ── read-only rendered Markdown
        ── GET /create/{fname}      ── auto-generated form (schema derived from spans)
        ── POST /create/{fname}/preview  ── HTML preview with filled/blank spans highlighted
        └─ POST /create/{fname}/download ── python-docx generates .docx and streams it back
```

**Backend only.** Jinja2 templates rendered server-side. No React, no SPA, no separate frontend build. If you find yourself reaching for a JS framework, stop and re-read this line.

### Data flow for a fill-in

1. `catalog.json` declares the 11 templates and their metadata.
2. User picks one → `/create/{filename}` loads the Markdown from `templates/`.
3. `app/docgen.py` parses `<span class="..._link">` tags to derive a form schema (party roles + document-specific fields, grouped into sections like *Key terms*, *Order form*, *Statement of work*).
4. Form is rendered from that schema. User fills it.
5. On submit, the same span-parsing logic substitutes values into the Markdown, and `python-docx` builds a `.docx` with a cover-page table (party details) followed by the filled body.
6. File is streamed as `{doc-slug}-{party-a}-{party-b}.docx`.

The span-parsing in `docgen.py` is load-bearing. If you touch it, run the full test suite before assuming anything works.

---

## Directory layout

```
prelegal/
├── CLAUDE.md              ← you are here
├── MANUAL_TESTING.md      ← checklist for things pytest can't catch
├── catalog.json           ← declares the 11 templates
├── app/
│   ├── main.py            ← FastAPI routes
│   ├── docgen.py          ← span parsing, schema derivation, docx generation
│   ├── templates/         ← Jinja2 HTML templates (form, preview, catalog)
│   └── tests/             ← pytest suite (routing, field discovery, docx structure)
└── templates/             ← the 11 legal Markdown templates (CommonPaper)
```

Two `templates/` dirs, watch the path:
- `app/templates/` = Jinja2 HTML for the web UI
- `templates/` (repo root) = the legal agreement Markdown source

---

## Conventions to respect

### Span markers in Markdown templates
Fillable fields and party roles are marked with `<span class="..._link">` tags. The class name encodes what the field is. Examples of the pattern:

- `provider_name_link`, `customer_name_link` → party fields
- `effective_date_link`, `governing_law_link` → document-specific fields

**Do not invent new class-name patterns.** `docgen.py`'s schema inference depends on the existing naming convention. If a new template needs a new field type, follow the existing suffix pattern (`_link`) and add explicit handling in `docgen.py`.

### Party roles
Templates use a small vocabulary: **Provider**, **Customer**, **Partner**, **Company**. Two-party templates map to a `party_a` / `party_b` pair for filename generation. Multi-party templates (rare) need explicit handling — don't assume two.

### Sections
The auto-derived form groups fields into named sections (*Key terms*, *Order form*, *Statement of work*, etc.). Section membership is inferred by `docgen.py` from position in the Markdown. Preserve this — the form UX depends on it.

### Filename pattern
Downloads are named `{doc-slug}-{party-a}-{party-b}.docx`. Slug the doc name; use party names as filled by the user (falling back to `party` / `counterparty` if empty). Preserve casing decisions in `docgen.py` if you touch them — the tests assert on filenames.

---

## Running & testing

```bash
# dev server
uvicorn app.main:app --reload

# tests
pytest app/tests/ -v
```

Assume Python 3.11+. Dependencies live in `requirements.txt` / `pyproject.toml` (whichever the repo uses — check before adding a new one).

### Testing philosophy

Automated tests cover:
- Route status codes and content types
- Field-discovery correctness against known templates
- `.docx` structural properties (cover page present, expected sections, filename shape)

**Manual tests live in `MANUAL_TESTING.md`** and cover what pytest fundamentally can't:
- Visual layout in the browser
- Rendered `.docx` appearance in Word, Pages, and Google Docs
- Dark mode
- Long-value overflow, non-ASCII characters, empty forms

When you change anything that touches rendering, remind the user to run through the relevant `MANUAL_TESTING.md` section. Don't skip this — a passing pytest suite has repeatedly shipped broken visuals.

### Adding a new template

1. Drop the Markdown file in `templates/` using the existing span-marker convention.
2. Add an entry to `catalog.json` (title, filename, description).
3. Add a field-discovery test in `app/tests/` that asserts the expected schema.
4. Manually render, preview, and download it. Add to `MANUAL_TESTING.md` if it has quirks.

---

## Stack constraints

- **FastAPI** for routes. Not Flask, not Django, not Starlette raw.
- **Jinja2** for HTML. Server-rendered. No htmx/Alpine unless the user explicitly asks.
- **python-docx** for `.docx` generation. Not docxtpl, not pandoc, not LibreOffice CLI.
- **pytest** for tests. Not unittest.
- **No database.** Session state only. If you feel the urge to add SQLAlchemy, stop and ask.

If a task seems to require a stack change, surface the tradeoff before implementing it.

---

## LLM features → use the `cerebras-inference` skill

This project may add LLM-powered helper features (e.g., plain-language explanations of clauses on hover, form-field hints, "explain this section" tooltips). When implementing any of those:

**Consult the `cerebras-inference` skill first** for how to call `api.cerebras.ai/v1`, pick a model ID, stream responses, and set up the client. Prefer streaming for anything user-facing — Cerebras' speed is only visible if you actually stream tokens.

Hard rules for any LLM feature in this app — these are stricter than the skill's defaults because this is a legal-adjacent product:

1. **LLM output never modifies template text.** Explanations and hints render in the UI chrome (tooltips, side panels), never inside the Markdown that becomes the `.docx`.
2. **No generated clauses.** The model does not write, rewrite, or "suggest improvements to" legal language. Ever. Even if a user asks.
3. **Explicit disclaimer.** Any LLM-generated text shown to users must be labeled "AI-generated explanation — not legal advice." Bake this into the component, not per-call.
4. **Deterministic where possible.** Field validation, filename slugging, party-role mapping — keep these in Python. Do not offload logic that has a right answer to an LLM.
5. **API key handling.** `CEREBRAS_API_KEY` via environment variable, never checked in. Add to `.env.example` if the user is using dotenv.
6. **Failure = graceful degrade.** If Cerebras is down or rate-limited, the fill-in-and-download flow must still work. LLM features are strictly additive.

Suggested model for anything user-facing on this app: `gpt-oss-120b` (fast, cheap, good enough for explanations). Verify against `https://inference-docs.cerebras.ai/models/overview` before hard-coding.

---

## Git & Jira conventions

- **Jira project prefix: `PREL`.** Tickets so far: PREL-1 (scaffold), PREL-2 (CommonPaper dataset + fill-and-download flow).
- Commits should reference the ticket: `PREL-3: add BAA field validation`.
- Feature branches: `prel-3-baa-validation` style.
- Keep commits scoped — the git history reads as a feature timeline, not a diff dump. If a change touches multiple concerns, split it.
- Before opening a PR, run `pytest` and skim the relevant `MANUAL_TESTING.md` sections.

---

## Common pitfalls

Things that have bitten this project before or predictably will:

- **Span parsing is regex-adjacent and fragile.** Whitespace inside `<span>` tags, nested spans, or class names with unexpected suffixes will silently break field discovery. Add a test whenever you change `docgen.py`.
- **Two `templates/` directories.** Confusing FastAPI's Jinja2 loader with the legal-template folder wastes hours. Check the path.
- **`.docx` looks fine in Word but wrong in Google Docs** (or vice versa). Always test all three. `python-docx` output is standards-compliant but rendering differs.
- **Party name edge cases.** Empty strings, single-word names, non-ASCII characters, and very long names all hit the filename generator. There are tests — don't remove them.
- **CommonPaper templates are versioned upstream.** If you update a template file, note the CommonPaper version in the commit message so we can trace regressions.
- **Preview vs. download drift.** The preview endpoint and the download endpoint share substitution logic through `docgen.py`. If you special-case one, special-case the other, or the download will silently differ from what the user previewed.

---

## When in doubt

Ask before doing any of these:
- Adding a dependency
- Introducing persistence (DB, disk cache, session store)
- Adding an LLM feature that touches template text
- Removing or restructuring the span-marker convention
- Adding auth or accounts
- Adding a frontend build step

Small refactors, test additions, bug fixes on existing behavior, and new templates that follow the existing convention — proceed without asking.