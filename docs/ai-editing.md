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
 LLM Call (Claude, OpenAI, or MindRouter)
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

## Editor Review Modes

Once the AI pipeline produces an edit, the editor reviews changes on the **AI Suggested** tab using one of three modes, selectable via a toggle:

| Mode            | Description                                                              |
|-----------------|--------------------------------------------------------------------------|
| **Side by Side**| Two-column layout with the original text on the left and AI-edited text on the right. Useful for reading the full copy in context and judging overall flow. Stacks vertically on small screens. Default view. |
| **Inline Diff** | Word-level diff with red strikethrough (deletions) and green highlights (insertions). Shows exactly what the AI changed, token by token. |
| **Live View**   | Editable AI-suggested headline, body, links, and linked-body preview. Editors can save a draft or approve the submission directly, or carry their changes into **Final Edit**. |

All modes display flags and a changes-made summary below the comparison or editor.

### Two editors, or a slow AI edit

Each save names the staff revision the editor's view was loaded with. If
another editor saved in the meantime, nothing is saved: the Editor shows the
newer version beside the unsaved text, and staff either load the newer version
or deliberately save theirs over it. An AI edit that finishes after staff saved
or approved the item keeps its suggestion in the history but leaves the status
and approval alone; only a submission still awaiting review becomes
"AI edited".

### Interrupted edits and retry

Accepted edits are recorded in `ai_edit_tasks` before background execution. Poll
`GET /api/v1/ai-edits/tasks/{task_id}` for their durable status and result. A
successful task and its edit versions commit together. Completed results remain
available after restart; queued/running tasks are marked failed at startup with
an interruption message. The Editor keeps polling the same task through brief
connection/gateway failures without re-sending the edit request. Staff can run
the edit again in the Editor, or retry
the same task through `POST /api/v1/ai-edits/tasks/{task_id}/retry`. Retrying an
active or successful task returns its existing state/result without another run.
Interrupted external calls are not automatically replayed.

Only one active request per submission/newsletter is admitted. Identical pending
requests share a task ID; different instructions receive 409 until it finishes.
Source copy, category, target, notes and links are fingerprinted when queued and
checked before execution and before saving. A changed source fails the old task;
reload and request a fresh edit. Newer staff copy/approval remains authoritative;
a suggestion completed after a staff save is retained only as history.

`AI_EDIT_MAX_CONCURRENCY` limits concurrent model calls (default 2), and
`AI_EDIT_MAX_PENDING` limits queued plus running requests (default 50). A full
queue returns 503 with `Retry-After: 5`. The current dispatcher supports the
single-process backend used by Compose; do not add workers or replicas without
replacing startup recovery and admission with coordinated worker leases.

Task instructions and result JSON may contain unpublished copy or incidental
personal data. They follow the parent submission's handling/retention category
and are deleted with it. Completed task rows are not cached in process memory.
There is no automatic task-history purge or new retention period.

### Links in Live View and Final Edit

Each link pairs a destination with the exact words in the body that carry it.
A link stays on the mention it was attached to: editing other text, even
typing the same words earlier in the body, does not move it. When the link
words appear more than once, a picker under the link lists each mention with
its surrounding words so staff can choose which one gets the link. If a link's
words are no longer in the body, the link shows a warning and saving is
blocked until the words are restored, changed, or the link is cleared, so a
link is never dropped silently.

## Edit Version Storage

Each pipeline run creates an `EditVersion` record with `Version_Type = AI_Suggested`. The original submission text is stored in a separate `Original` version. When an editor finalizes the copy, an `Editor_Final` version is created. No version is ever modified after creation.

```
Original  -->  AI_Suggested  -->  Editor_Final
```

This produces a complete, auditable trail of every change made to a submission.

Saving a final with **Approve** records that exact version as the submission's
approved revision (`Approved_Version_Id`); saving a draft leaves the
submission in review with nothing approved. The Editor reopens, and newsletter
assembly publishes, the revision chosen by `app/services/editorial_content.py`,
and each assembled item records the version it was copied from
(`Source_Version_Id`).

## Provider Abstraction

The LLM provider is selected at startup via the `LLM_PROVIDER` environment variable:

| Value        | Provider                     | Model (default)            | Notes                            |
|--------------|------------------------------|----------------------------|----------------------------------|
| `claude`     | Anthropic Claude API         | claude-sonnet-4-20250514   | Cloud API, requires API key      |
| `openai`     | OpenAI API                   | gpt-4o                     | Cloud API, requires API key      |
| `mindrouter` | U of I MindRouter (on-prem)  | moonshotai/kimi-k3         | On-prem, OpenAI-compatible API   |

All providers implement a common `LLMProvider` interface with two methods:

```python
class LLMProvider(ABC):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> LLMResponse: ...

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict: ...
```

Switching providers requires only changing the environment variable and restarting the backend. No code changes are needed.

### MindRouter Details

MindRouter is the University of Idaho's institutional AI services platform, hosted at `mindrouter.uidaho.edu`. It exposes an OpenAI-compatible `/v1/chat/completions` endpoint, which the `MindRouterProvider` calls using `httpx`.

Key implementation details:

- **`<think>` block stripping** -- Qwen3 models emit reasoning tokens wrapped in `<think>...</think>` tags before their actual response. The provider strips these automatically.
- **Markdown fence stripping** -- JSON responses sometimes arrive wrapped in ` ```json ... ``` ` fences, which are removed before parsing.
- **Timeout** -- 120-second timeout for the HTTP call (on-prem inference can be slower than cloud APIs).
- **Bearer token auth** -- set via `MINDROUTER_API_KEY`.

??? example "Environment Configuration"
    ```bash
    # .env — Claude
    LLM_PROVIDER=claude
    ANTHROPIC_API_KEY=sk-ant-...

    # .env — OpenAI
    LLM_PROVIDER=openai
    OPENAI_API_KEY=sk-...

    # .env — MindRouter (on-prem)
    LLM_PROVIDER=mindrouter
    MINDROUTER_API_KEY=mr2_...
    MINDROUTER_ENDPOINT_URL=https://mindrouter.uidaho.edu/v1/chat/completions
    MINDROUTER_MODEL=moonshotai/kimi-k3
    ```

## Governance and the separate ops classifier

Newsletter prompts include original copy, submitter notes, provided URLs/anchor
text, category and staff instructions with active style rules. A repair pass may
resend the original prompt, generated draft and findings. Dedicated contact
columns are not inserted, but personal information embedded in free text/links
is not automatically sanitized. The selected provider is controlled by
`LLM_PROVIDER`; the default configuration is Claude, while deployment examples
prefer MindRouter. Provider selection does not establish approved routing.

Event Services uses a separate MindRouter classifier after a harvest. It reads
event title, up to 4,000 description characters, location and category, then
stores needs, confidence, rationale and staff verdicts. It uses `OPS_CLASSIFIER_*`
with endpoint/key fallbacks to `MINDROUTER_*`, independent of newsletter provider
selection. The content hash tracks assessed source text; per-assessment model and
prompt version identifiers are not currently persisted.

See [Data governance](data-governance.md) for the complete sharing/processor
inventory and [Governance decisions](governance/decisions.md) for pending
model, gateway, contract and classification approvals. No blanket vendor
residency, zero-retention or legal-compliance claim is inferred from the code.
