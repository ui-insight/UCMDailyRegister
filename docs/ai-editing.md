# AI Editing Pipeline

The AI editing pipeline transforms raw submissions into polished newsletter copy by combining rule-based pre-analysis, LLM-powered rewriting, and deterministic post-processing.

## Pipeline Stages

```
Submission text
      |
      v
 Pre-Analysis (rule-based checks)
      |
      v
 Style Rule Loading (from DB)
      |
      v
 LLM Prompt Construction
      |
      v
 LLM Call (Claude or OpenAI)
      |
      v
 Post-Processing (headline case, diff)
      |
      v
 EditVersion stored (immutable)
```

## Pre-Analysis

Before calling the LLM, the pipeline runs deterministic checks to flag common issues:

| Check                    | What it detects                                |
|--------------------------|------------------------------------------------|
| First-person detection   | Uses of "I", "we", "our" in body text          |
| Exclamation marks        | Excessive or inappropriate exclamation points   |
| Event detail check       | Missing date, time, or location for events      |
| URL validation           | Broken or malformed links in submission links   |

Pre-analysis results are passed to the LLM as context so it can address flagged issues in its rewrite.

## Style Rule Loading

Style rules are stored in the `StyleRule` table with a `Rule_Set` column:

- **Shared** -- applies to both newsletters
- **TDR** -- The Daily Register only
- **MyUI** -- My UI only

When editing a submission, the pipeline loads all Shared rules plus the rules for the target newsletter. Rules are grouped by severity (Error, Warning, Suggestion) for prioritized prompt injection.

## LLM Prompt Construction

The prompt sent to the LLM has two parts:

### System Prompt

Contains the editorial persona and all applicable style rules organized by category:

```
You are a university communications editor...

## Error-Level Rules (must fix)
- [rule text from DB]
- ...

## Warning-Level Rules (should fix)
- ...

## Suggestion-Level Rules (consider)
- ...

## Pre-Analysis Flags
- First person detected in paragraph 2
- ...
```

### User Prompt

Contains the submission text and a before/after example demonstrating the expected transformation style:

```
Edit the following submission for [newsletter name].

### Example
**Before:** [raw example text]
**After:** [edited example text]

### Submission to Edit
**Title:** [submission title]
**Body:** [submission body]
```

!!! note "Few-Shot Learning"
    The before/after example in the user prompt grounds the LLM's editing style. Future phases may support multiple examples pulled from previously approved edits.

## Post-Processing

After the LLM returns its suggested edit, deterministic post-processing ensures consistency:

- **Headline case enforcement** -- the title is re-cased according to the `Headline_Case` setting for the target newsletter (Title Case or Sentence Case).
- **Diff generation** -- a structured diff between the original text and the AI suggestion is computed and stored as `Diff_JSON` on the EditVersion record.
- **Whitespace normalization** -- trailing spaces, double spaces, and inconsistent line breaks are cleaned up.

## Edit Version Storage

Each pipeline run creates an `EditVersion` record with `Version_Type = AI_Suggested`. The original submission text is stored in a separate `Original` version. When an editor finalizes the copy, an `Editor_Final` version is created. No version is ever modified after creation.

```
Original  -->  AI_Suggested  -->  Editor_Final
```

This produces a complete, auditable trail of every change made to a submission.

## Provider Abstraction

The LLM provider is selected at startup via the `LLM_PROVIDER` environment variable:

| Value     | Provider                | Model (default)         |
|-----------|-------------------------|-------------------------|
| `claude`  | Anthropic Claude API    | claude-sonnet-4-20250514  |
| `openai`  | OpenAI API              | gpt-4o                  |

Both providers implement the same interface:

```python
async def generate_edit(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000
) -> str:
    ...
```

Switching providers requires only changing the environment variable and restarting the backend. No code changes are needed.

??? example "Environment Configuration"
    ```bash
    # .env
    LLM_PROVIDER=claude
    ANTHROPIC_API_KEY=sk-ant-...
    # or
    LLM_PROVIDER=openai
    OPENAI_API_KEY=sk-...
    ```
