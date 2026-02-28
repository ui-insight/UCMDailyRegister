"""MindRouter LLM provider — calls the University of Idaho's on-prem AI
services platform via its OpenAI-compatible chat-completions endpoint.

MindRouter (mindrouter.uidaho.edu) hosts institutional AI models including
Qwen3-32B for text generation and dots.OCR for document processing.  The API
follows the OpenAI chat-completions contract so a thin httpx wrapper is all
that's needed.

Some models (Qwen3 in particular) emit ``<think>…</think>`` reasoning blocks
before their answer.  These are stripped before the content is returned.
"""

import json
import logging
import re

import httpx

from app.services.ai.provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

LLM_TIMEOUT = 120  # seconds — matches AuditDashboard convention


class MindRouterProvider(LLMProvider):
    def __init__(
        self,
        endpoint_url: str,
        api_key: str = "",
        model: str = "Qwen/Qwen3-32B",
    ):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _strip_think_blocks(text: str) -> str:
        """Remove Qwen3-style ``<think>…</think>`` reasoning blocks."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences that models sometimes wrap around JSON."""
        text = text.strip()
        if text.startswith("```"):
            first_newline = text.index("\n") if "\n" in text else 3
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            logger.info(
                "MindRouter request to %s (model=%s, %d+%d chars)",
                self.endpoint_url,
                self.model,
                len(system_prompt),
                len(user_prompt),
            )
            response = await client.post(
                self.endpoint_url,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

        result = response.json()
        raw_content = result["choices"][0]["message"]["content"]
        content = self._strip_think_blocks(raw_content)

        # Extract usage if the endpoint provides it
        usage_data = result.get("usage", {})
        usage = {
            "input_tokens": usage_data.get("prompt_tokens", 0),
            "output_tokens": usage_data.get("completion_tokens", 0),
        }

        return LLMResponse(
            content=content,
            model=self.model,
            provider="mindrouter",
            usage=usage,
        )

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict:
        json_system = (
            system_prompt
            + "\n\nYou MUST respond with valid JSON only. "
            "No markdown, no code fences, no explanation outside the JSON."
        )
        response = await self.complete(json_system, user_prompt, temperature, max_tokens)
        text = self._strip_code_fences(response.content)
        return json.loads(text)
