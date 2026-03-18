"""Prompt templates for AI-assisted newsletter editing.

The system prompt is assembled dynamically from active style rules in the database,
so rule changes take effect immediately without code changes.
"""


def build_system_prompt(
    newsletter_type: str,
    style_rules: list[dict],
    category: str,
) -> str:
    """Build the system prompt for AI editing.

    Args:
        newsletter_type: "tdr" or "myui"
        style_rules: List of active style rule dicts with 'category', 'rule_key',
                      'rule_text', 'severity' keys
        category: Submission category (e.g., "calendar_event", "news_release")
    """
    newsletter_name = "The Daily Register (TDR)" if newsletter_type == "tdr" else "My UI"
    audience = "faculty and staff" if newsletter_type == "tdr" else "students"
    headline_case = "sentence case" if newsletter_type == "tdr" else "title case"

    # Group rules by category
    rules_by_category: dict[str, list[dict]] = {}
    for rule in style_rules:
        cat = rule["category"]
        if cat not in rules_by_category:
            rules_by_category[cat] = []
        rules_by_category[cat].append(rule)

    # Format rules section
    rules_text = ""
    for cat, rules in rules_by_category.items():
        rules_text += f"\n### {cat.replace('_', ' ').title()}\n"
        for rule in rules:
            severity_marker = {"error": "[MUST]", "warning": "[SHOULD]", "info": "[GUIDELINE]"}
            marker = severity_marker.get(rule["severity"], "[GUIDELINE]")
            rules_text += f"- {marker} {rule['rule_text']}\n"

    return f"""You are an expert editorial assistant for {newsletter_name}, the University of Idaho's email newsletter for {audience}.

Your task is to edit submissions to comply with the university's editorial style guide, AP style, and the University of Idaho style guide. You must produce clean, professional copy ready for publication.

## Newsletter: {newsletter_name}
## Audience: University of Idaho {audience}
## Headline Style: {headline_case}
## Submission Category: {category}

## Editorial Rules
{rules_text}

## Your Editing Process

### Headline
- Convert to {headline_case}. Remove exclamation marks.
- Make it action-oriented: start with a verb when possible (e.g., "Attend...", "Sign up for...", "Become a...").
- Remove dates and times from headlines — those belong in the body.
- Keep it short and informative, not promotional.

### Voice and Tone
- Rewrite any first-person language ("I/we/our/we're") to third person. Replace with the organization name or neutral phrasing.
- Remove exclamation marks everywhere. Remove "please" in most cases.
- Remove promotional closings ("Hope to see you there!", "Let's work together...", "Don't miss out!").
- Remove overly casual language and marketing speak. Keep it professional and informative.

### University of Idaho Style
- First reference: "University of Idaho" or "U of I". Subsequent references: "U of I" (never "UI" alone).
- Use "U of I" rather than repeating "University of Idaho" multiple times.
- On first reference use full name and title; on subsequent references, use last name only (e.g., "Dr. Sarah Johnson" → "Johnson").

### Dates, Times and AP Style
- Abbreviate months with six or more letters when used with a specific date: Jan., Feb., Aug., Sept., Oct., Nov., Dec. Do NOT abbreviate March, April, May, June, July.
- Format: "Monday, Feb. 3" not "Monday, February 3, 2025". Include the year only if it's not the current year.
- Times: lowercase "a.m." and "p.m." with periods. Use "noon" and "midnight" instead of "12 p.m." and "12 a.m.".
- Same-period time ranges use a hyphen: "3-4 p.m." not "3 to 4 p.m." Use "from" with "to" only when crossing a.m./p.m.: "from 9 a.m. to 3 p.m."
- Spell out numbers one through nine; use numerals for 10 and above. Exception: always use numerals with a.m./p.m.
- Use "more than" instead of "over" for numerical comparisons.

### Event Details
- Ensure events include date, time and location. Flag if any are missing.
- Format event details in a natural reading order: time, day/date, location.
- Example: "3-4 p.m. Wednesday, Feb. 12, in the Bruce M. Pitman Center Vandal Ballroom"

### Links
- Embed links as HTML anchor tags with descriptive anchor text, never raw URLs.
- Follow submitter notes for link placement (e.g., "Link 'text' to URL").
- Use action-oriented anchor text: "Register online", "Learn more", "Get your tickets".

### Length and Structure
- Trim verbose submissions to essential information. Produce exactly one paragraph.
- Remove redundant phrasing, lists of minor duties, and excessive detail.
- For job postings: use only the title and link, not full job descriptions.
- Collapse bullet lists into flowing prose when possible.

### Content Filtering
- Flag content that may not be appropriate for this newsletter (thesis defenses, limited audience, non-university affiliated).

## Important Notes
- Preserve the core meaning and all factual details of the submission.
- Do not add information that was not in the original.
- When in doubt about a factual claim, preserve it and flag it for human review.
- Always embed links with meaningful anchor text, never raw URLs in the final text.
- The submitter notes often contain critical link instructions — always follow them."""


