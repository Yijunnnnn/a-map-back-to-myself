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

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

from app.schemas import MemoryEntry, EvidenceCard

load_dotenv()


def map_tags_to_evidence(tags: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Maps tags to skills, supports, and contradicts fields based on rules."""
    skills = []
    supports = []
    contradicts = []
    
    tags_lower = [t.lower() for t in tags]
    
    # 1. Map to skills & supports
    if "communication" in tags_lower:
        skills.append("communication")
        supports.append("I communicate well")
        
    if "learning" in tags_lower or "ai_learning" in tags_lower:
        skills.append("learning")
        supports.append("I am capable of learning and growing")
        
    if "system_thinking" in tags_lower:
        skills.append("system_thinking")
        supports.append("I can analyze systems effectively")
        
    if "product_design" in tags_lower or "product_thinking" in tags_lower:
        skills.append("product_thinking")
        supports.append("I have strong product thinking")
        
    if "privacy" in tags_lower or "safety" in tags_lower:
        skills.append("agent_governance")
        supports.append("I adhere to privacy and safety guidelines")
        
    if "persistence" in tags_lower or "recovery" in tags_lower or "resilience" in tags_lower:
        skills.append("resilience")
        supports.append("I can recover from failure and persist")
        
    if "feedback" in tags_lower:
        skills.append("feedback_integration")
        supports.append("I integrate feedback well")

    # 2. Map to contradicts
    contradicts_group_1 = {"progress", "learning", "project_log", "product_design", "system_thinking"}
    if any(t in contradicts_group_1 for t in tags_lower):
        contradicts.append("I have not made progress")
        contradicts.append("I have not grown at all")
        
    if "communication" in tags_lower:
        contradicts.append("I never communicate well")
        
    if "persistence" in tags_lower or "recovery" in tags_lower or "resilience" in tags_lower:
        contradicts.append("I always fail when I try something new")
        
    return skills, supports, contradicts


def build_evidence_cards(memories: List[MemoryEntry], include_hidden: bool = False) -> List[EvidenceCard]:
    """Converts MemoryEntry objects into EvidenceCard objects and saves them to derived/evidence_cards.json."""
    cards = []
    for mem in memories:
        if mem.privacy_level == "hidden" and not include_hidden:
            continue
            
        skills, supports, contradicts = map_tags_to_evidence(mem.tags)
        
        is_sensitive = mem.privacy_level == "sensitive"
        confidence = 0.3 if is_sensitive else 0.75
        display_detail_allowed = not is_sensitive
        needs_review = is_sensitive
        extraction_method = "local_sensitive_template" if is_sensitive else "local_regex"

        card = EvidenceCard(
            evidence_id=f"card_{mem.id}",
            profile_id=mem.profile_id,
            source_type=mem.source_type,
            source_id=mem.source_id,
            date=mem.date,
            event=mem.text,
            skills=skills,
            emotions=mem.emotion,
            supports=supports,
            contradicts=contradicts,
            citation=f"Source: {mem.source}",
            privacy_level=mem.privacy_level,
            redacted=True,
            send_to_gemini_allowed=mem.send_to_gemini_allowed,
            display_detail_allowed=display_detail_allowed,
            needs_review=needs_review,
            extraction_method=extraction_method,
            confidence=confidence
        )
        cards.append(card)
        
    output_path = "derived/evidence_cards.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    serialized = [c.model_dump() for c in cards]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2)
        
    return cards


class EvidenceBuilder:
    """Evaluates links between thoughts and beliefs to generate Evidence Cards."""

    def __init__(self, output_path: Optional[str] = None):
        if output_path is None:
            profile_id = os.getenv("ACTIVE_PROFILE_ID")
            if profile_id:
                self.output_path = f"derived/profiles/{profile_id}/evidence_cards.json"
            else:
                self.output_path = "derived/evidence_cards.json"
        else:
            self.output_path = output_path

    def build_evidence_cards(self, memories, beliefs=None, include_hidden: bool = False) -> List[EvidenceCard]:
        if beliefs is not None:
            cards = []
            for t in memories:
                if isinstance(t, dict):
                    p_id = t.get("profile_id") or os.getenv("ACTIVE_PROFILE_ID", "default_user")
                    s_type = t.get("source_type") or "user_event"
                    s_id = t.get("source_id") or t.get("id")
                    t_id = t.get("id")
                    t_text = t.get("raw_text", t.get("content", "")).lower()
                else:
                    p_id = getattr(t, "profile_id", None) or os.getenv("ACTIVE_PROFILE_ID", "default_user")
                    s_type = getattr(t, "source_type", None) or "user_event"
                    s_id = getattr(t, "source_id", None) or getattr(t, "id", None)
                    t_id = getattr(t, "id", None)
                    t_text = (getattr(t, "raw_text", None) or getattr(t, "content", "")).lower()

                for b in beliefs:
                    if isinstance(b, dict):
                        b_id = b.get("id")
                        b_text = b.get("statement", "").lower()
                    else:
                        b_id = getattr(b, "id", None)
                        b_text = getattr(b, "statement", "").lower()
                    
                    if any(word in t_text for word in b_text.split()):
                        rel = "support"
                        if "never" in t_text or "fail" in t_text:
                            rel = "contradict"
                            
                        card = EvidenceCard(
                            evidence_id=f"card_{t_id}_{b_id}",
                            profile_id=p_id,
                            source_type=s_type,
                            source_id=s_id,
                            date=datetime.utcnow().strftime("%Y-%m-%d"),
                            event=t_text,
                            skills=[],
                            emotions=[],
                            supports=[b_text] if rel == "support" else [],
                            contradicts=[b_text] if rel == "contradict" else [],
                            citation="legacy",
                            privacy_level="public_demo",
                            redacted=True,
                            send_to_gemini_allowed=True,
                            confidence=0.8
                        )
                        cards.append(card)
            self._save_cards(cards)
            return cards

        cards = build_evidence_cards(memories, include_hidden=include_hidden)
        self._save_cards(cards)
        return cards

    def _save_cards(self, cards: List[EvidenceCard]):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        serialized = [c.model_dump() for c in cards]
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
