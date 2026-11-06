"""Evaluate the configured AI model against UCM's editorial decisions (#411).

Each synthetic case in ``editorial_cases.json`` is run through the real
editing pipeline (``AIEditor.edit_submission``: prompt, model call,
deterministic clean-up, compliance repair and final flags) several times,
because the model's output varies. Every expectation is scored per run, and
the report gives each one a pass rate.

Usage, from ``backend/`` or inside a backend container::

    python -m app.evals.editorial                 # rules from the database
    python -m app.evals.editorial --rules seed    # rules from data/style_rules
    python -m app.evals.editorial --case curly-quotes --repeat 5

Cases are synthetic. Never add real submissions to the cases file.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from app.services.ai.editor import AIEditor, EditResult
from app.utils.style_checks import detect_headline_echoes_lead, strip_html

CASES_PATH = Path(__file__).with_name("editorial_cases.json")
SEED_DIR = Path(__file__).parents[2] / "data" / "style_rules"
SEED_FILES = {"shared": "shared_rules.json", "tdr": "tdr_rules.json", "myui": "myui_rules.json"}

_STRAIGHTEN = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class Check:
    """One expectation scored against one model output."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseRun:
    case_id: str
    run: int
    checks: list[Check] = field(default_factory=list)
    headline: str = ""
    body: str = ""
    flags: list[str] = field(default_factory=list)
    error: str | None = None


def visible(text: str) -> str:
    """Text a reader sees: tags removed, entities decoded, spaces collapsed."""
    return _SPACES.sub(" ", html.unescape(strip_html(text))).strip()


def straight(text: str) -> str:
    """Visible text with curly quotes straightened, for literal comparisons."""
    return visible(text).translate(_STRAIGHTEN)


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def _each(
    name: str,
    patterns: Iterable[str],
    target: str,
    ok: Callable[[str, str], bool],
) -> list[Check]:
    return [Check(f"{name}: {pattern}", ok(pattern, target)) for pattern in patterns]


def score(case: dict, headline: str, body: str, flags: list[dict]) -> list[Check]:
    """Score one model output against a case's expectations."""
    expect = case["expect"]
    head, text = straight(headline), straight(body)
    both = f"{head}\n{text}"
    # The body may span lines in HTML; keep newlines for the one-line check.
    raw_body = html.unescape(strip_html(body)).translate(_STRAIGHTEN).strip()
    flag_text = [f"{flag.get('rule_key', '')}: {flag.get('message', '')}" for flag in flags]

    def found(pattern: str, target: str) -> bool:
        return re.search(pattern, target) is not None

    checks: list[Check] = []
    checks += _each("contains", expect.get("contains", []), both, lambda p, t: p in t)
    checks += _each("not_contains", expect.get("not_contains", []), both, lambda p, t: p not in t)
    checks += _each("body_matches", expect.get("body_matches", []), raw_body, found)
    checks += _each(
        "body_not_matches",
        expect.get("body_not_matches", []),
        raw_body,
        lambda p, t: not found(p, t),
    )
    checks += _each("headline_matches", expect.get("headline_matches", []), head, found)
    checks += _each(
        "headline_not_matches",
        expect.get("headline_not_matches", []),
        head,
        lambda p, t: not found(p, t),
    )
    for pattern in expect.get("flag_matches", []):
        checks.append(
            Check(
                f"flag_matches: {pattern}",
                any(re.search(pattern, flag) for flag in flag_text),
            )
        )
    if expect.get("body_unchanged"):
        checks.append(
            Check(
                "body_unchanged",
                text == straight(case["body"]),
                "" if text == straight(case["body"]) else text,
            )
        )
    if expect.get("no_straight_quotes"):
        leftover = re.findall(r"[\"']", visible(f"{headline}\n{body}"))
        checks.append(Check("no_straight_quotes", not leftover, "".join(leftover)))
    if expect.get("headline_not_echo_lead"):
        checks.append(
            Check("headline_not_echo_lead", not detect_headline_echoes_lead(headline, body))
        )
    return checks


