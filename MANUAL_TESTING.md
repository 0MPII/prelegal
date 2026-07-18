# Manual test checklist

The pytest suite (`app/tests/`) covers routing, field discovery, span-substitution
logic, and docx structure. It cannot verify how the app actually looks or feels,
or whether a generated `.docx` opens cleanly in a real word processor. Run through
this checklist by hand before shipping a change that touches `app/docgen.py`,
`app/main.py`, or anything in `app/templates_html/`.

Start the app first: `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`

## 1. Catalog page (`/`)

- [ ] All 11 documents from `catalog.json` are listed, each with name + description.
- [ ] Every card has a working "Fill in and create this document" link.
- [ ] Clicking a card title (not the create link) opens the read-only template view.
- [ ] Card grid reflows sensibly at narrow widths (resize browser to ~375px).
- [ ] Nav bar stays pinned and legible while scrolling past a tall page.

## 2. Read-only template view (`/template/{filename}`)

- [ ] Spot-check 2–3 documents: text renders as proper prose (no stray `<span>`
      tags, no unrendered markdown syntax like `**bold**` or `[text](url)`).
- [ ] "Fill in and create this document" button at the top works.
- [ ] "All templates" back link returns to `/`.

## 3. Create form (`/create/{filename}`) — do this for at least these three,
      since they exercise different shapes of the field-discovery logic:
      **Mutual NDA** (no inline role references, fallback parties),
      **CSA** (two roles + two field groups: Key terms / Order form),
      **PSA** (heaviest field count, three groups including Statement of work)

- [ ] Party sections are labeled with the correct role names (e.g. "Customer" /
      "Provider", not "Party 1" / "Party 2", except for the NDA which has no
      inline roles and should show the generic fallback).
- [ ] Only the party *name* field is required; address/signatory/email are optional
      (submitting with just names filled in should not block submission).
- [ ] Field labels read naturally — no raw slugs, no double-escaped HTML entities.
- [ ] Long-field documents (PSA, CSA, Software License) are still usable — sections
      are visually distinct, nothing overlaps or overflows at 1280px and 375px widths.
- [ ] Tab order moves through fields top-to-bottom, left-to-right within a section.

## 4. Preview (`POST /create/{filename}/preview`)

- [ ] Filled-in blanks (Effective Date, Governing Law, Purpose, etc.) are visibly
      highlighted and show the value you typed.
- [ ] Fields left blank show as an italicized `[Field Name]` placeholder, not empty
      space or a crash.
- [ ] Role terms (Customer/Provider/Partner/Company) appear as plain defined terms
      in the body text — confirm the actual company name you typed does **not**
      appear inline in the body (it should only be in the cover page/table).
- [ ] "Edit details" link returns to the form with your previous input still filled in.
- [ ] Sticky action bar with the Download button stays visible while scrolling
      through a long document.

## 5. Download (`POST /create/{filename}/download`)

- [ ] File downloads with a sensible name: `{document-slug}-{party-a}-{party-b}.docx`.
- [ ] **Open the actual `.docx` file** in Word, Pages, or Google Docs (not just
      python-docx inspection) — confirm:
  - [ ] Title and "Cover Page" heading render correctly.
  - [ ] Cover page table shows all party details and filled term values.
  - [ ] Body text has correct bold formatting on defined terms (e.g. **Introduction**).
  - [ ] No leftover markdown syntax (`[text](url)`, `**text**`) anywhere.
  - [ ] No duplicate section headings.
  - [ ] Document is one continuous flow — no broken page breaks or orphaned tables.
- [ ] Try this at least once for a document with zero party info filled in — the
      docx should still open cleanly with `[Placeholder]` text throughout, not error.

## 6. Cross-cutting

- [ ] Toggle OS/browser dark mode — check catalog, template view, form, and preview
      pages all remain legible (text contrast, borders, highlighted-field background).
- [ ] Submit a party name with special characters (`O'Brien & Co., "Acme"`) —
      confirm it round-trips correctly through preview and into the downloaded docx
      without breaking the page or corrupting the file.
- [ ] Hit `/create/does-not-exist.md` directly in the browser — should show a clean
      404, not a stack trace.
- [ ] Reload the preview page (`Cmd+R`) after a POST — browser should prompt to
      resubmit the form rather than silently erroring (expected browser behavior,
      not a bug — just confirm it doesn't crash the server).
