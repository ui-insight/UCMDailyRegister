"""AI classifier for operational service needs hiding in event listings.

The Trumba feed carries no catering/alcohol/setup metadata — the signal
lives in free text ("reception to follow", "refreshments provided") and in
the location fields. This module reads one harvested event's text and
returns suggested operational needs from a controlled vocabulary, each with
a confidence level and a one-line rationale quoting the event's own wording.

The classifier always runs on MindRouter (the university's on-prem AI
platform) so event text never leaves campus infrastructure, and it is
deliberately independent of the global LLM_PROVIDER switch that drives the
newsletter editing pipeline: build_ops_classifier_provider() constructs its
own MindRouterProvider from the OPS_CLASSIFIER_* settings, falling back to
the MINDROUTER_* endpoint and key when unset. The default model is Qwen 3.6
27B (OPS_CLASSIFIER_MODEL overrides it; confirm the exact id against the
MindRouter catalog per deployment).

assess_event() is the whole interface: fields in, validated suggestions
out. Malformed model output raises ValueError; connectivity failures
propagate as httpx errors. Callers decide retry policy — the classify-
pending step simply leaves failed events unassessed for the next run.
"""

import logging
from dataclasses import dataclass

from app.config import Settings
from app.services.ai.mindrouter_provider import MindRouterProvider
from app.services.ai.provider import LLMProvider

logger = logging.getLogger(__name__)

CONFIDENCE_LEVELS = ("low", "medium", "high")
_MAX_RATIONALE_LENGTH = 300
_MAX_DESCRIPTION_CHARS = 4000


@dataclass
class NeedSuggestion:
    """One suggested operational need for one event."""

    need: str
    confidence: str
    rationale: str


def build_ops_classifier_provider(config: Settings) -> MindRouterProvider:
    """Construct the classifier's dedicated MindRouter provider."""
    return MindRouterProvider(
        endpoint_url=config.ops_classifier_endpoint_url
        or config.mindrouter_endpoint_url,
        api_key=config.ops_classifier_api_key or config.mindrouter_api_key,
        model=config.ops_classifier_model,
    )


def _system_prompt(need_codes: list[str]) -> str:
    codes = ", ".join(need_codes)
    return (
        "You review University of Idaho public event listings for the Event "
        "Services team, who provide catering, alcohol service, room setup, "
        "tabling, and outdoor-space support. Identify which operational "
        "services this event will plausibly require, using ONLY evidence in "
        "the listing's own text.\n\n"
        f"Allowed need codes: {codes}\n"
        'Confidence levels: "high" (the text states or strongly implies the '
        'service), "medium" (a reasonable inference from the event type or '
        'venue), "low" (a weak hint worth a human glance).\n\n'
        "Respond with JSON of this exact shape:\n"
        '{"needs": [{"need": "<code>", "confidence": "<level>", '
        '"rationale": "<one short sentence quoting or citing the signal>"}]}\n\n'
        "List each need at most once. If the listing gives no evidence of any "
        'operational need, respond {"needs": []}. Do not invent needs for '
        "ordinary lectures, deadlines, or online-only events."
    )


def _user_prompt(
    title: str,
    description: str,
    location: str | None,
    category_path: str | None,
) -> str:
    return (
        f"Title: {title}\n"
        f"Location: {location or '(none given)'}\n"
        f"Category: {category_path or '(none given)'}\n"
        f"Description: {description[:_MAX_DESCRIPTION_CHARS] or '(none given)'}"
    )


def _parse_suggestions(payload: dict, need_codes: list[str]) -> list[NeedSuggestion]:
    """Validate the model's JSON into suggestions. Raises ValueError."""
    if not isinstance(payload, dict) or not isinstance(payload.get("needs"), list):
        raise ValueError("Classifier response is missing a 'needs' list")

    allowed = set(need_codes)
    suggestions: dict[str, NeedSuggestion] = {}
    for item in payload["needs"]:
        if not isinstance(item, dict):
            raise ValueError("Classifier response contains a non-object need")
        need = item.get("need")
        confidence = item.get("confidence")
        rationale = item.get("rationale")
        if not isinstance(need, str) or not isinstance(rationale, str):
            raise ValueError("Classifier need entries must have need and rationale")
        if need not in allowed:
            # Vocabulary drift is a prompt problem, not a harvest problem:
            # drop the unknown code but leave a trace in the logs.
            logger.warning("Ops classifier suggested unknown need %r; dropped", need)
            continue
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"Classifier confidence {confidence!r} is not a level")
        suggestions[need] = NeedSuggestion(
            need=need,
            confidence=confidence,
            rationale=rationale.strip()[:_MAX_RATIONALE_LENGTH],
        )
    return list(suggestions.values())


async def assess_event(
    provider: LLMProvider,
    *,
    title: str,
    description: str,
    location: str | None,
    category_path: str | None,
    need_codes: list[str],
) -> list[NeedSuggestion]:
    """Classify one event's operational needs against the vocabulary.

    Raises ValueError on malformed model output; propagates httpx errors on
    connectivity failure.
    """
    payload = await provider.complete_json(
        _system_prompt(need_codes),
        _user_prompt(title, description, location, category_path),
        temperature=0.1,
        max_tokens=1000,
    )
    return _parse_suggestions(payload, need_codes)
