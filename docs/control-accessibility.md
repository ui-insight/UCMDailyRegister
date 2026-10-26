# Control accessibility baseline

Version **1.2**, October 26, 2026. Engineering implementation and evidence for
[#248](https://github.com/ui-insight/UCMDailyRegister/issues/248) and
[#264](https://github.com/ui-insight/UCMDailyRegister/issues/264).
This describes the proposed release, not the current deployment or an
institutional accessibility approval.

## Ownership, provenance and supported use

The repository maintainers own implementation and review of these controls.
Brand provenance is the University of Idaho Brand Book 2023, as recorded in
[UI Branding](branding.md). Existing brand/status hex values, Public Sans and
the Tailwind spacing/type scale are retained. This assigns no institutional
Data Owner or accessibility-approval authority.

| Contract | Implementation and guidance |
| --- | --- |
| Color | Gold fills use dark `ui-black` text; gold text on light surfaces uses `ui-gold-800`. Status text uses `-800` on the corresponding `-100` tint. `-500` status hues remain decorative markers, not normal text or white-text fills. |
| Typography | Public Sans, with the existing Tailwind rem sizes and line heights. Small labels, counters and pills must meet the normal-text 4.5:1 floor. Size alone is not an exemption. |
| Spacing | Existing Tailwind quarter-rem spacing scale; native field sizing and wrapping remain available. The segmented group no longer clips its focus outline. |
| Focus | Native interactive elements, links, editable regions and explicit tab stops receive a 2px dark outline with 2px white gap. The dark outline supplies contrast on light surfaces; the white gap supplies contrast on dark surfaces. Do not clip it with ancestor overflow. |
| Field boundaries | Enabled native text/date/number/select/textarea boundaries use `status-muted-500`. Invalid fields use `status-error-800`. These are unlayered rules so legacy utility classes cannot silently weaken the boundary/focus baseline. |
| Selection | Pressed buttons expose `aria-pressed`; current navigation exposes `aria-current`. Both receive an underline independent of their fill/hue. Newsletter target buttons have a named group and native disabled behavior. |
| Names | Native fields have a connected visible label, wrapping label or explicit accessible name. Reusable editor and recurring-form instances use unique IDs. Icon month controls and field-only search/move/filter controls have contextual names. |
| Disabled/read-only | Native controls retain their HTML semantics. Read-only text fields use the muted surface. While submitting, the announcement fields are disabled but its send button stays focusable with `aria-disabled`, enforced by an immediate request lock. |
| Motion | Reduced-motion preference disables transitions, animations and smooth scrolling globally. Loading still has text announcements. |
| Forced colors | System `Highlight` focus, `ButtonText` field boundaries and an inset selected outline supplement the persistent underline; native colors remain adjustable by the browser. |
| Links | Main-content links are underlined as a cue independent of color. Sidebar navigation retains its current-page and native link semantics. |

The intended browser targets are current desktop Chromium, Firefox and Safari,
including native form and keyboard behavior. Automated tests use jsdom; the
local browser check below is a separate evidence point. The target list is not
a claim that every browser/platform/assistive-technology combination was tested.

## Measured semantic pairings

The following ratios use sRGB relative luminance from the actual theme values.
Enabled normal text must reach 4.5:1; essential non-text boundaries reach 3:1.
Disabled-opacity controls and decorative markers are excluded from this table.

| Foreground/boundary | Background | Ratio |
| --- | --- | --- |
| `ui-black` | `ui-gold-500` | 6.83:1 |
| `ui-black` | `ui-gold-600` | 5.18:1 |
| `ui-gold-800` | `white` | 6.46:1 |
| `ui-gold-800` | `ui-gold-100` | 5.71:1 |
| `ui-clearwater-800` | `ui-clearwater-100` | 9.92:1 |
| `status-info-800` | `status-info-100` | 7.15:1 |
| `status-edited-800` | `status-edited-100` | 8.06:1 |
| `status-warning-800` | `status-warning-100` | 6.37:1 |
| `status-success-800` | `status-success-100` | 6.78:1 |
| `status-attention-800` | `status-attention-100` | 5.40:1 |
| `status-error-800` | `status-error-100` | 6.80:1 |
| `status-muted-800` | `status-muted-100` | 9.37:1 |
| `white` | `status-success-800` | 7.68:1 |
| `white` | `status-attention-800` | 7.31:1 |
| `status-muted-500` | `white` | 4.83:1 |
| `status-muted-500` | `status-muted-100` | 4.39:1 |

Regression tests measure all Pill tones and strong status fills, primary/success
buttons and selected segmented text. The selected segment previously measured
1.88:1 (white on gold); the corrected dark text measures 6.83:1. Page-level gold
buttons, gold hints/actions, the calendar's selected day, attention fills and raw
status text were also repaired. Inactive but interactive rule/provider cards retain
readable text rather than reducing opacity across the entire card. The source audit covers native field naming across 54 component
and page files. Static wiring and theme arithmetic do not replace rendered
contrast/focus or screen-reader checks.

## Public submission validation and recovery

- Existing required, email/URL and date/range constraints are collected into one
  focused summary. Links focus the affected fields. Each inline error has an ID,
  `aria-invalid` and `aria-describedby`; instructions/counters are associated too.
  Field errors clear as the user edits, and changing a category/choice clears
  stale errors for hidden fields. Newsletter content and scheduling policy are
  unchanged.
- Known structured server validation maps to displayed fields, including link
  slots and scheduling controls. Other server/network errors remain an announced
  form-level failure. Entered text, notes, links, dates and contact fields remain
  available after rejection.
- A synchronous request lock blocks duplicate submit events. The pending fieldset
  prevents editing the payload being sent. The send control remains focusable
  with its disabled state announced; native disabling had dropped its focus.
- Loading, success and failure use live announcements. Successful submission
  clears announcement fields without automatic scrolling or focus changes.
  An explicit retry reuses the retained work; there is no automatic POST retry.
- A lost response can leave the server outcome unknown. The failure copy asks
  the submitter to check with UCM before sending again. This batch does not add
  server-side idempotency or promise exactly-once delivery; broader interrupted
  write handling remains in #259.

## Evidence and remaining acceptance

Automated checks cover contrast, native names, segmented selection/keyboard use,
required-field summary/focus, resolvable description IDs, retained input after
failure, structured server validation, duplicate-event blocking, loading and
success. Existing editorial and scheduling tests remain in the suite.

An isolated local browser fixture used synthetic data and in-memory mocked API
responses. It verified summary focus, linked-field focus, retained values after a
503, explicit successful retry and retained submit-button focus. The selected
segment, field/error layout and dual focus treatment against a dark surface were
visually inspected. No deployed records or authenticated sessions were used.

Before closing #248/#264, record supported-browser, forced-colors, reduced-motion,
zoom/reflow and screen-reader workflow results, including survey/job/both-newsletter
branches and interruptions. The CSS fallbacks are implemented; forced-colors and
all supported browser/assistive-technology combinations have not been manually
verified here. Broader 320px/200% layout coverage is tracked by #258; dialog workflow
acceptance by #260. No complete WCAG-conformance claim is made.

## Change history

- **1.0:** Existing brand/status theme and shared primitives.
- **1.1, PR #437:** Shared Button contrast and light-surface focus; shared modal and
  destructive-action review. Deployed baseline `88aea8d`.
- **1.2, proposed:** Remaining gold/status page pairings, native field naming,
  group states, un-clipped focus, field boundaries, forced-colors/reduced-motion
  rules and public form validation/recovery described above.
