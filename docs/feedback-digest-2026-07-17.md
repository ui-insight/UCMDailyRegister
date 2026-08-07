# Joy's Feedback Digest — prepared 2026-07-17

Source: `product_feedback` table, production database (`ucm_newsletter` on insight-db).
48 reports total (43 from jbauer@uidaho.edu, 5 anonymous filed in the same sessions), 2026-05-14 → 2026-07-17. **All 48 still have status `new`.**

Report numbers below refer to chronological order (1 = oldest).

---

## Theme 1 — The off-by-one date bug (her most-reported issue; root cause identified)

Reports **9, 26, 44, 47** all describe the same thing: she requests a run date (e.g. Monday 6/29 or 7/20), and staff view / the Builder header shows the day before (Sunday 6/28, 7/19). Report 47 opens with *"I've brought this one to your attention before."*

Reports **5, 25, 40, 41–42, 43** are very likely the same bug wearing different costumes:
- 5 & 43: Builder shows the wrong day's entries / no entries for a date she knows has items.
- 25: "Sunday should not be a selectable option" — a Monday shifted back a day renders as Sunday.
- 40: Monday Oct. 5 rejected as invalid for My UI — consistent with it being validated as Sunday Oct. 4.
- 41–42: dates rejected as "not a valid publication date."

