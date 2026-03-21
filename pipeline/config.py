from __future__ import annotations

import os

from pipeline.state import PipelineConfig


def load_config(**overrides: object) -> PipelineConfig:
    """Load pipeline configuration from environment variables with overrides."""
    config: PipelineConfig = {
        "llm_provider": os.environ.get("GARFIELD_LLM_PROVIDER", "openai"),
        "llm_model": os.environ.get("GARFIELD_LLM_MODEL", "gpt-4o"),
        "spec_mode": os.environ.get("GARFIELD_SPEC_MODE", "multi"),
        "require_review": os.environ.get("GARFIELD_REQUIRE_REVIEW", "false").lower() == "true",
        "specs_dir": os.environ.get("GARFIELD_SPECS_DIR", "specs"),
    }
    for key, value in overrides.items():
        if key in config and value is not None:
            config[key] = value  # type: ignore[literal-required]
    return config