def build_submission(case: dict):
    """A transient Submission for the pipeline; it is never added to a session."""
    from app.models.submission import Submission, SubmissionLink

    submitted = date.fromisoformat(case["submitted"])
    return Submission(
        Id=f"eval-{case['id']}",
        Category=case["category"],
        Target_Newsletter=case["newsletter"],
        Original_Headline=case["headline"],
        Original_Body=case["body"],
        Submitter_Name="Synthetic Eval",
        Submitter_Email="eval@example.edu",
        Submitter_Notes=case.get("notes"),
        Created_At=datetime(submitted.year, submitted.month, submitted.day, 9, tzinfo=timezone.utc),
        Links=[
            SubmissionLink(Url=link["url"], Anchor_Text=link.get("anchor_text"), Display_Order=i)
            for i, link in enumerate(case.get("links", []))
        ],
    )


def seed_rules(newsletter_type: str) -> list[dict]:
    """Active rules as shipped in the seed files (the database may differ)."""
    rules = []
    for rule_set in ("shared", newsletter_type):
        for rule in json.loads((SEED_DIR / SEED_FILES[rule_set]).read_text(encoding="utf-8")):
            if rule.get("is_active", True):
                rules.append({**rule, "rule_set": rule_set})
    return rules


class SeedRulesEditor(AIEditor):
    """AIEditor that reads rules from the seed files instead of the database."""

    async def load_style_rules(self, session, newsletter_type: str) -> list[dict]:
        return seed_rules(newsletter_type)


async def run_case(editor: AIEditor, session, case: dict, run: int) -> CaseRun:
    result = CaseRun(case_id=case["id"], run=run)
    try:
        edit: EditResult = await editor.edit_submission(
            session, build_submission(case), case["newsletter"]
        )
    except Exception as error:  # noqa: BLE001 — a failed call is a scored outcome
        result.error = f"{type(error).__name__}: {error}"
        return result
    result.headline, result.body = edit.edited_headline, edit.edited_body
    result.flags = [f"{f.get('rule_key', '')}: {f.get('message', '')}" for f in edit.flags]
    result.checks = score(case, edit.edited_headline, edit.edited_body, edit.flags)
    return result


def summarize(cases: list[dict], runs: list[CaseRun]) -> dict:
    """Pass rate per expectation, per case and overall (pending cases apart)."""
    by_case: dict[str, list[CaseRun]] = {}
    for run in runs:
        by_case.setdefault(run.case_id, []).append(run)
    summary = {"cases": [], "checks_passed": 0, "checks_total": 0}
    for case in cases:
        case_runs = by_case.get(case["id"], [])
        rates: dict[str, list[bool]] = {}
        for run in case_runs:
            for check in run.checks:
                rates.setdefault(check.name, []).append(check.passed)
        errors = sum(1 for run in case_runs if run.error)
        checks = [
            {"name": name, "passed": sum(results), "runs": len(case_runs)}
            for name, results in rates.items()
        ]
        all_passed = errors == 0 and all(c["passed"] == c["runs"] for c in checks)
        entry = {
            "id": case["id"],
            "issues": case["issues"],
            "decision": case["decision"],
            "pending": case.get("pending"),
            "errors": errors,
            "all_passed": all_passed,
            "checks": checks,
        }
        summary["cases"].append(entry)
        if not case.get("pending"):
            summary["checks_total"] += sum(c["runs"] for c in checks) + errors
            summary["checks_passed"] += sum(c["passed"] for c in checks)
    return summary


