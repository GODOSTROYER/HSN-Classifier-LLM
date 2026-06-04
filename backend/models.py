"""
HSN Classifier — Pydantic Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class WorkflowStep(BaseModel):
    step: int
    name: str
    status: StepStatus = StepStatus.PENDING
    detail: str = ""
    progress_pct: float = 0.0
    data: Optional[dict] = None


class ChapterChunk(BaseModel):
    """A single indexed chunk from a chapter file."""
    chunk_id: str
    chapter: int
    heading: str = ""            # e.g. "85.01"
    title: str = ""              # e.g. "Electric motors and generators"
    section: str = ""            # e.g. "XVI"
    chapter_title: str = ""
    text: str = ""               # full text of this chunk
    subheadings: list[str] = []  # e.g. ["8501.10", "8501.20"]
    notes: str = ""              # chapter notes text
    chunk_type: str = "heading"  # "heading", "chapter_notes", "general"
    source_file: str = ""


class RoutingEntry(BaseModel):
    """Keyword-to-chapter routing entry."""
    keywords: list[str]
    chapter_file: str
    heading_range: str = ""


class RerankedCandidate(BaseModel):
    """A candidate chunk after reranking."""
    chunk: ChapterChunk
    bm25_score: float = 0.0
    rerank_score: float = 0.0
    combined_score: float = 0.0


class GRIStep(BaseModel):
    """Result of applying one GRI rule."""
    rule: str        # "GRI 1", "GRI 2(a)", etc.
    applied: bool
    reasoning: str
    headings_remaining: list[str] = []
    resolved: bool = False


class ClassificationResult(BaseModel):
    """Final classification opinion."""
    product_description: str
    hsn_code: str = ""
    hsn_description: str = ""
    confidence: float = 0.0
    confidence_label: str = ""
    gri_steps: list[GRIStep] = []
    chapter: str = ""
    section: str = ""
    subheadings_considered: list[str] = []
    verbatim_quotes: list[str] = []
    cross_references: list[str] = []
    reasoning_summary: str = ""
    alternative_codes: list[dict] = []
    classification_opinion: str = ""


class ClassifyRequest(BaseModel):
    product_description: str = Field(..., min_length=3, max_length=2000)
