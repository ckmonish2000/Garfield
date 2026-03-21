from __future__ import annotations

from typing import Literal, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    description: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None


class SpecOutput(BaseModel):
    meeting_id: int
    topic: str
    summary: str
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    decisions_made: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_segments: list[int] = Field(default_factory=list)


class CritiqueIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    description: str
    suggestion: str


class Critique(BaseModel):
    overall_quality: Literal["pass", "needs_refinement", "fail"]
    issues: list[CritiqueIssue] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    hallucination_flags: list[str] = Field(default_factory=list)


class TopicCluster(BaseModel):
    title: str
    segment_indices: list[int]
    relevance: Literal["spec_relevant", "context_only"]


class ClassificationResult(BaseModel):
    topics: list[TopicCluster]
    noise_indices: list[int] = Field(default_factory=list)


class SpeakerMap(BaseModel):
    mapping: dict[str, str] = Field(default_factory=dict)


class PipelineConfig(TypedDict, total=False):
    llm_provider: str       # "openai" | "anthropic" | "google"
    llm_model: str          # model name
    spec_mode: str           # "multi" | "single"
    require_review: bool
    specs_dir: str           # output directory for spec files


class PipelineState(TypedDict, total=False):
    meeting_id: int
    raw_segments: list[dict]
    meeting_title: str
    meeting_attendees: list[str]
    speaker_map: dict[str, str]
    classified_topics: list[dict]
    specs: list[dict]
    critique: dict
    refinement_count: int
    review_decision: Optional[str]
    config: PipelineConfig
    error: Optional[str]
