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

import os
import json
from typing import List, Dict, Any, Optional
from app.schemas import EvidenceCard, EvidenceDard

# Helper to load cards
def load_evidence_cards_raw() -> List[EvidenceCard]:
    """Loads all evidence cards raw from derived/evidence_cards.json."""
    path = "derived/evidence_cards.json"
    cards = []
    if not os.path.exists(path):
        return cards
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                cards.append(EvidenceCard(
                    evidence_id=item.get("evidence_id") or item.get("id") or "ev_unknown",
                    profile_id=item.get("profile_id") or "unknown",
                    source_type=item.get("source_type") or "unknown",
                    source_id=item.get("source_id") or item.get("thought_id") or "unknown",
                    date=item.get("date") or "",
                    event=item.get("event") or item.get("justification") or "",
                    skills=item.get("skills") or [],
                    emotions=item.get("emotions") or [],
                    supports=item.get("supports") or [],
                    contradicts=item.get("contradicts") or [],
                    citation=item.get("citation") or "",
                    privacy_level=item.get("privacy_level") or "private",
                    redacted=item.get("redacted", True),
                    send_to_gemini_allowed=item.get("send_to_gemini_allowed", True),
                    confidence=item.get("confidence", 0.75)
                ))
    except Exception:
        pass
    return cards


def retrieve_candidate_evidence(
    belief_text: str,
    bias_result: Any,
    profile_id: str,
    mode: str,
    top_k: int = 10,
    allow_sensitive: bool = False
) -> List[EvidenceCard]:
    """Retrieves and ranks the top_k EvidenceCard objects based on filtering and scoring rules."""
    all_cards = load_evidence_cards_raw()
    filtered_cards = []
    
    # 1. Filtering
    active_profile = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    
    for card in all_cards:
        # Exclude privacy_level == hidden
        if card.privacy_level == "hidden":
            continue
            
        # Exclude sensitive unless explicitly allowed
        if card.privacy_level == "sensitive" and not allow_sensitive:
            continue
            
        # Exclude if LLM access is manually disabled
        if not card.send_to_gemini_allowed:
            continue
            
        # Mode filtering
        if mode == "demo":
            if card.profile_id != "demo_user":
                continue
        elif mode == "user":
            if card.profile_id != active_profile:
                continue
        elif mode == "mixed_demo":
            if card.profile_id not in ("demo_user", active_profile):
                continue
        else:
            if card.profile_id != active_profile:
                continue
                
        filtered_cards.append(card)

    # 2. Ranking
    belief_words = set(belief_text.lower().split())
    ranked_cards = []
    
    for card in filtered_cards:
        score = 0
        
        # Word overlap
        for s in card.supports:
            score += sum(1 for w in belief_words if w in s.lower())
        for c in card.contradicts:
            score += sum(1 for w in belief_words if w in c.lower())
            
        event_lower = card.event.lower()
        score += sum(1 for w in belief_words if w in event_lower)
        
        for sk in card.skills:
            score += sum(1 for w in belief_words if w in sk.lower())

        # Bonus if evidence contradicts negative belief
        is_negative_belief = any(neg in belief_text.lower() for neg in [
            "never", "fail", "not", "no progress", "worthless", "hopeless", "失败", "没进步", "一无是处"
        ])
        if is_negative_belief and card.contradicts:
            score += 5
            
        # Bonus for progress / learning / feedback / persistence
        bonus_skills = {"progress", "learning", "feedback", "persistence", "resilience", "growth"}
        card_text_content = (card.event + " " + " ".join(card.skills)).lower()
        if any(b_skill in card_text_content for b_skill in bonus_skills):
            score += 3

        # Bonus for source_type user_import or manual_input in user mode
        if mode == "user" and card.source_type in ("user_import", "manual_input"):
            score += 2

        ranked_cards.append((score, card))

    ranked_cards.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in ranked_cards[:top_k]]


def retrieve_evidence(belief: str, profile_id: str, mode: str) -> List[EvidenceDard]:
    """Retrieves and ranks evidence cards matching the belief (backward-compatibility wrapper)."""
    from app.cbt_bias_agent import detect_bias
    bias_res = detect_bias(belief)
    candidate_cards = retrieve_candidate_evidence(
        belief_text=belief,
        bias_result=bias_res,
        profile_id=profile_id,
        mode=mode,
        top_k=10
    )
    
    dards = []
    for c in candidate_cards:
        dards.append(EvidenceDard(
            evidence_id=c.evidence_id,
            profile_id=c.profile_id or "unknown",
            source_type=c.source_type or "unknown",
            source_id=c.source_id or "unknown",
            event=c.event,
            skills=c.skills,
            privacy_level=c.privacy_level or "unknown"
        ))
    return dards


class Retriever:
    """Legacy class wrapper to support old search patterns."""

    def __init__(self, memories: List[Dict], documents: List[Dict]):
        self.memories = memories
        self.documents = documents

    def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        results = []
        words = set(query.lower().split())

        for m in self.memories:
            text = m.get("content", "").lower()
            score = sum(1 for w in words if w in text)
            if score > 0:
                results.append({"type": "memory", "score": score, "data": m})

        for doc in self.documents:
            text = doc.get("content", "").lower()
            score = sum(1 for w in words if w in text)
            if score > 0:
                results.append({"type": "document", "score": score, "data": doc})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


