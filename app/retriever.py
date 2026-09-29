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
import re
import logging
import math
from app.semantic_retriever import semantic_scores
from typing import List, Dict, Any, Optional
from app.schemas import EvidenceCard, EvidenceDard


# Ignore grammatical words so shared pronouns do not count as evidence.
_STOP_WORDS = frozenset("""
a an the i me my myself we us our you your he she it they them their
am is are was were be been being do does did have has had
can cannot cant could would should will shall may might must
not no never always nothing anything everything something
to of in on at for from with by as and or but if that this these those
so very really feel feels feeling
ich mich mir mein meine wir uns unser du dich dir dein deine
er sie es ihr ihnen der die das ein eine einer einen einem eines
und oder aber dass wenn weil zu von mit auf im in am an für als
bin bist ist sind war waren sein habe hat haben kann können nicht nie
""".split())


def _relevance_terms(text: str) -> set[str]:
    """Conservative lexical terms; not a semantic or cross-language matcher."""
    text = text.casefold().replace("’", "'")
    terms = set()
    for word in re.findall(r"[^\W_]+", text, flags=re.UNICODE):
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            # Overlapping bigrams support unspaced Chinese without a dependency.
            terms.update(word[i:i + 2] for i in range(len(word) - 1))
        elif len(word) > 1 and word not in _STOP_WORDS:
            terms.add(word)
    return terms


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

    # 2. Rank by topical overlap only, without positivity/source bonuses.
    # Returning no evidence is preferable to filling top_k with unrelated cards.
    query_terms = _relevance_terms(belief_text)
    if not query_terms or top_k <= 0:
        return []
    texts = [" ".join([card.event, *card.supports, *card.contradicts, *card.skills])
             for card in filtered_cards]
    similarities = None
    threshold = 0.55
    if os.getenv("SELFMAP_RETRIEVAL_MODE", "lexical").lower() == "hybrid" and texts:
        try:
            threshold = float(os.getenv("SELFMAP_SEMANTIC_THRESHOLD", "0.55"))
            if not math.isfinite(threshold) or not 0 < threshold <= 1:
                raise ValueError("Invalid threshold")
            similarities = semantic_scores(belief_text, texts)
            if len(similarities) != len(texts) or not all(
                math.isfinite(value) and -1 <= value <= 1 for value in similarities
            ):
                raise ValueError("Invalid similarity scores")
        except Exception:
            # Never include exception details: they may contain personal text.
            logging.getLogger(__name__).warning(
                "Local semantic retrieval unavailable; using lexical retrieval.")
            similarities = None
    ranked_cards = []
    for index, card in enumerate(filtered_cards):
        overlap = len(query_terms & _relevance_terms(texts[index]))
        lexical = overlap / len(query_terms)
        similarity = similarities[index] if similarities is not None else None
        if similarity is not None:
            # Require semantic relevance even when an incidental word matches.
            if similarity < threshold:
                continue
            score = 0.85 * similarity + 0.15 * lexical
        else:
            if not overlap:
                continue
            score = lexical
        ranked_cards.append((score, card))

    ranked_cards.sort(key=lambda item: item[0], reverse=True)
    return [card for _, card in ranked_cards[:top_k]]



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


