# Making the newsletter application dependable

September 18, 2026 · Summary for editors and product owners

## What we learned

The application has made useful progress since development began in February. It has a foundation we can continue to build on. It now needs a focused period of reliability improvements before people can confidently depend on it for daily newsletter production.

The most important promise is simple: **what an editor checks and approves must be what readers receive.** Facts, staff corrections, dates and links must survive every step from submission to the finished newsletter.

Our review found that similar complaints have returned over several months. Some concern AI wording, but others concern how the application saves and passes information between its screens and the final Word document. Adding more AI instructions will not solve all of them.

## What this means in everyday work

| What staff experience | What the review found | What needs to improve |
|---|---|---|
| “I corrected this, but older wording came back.” | Different parts of the application can choose different saved versions. A test confirmed that newsletter assembly can select an older final version. | One clearly identified approved version, with deliberate handling of later changes. |
| “The link looks right, but does not work in Word.” | A test confirmed that the Word document can keep blue underlined words while losing their web address. | Check the actual clickable link in the finished document. |
| “We have already explained this editing rule.” | Both running environments contain all 99 current rules. Some instructions conflict, and the AI still needs stronger checks. | Clear editorial decisions, consistent instructions and repeated testing with realistic examples. |
| “The AI changed what the submission meant.” | Reports repeatedly describe lost purpose, audience information, recurring-event details or added assumptions. | Preserve the facts and meaning; ask staff to resolve uncertainty instead of guessing. |

Not every new report proves that a previous fix broke. Some reveal an older gap; others add a requirement or clarify what staff need. We should record that distinction and test the complete process.

We also need to verify who can enter staff-only areas, how interrupted work is recovered, and whether a backup can restore the service in time for a newsletter deadline. The review did not establish that backups are absent or that an intrusion occurred. It identified checks that must be completed before making a dependable-service commitment.

## Why Joy and the team's involvement matters

**Joy and the UCM team's continued engagement made this review more useful by showing where the application falls short in real editorial work. Joy's detailed reports gave us a documented history of recurring problems and concrete examples to investigate.**

There is evidence for that contribution:

- The [July feedback record](feedback-digest-2026-07-17.md) documented 48 reports submitted between May 14 and July 17. It attributed 43 to Joy and left five anonymous. Those reports already raised concerns about original text, dates, job listings and links.
- The September 15 batch added 17 reports. These explained what correct behavior should look like, including preserving staff edits across scheduling changes and keeping links working through the final Word document. All 17 are now recorded as [tracked issues](https://github.com/ui-insight/UCMDailyRegister/issues?q=is%3Aissue%20created%3A2026-09-18%20label%3Auser-feedback).
- Repeated reports made patterns visible. For example, the [August headline report](https://github.com/ui-insight/UCMDailyRegister/issues/276) and [September follow-up](https://github.com/ui-insight/UCMDailyRegister/issues/376) both describe headlines repeating the opening sentence. That history prompted a broader question: how do we verify that editorial requirements remain satisfied after a change?
- The concerns about [staff edits](https://github.com/ui-insight/UCMDailyRegister/issues/386) and [finished-document links](https://github.com/ui-insight/UCMDailyRegister/issues/389) guided checks that confirmed specific defects. The feedback identified the experience; examining and testing the application established the cause.

The clearest individual attribution in the records is to Joy; anonymous reports should remain anonymous. The team's role now is to help judge whether the repaired workflow meets editorial needs. Responsibility for fixing defects, checking releases and following up belongs to the development team—not to users repeatedly rediscovering the same problems.

## Our proposed remediation plan

This is the recommended order of work. The review and issue filing are complete; the repairs below are not yet complete, and delivery dates and named owners still need to be agreed.

| Order | Work | How we will know it is successful |
|---|---|---|
| 1. Protect staff work and access | Correct saved-version selection, preserve Word links, and verify staff sign-in and permissions. | The approved text and working links appear in the finished document; people only access the areas appropriate to them. |
| 2. Make the whole workflow consistent | Keep staff changes intact when dates, newsletter selections and screens change. Clearly identify changes made after approval. | A representative announcement can travel through editing, scheduling, assembly and export without losing approved work. |
| 3. Make AI behavior more dependable | Resolve conflicting instructions and test the AI actually used by the application against agreed examples. | Checks show whether facts, meaning, dates, audience and links were preserved; unresolved questions are shown to staff. |
| 4. Prepare for interruptions | Verify recovery of interrupted work, backup restoration, alerts and a practical manual fallback. | A demonstrated recovery meets an agreed newsletter deadline, and staff know what to do when the service is unavailable. |
| 5. Keep improvements from slipping | Check complete workflows before release, update guidance and confirm fixes in the version staff actually use. | Each report can be followed from receipt to fix, release and editorial confirmation. |

## Decisions for product owners

We need editorial agreement on a few practical questions:

- Should “today” and “tomorrow” be replaced by calendar dates, or retained alongside them? Which publication date should govern the wording?
- When a submitted weekday and date disagree, should the application preserve both and ask staff to confirm the intended date? That is the recommendation.
- How should job titles appear while editing and in the published single-line listing?
- How much interruption or lost work is acceptable near a publication deadline, and who can approve the manual fallback?
- Which newsletter reliability milestones should be met before further expansion of the leadership-calendar and event-services features?

Development should prepare and run the checks first. Joy and the team should then review a manageable set of familiar examples in the updated application. A fix is ready to close when the complete outcome works where staff use it—not simply when a software change has been written.

The [technical review](architecture-review-2026-09-18.md) contains the supporting evidence, limitations and implementation recommendations.
