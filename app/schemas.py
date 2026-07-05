# Copyright (c) 2026 MyCompany LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    id: str
    profile_id: str
    source_type: str
    source_id: str
    date: str
    source: str
    text: str
    tags: List[str]
    emotion: List[str]
    privacy_level: str
    send_to_gemini_allowed: bool = True


class MemoryEvent(BaseModel):
    event_id: str
    type: str
    created_at: str
    profile_id: str
    source_type: str
    source_id: str
    text: str
    tags: List[str]
    privacy_level: str
    deleted: bool = False
    send_to_gemini_allowed: bool = True
    
    # Optional fields for reflection memories
    original_belief: Optional[str] = None
    detected_biases: Optional[List[str]] = None
    selected_evidence_ids: Optional[List[str]] = None
    reframe: Optional[str] = None
    next_action: Optional[str] = None


class ImportedDocument(BaseModel):
    document_id: str
    filename: str
    file_type: str
    imported_at: str
    profile_id: str
    privacy_level: str
    status: str
    chunks_created: int = 0
    chunks_sent_to_gemini: int = 0
    send_to_gemini_allowed: bool = True


class EvidenceCard(BaseModel):
    evidence_id: str
    profile_id: str
    source_type: str
    source_id: str
    date: str
    event: str
    skills: List[str]
    emotions: List[str]
    supports: List[str]
    contradicts: List[str]
    citation: str
    privacy_level: str
    redacted: bool = True
    send_to_gemini_allowed: bool = True
    display_detail_allowed: bool = True
    needs_review: bool = False
    extraction_method: str = "local_regex"
    confidence: float = 0.75


class BeliefInput(BaseModel):
    query_id: str
    created_at: str
    profile_id: str
    raw_text: str
    domain: Optional[str] = None
    intensity: Optional[int] = None


class PrivacyResult(BaseModel):
    allowed: bool
    route: str
    redacted_text: str
    detected_items: List[str]
    reason: str


class SafetyResult(BaseModel):
    risk_level: str
    route: str
    normal_reflection_allowed: bool
    reason: str


class BiasResult(BaseModel):
    biases: List[str]
    core_belief: str
    reason: str


class RerankResult(BaseModel):
    selected_evidence_ids: List[str]
    reason: str
    cbt_reframe_plan: Dict


class EvidenceCheckItem(BaseModel):
    """A single evidence check item in the structured reflection."""
    citation_number: int
    evidence_id: str
    summary: str
    why_it_matters: str


class StructuredReflection(BaseModel):
    """Parsed structured JSON response from Gemini for the reflection section."""
    what_i_am_hearing: str = ""
    possible_thinking_pattern: str = ""
    evidence_check: List[EvidenceCheckItem] = Field(default_factory=list)
    balanced_thought: str = ""
    small_next_step: str = ""
    raw_text: str = ""          # original Gemini output, preserved for fallback
    parse_ok: bool = True


class ReflectionResponse(BaseModel):
    text: str
    evidence_ids: List[str]
    save_allowed: bool
    gemini_calls: int
    structured: Optional[StructuredReflection] = None


# ==========================================
# Legacy schemas for backward compatibility
# ==========================================

class Distortion(BaseModel):
    id: str
    name: str
    confidence: float
    justification: str


class Thought(BaseModel):
    id: str
    raw_text: str
    redacted_text: Optional[str] = None
    detected_distortions: List[Distortion] = Field(default_factory=list)


class Belief(BaseModel):
    id: str
    statement: str
    strength: float = 50.0
    associated_thoughts: List[str] = Field(default_factory=list)


class EvidenceDard(BaseModel):
    evidence_id: str
    profile_id: str
    source_type: str
    source_id: str
    event: str
    skills: List[str] = Field(default_factory=list)
    privacy_level: str