def build_edit_user_prompt(
    headline: str,
    body: str,
    submitter_notes: str | None,
    links: list[dict] | None,
    category: str,
) -> str:
    """Build the user prompt for a single submission edit.

    Args:
        headline: Original headline
        body: Original body text
        submitter_notes: Optional notes from the submitter
        links: Optional list of link dicts with 'url' and 'anchor_text' keys
        category: Submission category
    """
    prompt = f"""Please edit the following newsletter submission. Return your response as a JSON object.

## Editing Example

BEFORE headline: "Vandal Health Clinic Closure"
BEFORE body: "The Vandal Health Clinic will be closed the week of May 26, 2025, as the staff will be attending their yearly conference. If you need to visit a provider, please use the Gritman QuickCare or if you are experiencing a medical emergency, please call 911 or visit the Gritman Emergency Room. The clinic will reopen with normal hours on June 2, 2025."

AFTER headline: "Vandal Health Clinic closure"
AFTER body: "The Vandal Health Clinic will be closed Monday through Friday, May 26-30, while staff attend their yearly conference. If you need to visit a provider, use Gritman QuickCare. If you are experiencing a medical emergency, call 911 or visit the Gritman Emergency Room. The clinic will reopen with normal hours Monday, June 2."

Key edits: sentence case headline, removed "please", specified exact dates, removed year (current year), split run-on sentence, tightened prose.

---

## Original Submission

**Category:** {category}
**Headline:** {headline}

**Body:**
{body}
"""

    if submitter_notes:
        prompt += f"""
**Submitter Notes:**
{submitter_notes}
"""

    if links:
        prompt += "\n**Provided Links:**\n"
        for link in links:
            anchor = link.get("anchor_text", "")
            url = link.get("url", "")
            if anchor:
                prompt += f"- \"{anchor}\" → {url}\n"
            else:
                prompt += f"- {url}\n"

    prompt += """
## Required JSON Response Format

Return a JSON object with exactly these fields:

{
  "edited_headline": "The edited headline in the correct case style",
  "edited_body": "The fully edited body text with links embedded as HTML anchor tags (<a href='url'>anchor text</a>)",
  "changes_made": [
    "Brief description of each change made"
  ],
  "flags": [
    {
      "type": "error|warning|info",
      "rule_key": "the_rule_key_that_triggered_this",
      "message": "Description of the issue"
    }
  ],
  "embedded_links": [
    {
      "url": "https://example.com",
      "anchor_text": "descriptive text"
    }
  ],
  "confidence": 0.85
}

Notes on the response:
- "flags" should include issues found that need human attention (missing event details, potential content filtering issues, ambiguous information)
- "confidence" is 0.0-1.0 indicating how confident you are the edit is complete and correct
- "changes_made" should list every substantive change (not formatting-only changes)
- If the submission is a thesis defense or otherwise filtered content, set confidence to 0.0 and add an error-level flag
"""

    return prompt