def render_markdown(meta: dict, summary: dict, runs: list[CaseRun]) -> str:
    total, passed = summary["checks_total"], summary["checks_passed"]
    rate = f"{passed / total:.0%}" if total else "n/a"
    lines = [
        "# Editorial model evaluation",
        "",
        f"- Run at: {meta['run_at']}",
        f"- Model: {meta['provider']} / {meta['model']}",
        f"- Rules: {meta['rules']} (policy fingerprint {meta['policy_fingerprint']})",
        f"- Runs per case: {meta['repeat']}",
        f"- Checks passed (excluding pending cases): {passed} of {total} ({rate})",
        "",
        "| Case | Issues | Result | Failing checks |",
        "| --- | --- | --- | --- |",
    ]
    for case in summary["cases"]:
        if case["pending"]:
            result = "pending, now passing" if case["all_passed"] else "pending"
        else:
            result = "pass" if case["all_passed"] else "FAIL"
        failing = [
            f"{c['name']} ({c['passed']}/{c['runs']})"
            for c in case["checks"]
            if c["passed"] < c["runs"]
        ]
        if case["errors"]:
            failing.insert(0, f"model errors ({case['errors']})")
        issues = ", ".join(f"#{n}" for n in case["issues"])
        lines.append(f"| {case['id']} | {issues} | {result} | {'; '.join(failing) or '—'} |")
    lines += ["", "## Outputs of failing runs", ""]
    failing_runs = [r for r in runs if r.error or not all(c.passed for c in r.checks)]
    for run in failing_runs:
        lines += [f"### {run.case_id}, run {run.run}", ""]
        if run.error:
            lines += [f"Error: `{run.error}`", ""]
            continue
        lines += [
            f"**Headline:** {visible(run.headline)}",
            "",
            f"**Body:** {visible(run.body)}",
            "",
            "**Flags:** " + ("; ".join(run.flags) or "none"),
            "",
        ]
    if not failing_runs:
        lines.append("None.")
    return "\n".join(lines) + "\n"


async def evaluate(
    cases: list[dict],
    *,
    repeat: int,
    rules: str,
    concurrency: int,
) -> tuple[dict, list[CaseRun]]:
    from app.config import settings
    from app.services.ai.factory import get_llm_provider
    from app.services.ai.prompts import policy_fingerprint

    llm = get_llm_provider(settings)
    editor_class = SeedRulesEditor if rules == "seed" else AIEditor
    editor = editor_class(llm)
    limit = asyncio.Semaphore(concurrency)

    async def one(case: dict, run: int) -> CaseRun:
        async with limit:
            if rules == "seed":
                return await run_case(editor, None, case, run)
            from app.db.engine import async_session_factory

            async with async_session_factory() as session:
                return await run_case(editor, session, case, run)

    runs = await asyncio.gather(
        *(one(case, run) for case in cases for run in range(1, repeat + 1))
    )
    if rules == "seed":
        fingerprint = policy_fingerprint(seed_rules("tdr"))
    else:
        from app.db.engine import async_session_factory

        async with async_session_factory() as session:
            fingerprint = policy_fingerprint(await editor.load_style_rules(session, "tdr"))
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": llm.__class__.__name__.replace("Provider", "").lower(),
        "model": getattr(llm, "model", "unknown"),
        "rules": rules,
        "policy_fingerprint": f"{fingerprint} (TDR rules)",
        "repeat": repeat,
    }
    return meta, list(runs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repeat", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument("--rules", choices=("db", "seed"), default="db")
    parser.add_argument("--case", action="append", help="run only this case id (repeatable)")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("eval-results"),
        help="directory for the JSON and Markdown reports",
    )
    args = parser.parse_args(argv)

    cases = load_cases()
    if args.case:
        unknown = set(args.case) - {case["id"] for case in cases}
        if unknown:
            parser.error(f"unknown case id(s): {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in args.case]

    meta, runs = asyncio.run(
        evaluate(cases, repeat=args.repeat, rules=args.rules, concurrency=args.concurrency)
    )
    summary = summarize(cases, runs)
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = meta["run_at"].replace(":", "").replace("-", "")[:15]
    report = render_markdown(meta, summary, runs)
    (args.out / f"editorial-eval-{stamp}.md").write_text(report, encoding="utf-8")
    (args.out / f"editorial-eval-{stamp}.json").write_text(
        json.dumps(
            {"meta": meta, "summary": summary, "runs": [asdict(r) for r in runs]},
            indent=2,
        ),
        encoding="utf-8",
    )
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
