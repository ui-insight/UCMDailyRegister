# Staff action safety

Engineering inventory for [#260](https://github.com/ui-insight/UCMDailyRegister/issues/260),
updated October 26, 2026. This describes the implementation in the staff action
safety branch; deployment and manual assistive-technology acceptance remain separate.

## Persisted removals and replacement

All confirmations name the affected record and explain the effect and recovery.
Cancel receives initial focus. Opening a review does not write to the API.
A confirmed request disables both buttons and blocks dismissal while saving to
avoid duplicate writes and misleading cancellation. Rejected actions either retain
the review with an alert or use the page's existing error alert; no success is shown.
A failed refresh after a successful write can still require reloading the page.
Network-level ambiguous outcomes are tracked separately in #259.

| Workflow | Effect | Protection and recovery |
| --- | --- | --- |
| Builder: remove submission item | Deletes this issue's item and edition-only wording, retaining the source | Confirm names headline and issue date; copy edition wording first. Reassemble to recover eligible approved source copy. |
| Builder: remove imported item | Removes the external item from this issue | Confirm warns about edition wording; add from its source panel again. For recurring messages, use Restore in the Builder's Recurring Messages panel. |
| Builder: skip recurring message | Persists an exclusion for this issue | Confirm identifies headline/date and warns about lost edition wording; Restore adds source copy again. Future issues remain unaffected. |
| Builder: Use approved copy | Replaces edition wording with the reviewed approved source | Source preview followed by confirmation; copy edition-only edits before proceeding. Keep edition copy remains an explicit alternative. |
| Settings: remove mode override | Deletes a date-range override, returning to normal schedule rules | Confirm identifies newsletter/date range/description; recreate the override to restore it. |
| Settings: remove custom date | Deletes an explicitly added publication date | Confirm identifies newsletter/date/description; add the custom date again. |
| Settings: remove blackout | Stops blocking the date under this blackout rule | Confirm identifies date/newsletter/description; re-add the blackout to restore it. Other schedule rules still apply. |
| Editor: remove run schedule | Deletes the schedule and its occurrences, retaining the submission | Confirm names submission/start date and warns that recurring schedules lose every occurrence. Recreate using Add run date and re-enter exclusions. |
| Editor: skip occurrence | Excludes the selected run date | Confirm names submission/date; add a separate run date to restore publication. Other occurrences remain intact. |
| Ops: remove staff-added need | Removes the need from the event, retaining the event | Confirm identifies need/event; Add need restores it. |
| SLC: unflag or dismiss a flagged event | Removes the promoted event from the SLC calendar | Confirm identifies event and calendar effect; flag it again, restoring a dismissed event first when necessary. |
| Style rules: delete | Deletes the reusable rule; existing edit versions remain | Confirm identifies rule key and future AI effect; copy text first and recreate with Add Rule. |
| Recurring library: delete | Deletes the reusable message; existing newsletter items remain | Confirm identifies headline and future assembly effect; copy content/schedule first and recreate with Add Recurring Message. |

## Existing review and reversible controls

- Editor concurrency conflicts display both saved and unsaved wording before the
  explicit “Discard mine and load theirs” or “Save mine instead” actions. This is
  the review step; no additional nested confirmation is added.
- AI suggestions are reviewed against source wording before editorial acceptance.
  Saved edit versions remain available. Feedback export requires the separate
  editable preview and server-confirmed review introduced in #368.
- Ops verdict/status changes retain their suggested/confirmed/dismissed controls
  and Restore/Add need paths. SLC dismissal of an unflagged event is reversible
  through the Dismissed filter and Restore. Flagging and classification changes
  remain direct; removal of an already promoted calendar event requires review.
- Rule and recurring-message activation toggles can be reversed with the same
  control. Reordering/moving newsletter items retains the item and content.
- Transient form rows, preferred-date selections, image/link edits and unsaved
  form cancellation operate within an editing session; persisted removal paths
  are listed above. Source/edition replacement uses the review described above.

## Shared dialogs

Confirmations and the feedback form share the same portal, unique accessible
names, focus containment, Escape handling, background inert isolation, scroll
containment and focus return. Stacked dialogs isolate the topmost dialog. When a
successful removal deletes the invoking control, focus falls back to the main
content region. Feedback starts at Short summary and preserves unfinished text
when canceled or closed with Escape. Successful submission clears the report.

## Verification and remaining acceptance

Automated synthetic-data checks cover single/stacked focus lifecycle, retained
inert state, Tab/Shift+Tab and Escape; confirmation cancellation, pending-request
serialization, failure announcement/retry; feedback draft retention; Settings
removals; Builder replacement; schedule removal; SLC unflagging; and Ops need
removal. These establish behavior, not complete accessibility conformance.

A local in-app-browser check using synthetic data confirmed initial Cancel focus,
reverse Tab containment, Escape without saving, focus return, feedback initial
summary focus and draft retention on reopening. The dialog and form layouts were
visually inspected at the default 1280×720 viewport. This was a shared-component
fixture, not a complete staff workflow or screen-reader acceptance test.

Before closing #260, retain manual browser and screen-reader evidence:

1. Open each representative removal using only the keyboard. Confirm the record,
   consequence and recovery are announced, and Cancel is focused.
2. Tab and Shift+Tab at both boundaries; attempt background navigation. Escape
   must cancel before saving, restore focus, and leave data unchanged.
3. Confirm a synthetic removal and a failed request. Check saving/error
   announcements, one request per confirmation, and meaningful focus after the
   invoking control disappears.
4. Open feedback, type a synthetic draft, Escape and reopen; verify retained
   wording, labels, focus containment and successful/failed submission behavior.
5. Check short viewports and 200% zoom for reachable controls and scroll behavior.
   Record browser/screen reader/version and outcome. Contrast/focus-token work
   remains tracked by #248; broader reflow and network recovery by #258/#259.
