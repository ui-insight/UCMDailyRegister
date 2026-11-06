# Editorial model evaluation, Nov. 6, 2026 (baseline)

- Run at: 2026-11-06T21:47:49+00:00
- Model: mindrouter / moonshotai/kimi-k3
- Rules: db (policy fingerprint 2026-11-04:5d5635cf9172 (TDR rules))
- Runs per case: 3
- Checks passed (excluding pending cases): 163 of 165 (99%)

| Case | Issues | Result | Failing checks |
| --- | --- | --- | --- |
| clear-notice-untouched | #396 | pass | — |
| product-names-protected | #396 | pass | — |
| person-and-event-names-protected | #396 | pass | — |
| composition-title-protected | #396 | pass | — |
| organization-name-not-extended | #396 | pass | — |
| unclear-venue-flagged | #396, #385 | pass | — |
| acronym-used-once | #381 | pass | — |
| acronym-reused | #381 | FAIL | body_matches: Center for Example Data Science \(CEDS\) (2/3); body_matches: CEDS[^)] (2/3) |
| never-spell-out-tdr | #381 | pass | — |
| never-spell-out-myui-only | #381 | pass | — |
| familiar-acronym-ai | #399 | pass | — |
| event-detail-order | #373 | pass | — |
| headline-rules | #376 | pass | — |
| curly-quotes | #409 | pass | — |
| can-not-may | #409 | pass | — |
| meaning-and-eligibility-kept | #377 | pass | — |
| weekday-date-conflict-kept-and-flagged | #384 | pass | — |
| headline-body-date-conflict | #384 | pass | — |
| added-weekday-is-correct | #410 | pass | — |
| date-has-passed | #410 | pending | flag_matches: (?i)date has passed (0/3) |
| year-unclear | #410 | pending | flag_matches: (?i)confirm year (0/3) |
| no-invented-speaker | #378 | pass | — |
| job-listing-format | #387 | pass | — |

## Outputs of failing runs

### acronym-reused, run 2

**Headline:** Book a free data science consultation

**Body:** The Center for Example Data Science offers free consultations for faculty starting research projects. The center also runs monthly workshops. Contact the Center for Example Data Science to book a session.

**Flags:** event_details_required: Event listing may be missing: time, date; spell_out_acronyms: CEDS expanded to Center for Example Data Science based on submission context; editor should verify this is the official name; contact_information: No email address, phone number or link provided for booking a session; editor may want to request contact details from submitter

### date-has-passed, run 1

**Headline:** Review benefits choices before open enrollment ends Oct. 15

**Body:** Open enrollment for employee benefits ends Thursday, Oct. 15. Review your choices in the Example Benefits Portal.

**Flags:** event_details_required: Event listing may be missing: time, location; date_conflict: [DATE CONFLICT: OCT. 15, 2026, IS A THURSDAY, BUT THE SUBMISSION DATE OF FRIDAY, NOV. 6, 2026, IS AFTER THIS DEADLINE. CONFIRM THE INTENDED YEAR OR DEADLINE DATE.]

### date-has-passed, run 2

**Headline:** Review your benefits choices before open enrollment ends Oct. 15

**Body:** Open enrollment for employee benefits ends Thursday, Oct. 15. Review your choices in the Example Benefits Portal.

**Flags:** event_details_required: Event listing may be missing: time, location; date_conflict: [DAY OF WEEK NOT VERIFIED: Oct. 15, 2026, falls more than 30 days after the Nov. 6, 2026 submission date if resolved to the next occurrence; the deadline may precede the submission date. Confirm the intended year for Oct. 15.]

### date-has-passed, run 3

**Headline:** Review benefits choices before open enrollment ends

**Body:** Open enrollment for employee benefits ends Thursday, Oct. 15. Review your choices in the Example Benefits Portal.

**Flags:** event_details_required: Event listing may be missing: time, location; date_conflict: [DATE CONFLICT: OCT. 15, 2026, IS A THURSDAY; THE SUBMISSION DATE OF FRIDAY, NOV. 6, 2026, FALLS AFTER THIS DEADLINE, SO THE NEXT OCCURRENCE OF OCT. 15 WOULD BE FRIDAY, OCT. 15, 2027. CONFIRM THE INTENDED YEAR AND DEADLINE]

### year-unclear, run 1

**Headline:** Save the date for the Example Teaching Conference

**Body:** The Example Teaching Conference returns Friday, Aug. 20, with sessions on course design and student engagement.

**Flags:** event_details_required: Event listing may be missing: time, location; event_details: Event listing is missing a time and location.

### year-unclear, run 2

**Headline:** Save the date for the Example Teaching Conference

**Body:** The Example Teaching Conference returns Friday, Aug. 20, with sessions on course design and student engagement.

**Flags:** event_details_required: Event listing may be missing: time, location; event_details: Event listing is missing a time and location, which are required for event-related listings.

### year-unclear, run 3

**Headline:** Save the date for the Example Teaching Conference

**Body:** The Example Teaching Conference returns Friday, Aug. 20, with sessions on course design and student engagement.

**Flags:** event_details_required: Event listing may be missing: time, location; event_details: Event listing is missing a time and location.

