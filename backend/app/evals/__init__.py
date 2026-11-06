"""On-demand evaluations that call the configured AI model.

These are not part of the pytest suite or CI: they spend model calls and
their results vary from run to run. Run them from a backend container (or a
local environment with model credentials) when the model, the prompt or the
editorial rules change, and keep the report as evidence (#411).
"""