**Root cause (from today's code audit):** date-only strings parsed as UTC midnight (`new Date('2026-07-20')`) render/validate one day earlier in Mountain time. Confirmed in `BuilderPage.tsx:1085`, `BuilderPage.tsx:1317`, `SubmissionMeta.tsx:187/203/229`; UTC "today" math in `SchedulePrefs.tsx`, `SubmissionMeta.tsx`, `BuilderPage.tsx`. Other pages already use the safe `+'T12:00:00'` pattern. **Fixing this one bug likely resolves ~9 of her 48 reports.**

## Theme 2 — Manual edit destroys the original submission (root cause identified)

Reports **12, 29**: saving a manual/final edit overwrites the Original view; *"We always need a record of what was originally submitted that remains intact."*
Related asks: **11** (show original beside the manual-edit window), **12** (let her edit the AI version directly, side-by-side with original).

**Root cause (from audit):** `POST /ai-edits/{id}/finalize` overwrites `Original_Headline`/`Original_Body` (`backend/app/api/v1/ai_edits.py:313`). If no AI edit ran first, the submitter's original is unrecoverable.

## Theme 3 — AI style-rule adjustments (13 reports; these are her editing the prompt via the bug tracker)

Reports **2, 3, 10, 13, 14, 15, 16, 17, 18, 19, 27, 28, 30** each contain a ready-to-use style rule:
- Times: noon/midnight, "to" vs hyphen across a.m./p.m., full AP time rules (28)
- Headlines: sentence case but capitalize proper nouns (10, 30 — see Theme 4)
- Acronyms: spell out on first reference (13)
- Spell out state names (14); "&" → "and" (15)
- Don't touch event titles' title case (16)
- Event info order: time, day, date, location (17, also 39)
- "MDT" → "Mountain time" (18); periods on directional abbreviations (19)
- Short sentences, no semicolons (27)
- Overall tone/structure prompt rewrite (3)

These are mostly **data changes in the Style Rules UI**, not code. ⚠️ But note audit finding: the seed script **force-reverts style-rule text on every redeploy** (`backend/app/db/seed.py:106`, run by `docker-entrypoint.sh`). If rules were added in the UI and later reverted, that explains Theme 4.

## Theme 4 — "I reported this and it's still broken" (trust erosion)

Reports **21, 30, 38**: headline proper-noun capitalization reported three times over three weeks; *"It does not respond to Editor feedback... It makes no changes after I select Revise."* Report 34 (jobs): *"I believe I reported this last week... If this requires a call to sort out, please let me know."*
Candidate causes: seed reverting rule edits (Theme 3 warning), and/or editor feedback not persisting (Theme 5).

## Theme 5 — Editor feedback should teach the system, not just fix one item

Reports **31, 39**: feedback given in the AI controls applies only to the current submission; she wants it to update the instruction set for all future edits. This is a real feature request (feedback → persisted style rule), not a bug.

## Theme 6 — Job postings need a completely different pipeline

Reports **8, 20, 22, 23, 34** (repeated, escalating): jobs should not get AI news-style editing or headlines. Wanted format: one line per job — `Job title (sentence case), Department (capitalized), location (omit if Moscow)` — as a live link, in a dedicated "Job opportunities" section at the bottom of the Builder. Remove "how many times to run" from the job submission form (jobs always run once, for two weeks).

## Theme 7 — Builder gaps

- **33**: show the full approved entry text, not just the first sentence.
- **45**: "Academic dates and deadlines" drop-zone doesn't accept anything (she wants to pull from uidaho.edu/registrar/dates-deadlines).
- **46**: wants manual editing inside the Builder.
- **35**: new section under Employee Announcements: **"Reminders for your students"** (staff-only, not in submitter view).

## Theme 8 — Scope confusion / remove features

- **1**: Auxiliary Services calendar spreadsheet import is flooding submissions with unusable items — remove it entirely.
- **6, 7**: doesn't know what the SLC calendar is or why it's in the tool ("Did someone else request it?").
- **24**: "Repeat on a cadence" should be staff-only, not in submitter view.

## Theme 9 — Links & URLs

- **32**: in edit mode, links render as raw code/plain text; wants CTA text as a live link with the URL editable separately, and the ability to add URLs/CTAs while editing.
- **37**: accept email addresses as links, with a name field beside them.

## Theme 10 — Scheduling rules & settings (data/config)

- **36**: My UI runs every Monday including holidays; TDR skips holidays — holiday blocking must be per-newsletter.
- **48** (filed today): My UI submission deadline should be noon Wednesday during the academic year — Settings change.

## One-off

- **4**: two users got different AI results for the same submission — expected LLM nondeterminism; worth explaining (or lowering temperature) rather than "fixing."

---

## Suggested meeting talking points

1. Acknowledge the backlog: 48 reports received, none triaged — own it, then show the themes above so she knows they were heard.
2. Quick wins to promise: the off-by-one date fix (kills ~9 reports), original-preservation fix, loading her 13 style-rule prompts.
3. Decisions to ask of her: job-posting format sign-off (Theme 6), SLC calendar's future (Theme 8), "Reminders for your students" section details.
4. Set expectations on Theme 5 (feedback that persists) — real feature, worth scoping together.

---

## GitHub issues (filed 2026-07-17)

All 48 reports were exported to 13 issues; each `product_feedback` row now has `Status=exported` and its `GitHub_URL` set.

| Issue | Covers reports |
|---|---|
| [#192](https://github.com/ui-insight/UCMDailyRegister/issues/192) UTC off-by-one dates | 5, 9, 25, 26, 40, 41, 42, 43, 44, 47 |
| [#193](https://github.com/ui-insight/UCMDailyRegister/issues/193) Finalize overwrites original | 11, 12, 29 |
| [#194](https://github.com/ui-insight/UCMDailyRegister/issues/194) 13 AP-style rule adjustments | 2, 3, 10, 13–19, 27, 28, 30 |
| [#195](https://github.com/ui-insight/UCMDailyRegister/issues/195) Seed reverts style-rule edits | 21, 38 |
| [#196](https://github.com/ui-insight/UCMDailyRegister/issues/196) Persistent editor feedback | 31, 39 |
| [#197](https://github.com/ui-insight/UCMDailyRegister/issues/197) Job postings pipeline | 8, 20, 22, 23, 34 |
| [#198](https://github.com/ui-insight/UCMDailyRegister/issues/198) Builder: full text + manual edit | 33, 46 |
| [#199](https://github.com/ui-insight/UCMDailyRegister/issues/199) Builder: academic-dates drop-zone | 45 |
| [#200](https://github.com/ui-insight/UCMDailyRegister/issues/200) Builder: "Reminders for your students" | 35 |
| [#201](https://github.com/ui-insight/UCMDailyRegister/issues/201) My UI Monday/holiday rules + deadline | 36, 40*, 48 |
| [#202](https://github.com/ui-insight/UCMDailyRegister/issues/202) CTA links + email links | 32, 37 |
| [#203](https://github.com/ui-insight/UCMDailyRegister/issues/203) Scope decisions (Aux import, SLC, cadence) | 1, 6, 7, 24 |
| [#204](https://github.com/ui-insight/UCMDailyRegister/issues/204) AI nondeterminism between users | 4 |

*Report 40's DB row points at #192 (likely the UTC bug); it's cross-referenced in #201 for retest.
