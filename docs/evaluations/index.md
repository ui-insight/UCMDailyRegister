# AI Model Evaluation

The editorial evaluation checks whether the deployed AI model follows UCM's
editorial decisions (#409, #411). It runs synthetic submissions through the
real editing pipeline, the same path the **AI edit** button uses: prompt,
model call, deterministic clean-up, compliance repair and final flags. Then
it scores each output against what the decision requires.

Tests in CI can't do this. They use a scripted stand-in for the model, so
they prove the code around the model, not the model's behavior.

## What a case looks like

Cases live in `backend/app/evals/editorial_cases.json`. Each one names the
issue and decision it tests, gives a synthetic headline and body, and lists
expectations, for example:

- `contains` / `not_contains`: literal text that must or must not appear
  (curly quotes are straightened first)
- `body_matches` / `body_not_matches`, `headline_matches` /
  `headline_not_matches`: regular expressions
- `flag_matches`: a flag whose rule key or message matches
- `body_unchanged`: clear copy must not be rewritten
- `no_straight_quotes`, `headline_not_echo_lead`

A case marked `pending` tests a rule that isn't built yet. Its result is
shown but left out of the pass rate; when it starts passing, remove the
marker.

Every name, venue and event in the cases is invented. Never copy a real
submission into the file.

## Running it

The model varies from run to run, so each case runs several times (three
by default) and every expectation gets a pass rate.

From a backend container, using the deployed model and the rules in that
environment's database:

```bash
docker exec -w /app ucmnews-dev-backend-1 python -m app.evals.editorial --out /tmp/eval
```

Locally, with model credentials in `backend/.env` and rules from the seed
files:

```bash
cd backend && python -m app.evals.editorial --rules seed
```

Other options: `--repeat N`, `--case <id>` (repeatable), `--concurrency N`.
The report is written as Markdown and JSON to `--out` (default
`eval-results/`, which git ignores).

Run it when the model, the prompt or the editorial rules change, and add
the Markdown report here.

## Results

| Date | Model | Policy | Checks passed | Notes |
| --- | --- | --- | --- | --- |
| [2026-11-06](editorial-2026-11-06.md) | MindRouter `moonshotai/kimi-k3` | 2026-11-04 | 163 of 165 (99%) | Baseline on dev. One miss: a reused acronym lost its definition in 1 of 3 runs. The two #410 date flags are pending. |
