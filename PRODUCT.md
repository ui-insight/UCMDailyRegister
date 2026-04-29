# Product

## Register

product

## Users

Three audiences, all internal to the University of Idaho:

- **Submitters (faculty & staff)** — occasional users sending announcements, events, and news items into the newsletter pipeline. Working in browser tabs between other tasks; need a guided, low-friction path that prevents bad submissions.
- **UCM editors** — the daily power users. They triage incoming submissions, apply AI-assisted style edits, manage controlled vocabularies (sections, allowed values, schedule), assemble newsletters, and publish. They live in this tool.
- **SLC Leadership Council and their admins** — preview audience for a private strategic-events calendar. Read-mostly, occasional input.

The two newsletters produced are *The Daily Register* (faculty/staff) and *My UI* (students).

## Product Purpose

An AI-assisted newsletter production pipeline. It absorbs unstructured submissions, applies institutional style rules through an LLM editor, and produces two newsletters on a recurring schedule. Success looks like: editors ship daily without copy-paste fatigue, style consistency is enforced without nagging humans, and submitters get useful constraints up front rather than rejection rounds.

## Brand Personality

**Confident, modern, helpful.** Linear / Notion / Stripe-grade product polish wearing University of Idaho brand colors. The voice is institutional but not stuffy, like a well-run newsroom desk: clear, efficient, mildly opinionated about good prose.

Three words: confident, modern, helpful.

## Anti-references

What this should explicitly NOT look like:

- **Generic SaaS dashboards.** Gradient hero metrics, identical 3-column card grids, "Welcome back, [name] 👋", animated counters. This is a workspace, not a portfolio piece.
- **Old-school university CMS.** Cascade Server / SiteImprove era, tabular layouts, dated chrome, six-deep nested admin menus. The audience is institutional, the interface should not be.
- **Consumer marketing flash.** Bold gradients, animated heroes, scroll-driven sections, motion-heavy compositions. Editors will use this for hours a day; spectacle becomes irritation.
- **AI-tool slop.** Neon-on-black, glassmorphism cards, gradient text, dark glows, the "AI made this" reflex aesthetic. The product *uses* AI; it should not *advertise* AI.

## Design Principles

1. **Editorial calm over product flash.** This is a newsroom workspace, not a SaaS dashboard. Density, restraint, and clear information are the job, never decorative motion or hero-metric vanity.

2. **The interface earns the brand, not the other way around.** UI Pride Gold and Clearwater are powerful colors; they should appear as deliberate accents on a quiet canvas. The UI should feel unmistakably University of Idaho without ever shouting it.

3. **Trust the editor.** Submitters are guided; editors are not. Power-user surfaces (builder, dashboard, style rules) should reward speed and keyboard fluency, not hand-hold.

## Accessibility & Inclusion

- **WCAG 2.1 AA** baseline (US public university standard).
- Editors use this product as a daily tool. Assume long sessions; fatigue tolerance matters more than first-impression dazzle.
- Reduced motion: respect `prefers-reduced-motion`; any motion must be functional, never decorative.
- Color-contrast caution: UI Pride Gold (#F1B300) on white fails AA for body text. Use Gold for accents and decoration only, never for text, links, or critical UI affordances. Clearwater 700+ on white is the safe text accent.
