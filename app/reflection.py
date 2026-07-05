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
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from app.gemini_client import GeminiClient
from app.prompt_builder import PromptBuilder
from app.schemas import ReflectionResponse

load_dotenv()


def local_crisis_response() -> str:
    """Returns a safe local crisis support message without calling Gemini."""
    return (
        "It sounds like you may be going through a very difficult time. "
        "If you are in distress, please consider reaching out to a professional. "
        "You can connect with the Suicide & Crisis Lifeline by calling or texting 988 (USA/Canada), "
        "or contact local crisis support lines in your area."
    )


def local_watch_response() -> str:
    """Returns a limited supportive response without calling Gemini."""
    return (
        "It is completely understandable to feel overwhelmed or discouraged at times. "
        "Please remember that your feelings are valid, and it can help to take a gentle step back. "
        "We are here to support you in exploring your experiences, one moment at a time."
    )


def _parse_structured_reflection(response_text: str, evidence_map: dict) -> "StructuredReflection":
    """Try to parse a structured JSON reflection from Gemini output.

    Validates that:
    - max evidence items = 4
    - every evidence_id exists and is not fake
    - no duplicate evidence_id
    - sensitive evidence is abstract only

    Returns a StructuredReflection with parse_ok=False on failure.
    """
    from app.schemas import StructuredReflection, EvidenceCheckItem

    # Strip markdown fences if Gemini wrapped output anyway
    clean = response_text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:] if lines[0].startswith("```") else lines)
        clean = clean.rstrip("`").strip()

    try:
        data = json.loads(clean)
        evidence_check_raw = data.get("evidence_check", [])
        
        evidence_check = []
        seen_ids = set()
        
        for item in evidence_check_raw:
            if len(evidence_check) >= 4:
                break
                
            eid = item.get("evidence_id", "")
            if eid and (eid in evidence_map) and (eid not in seen_ids):
                seen_ids.add(eid)
                
                # Check privacy level of this card
                card = evidence_map[eid]
                privacy = getattr(card, "privacy_level", "") or card.get("privacy_level", "")
                
                summary = item.get("summary", "")
                why_it_matters = item.get("why_it_matters", "")
                
                # Force abstract only for sensitive items
                if privacy == "sensitive":
                    summary = f"[Protected] An evening reflection was recorded"
                    why_it_matters = "This experience is kept private for user security."
                
                evidence_check.append(
                    EvidenceCheckItem(
                        citation_number=item.get("citation_number") or len(evidence_check) + 1,
                        evidence_id=eid,
                        summary=summary,
                        why_it_matters=why_it_matters
                    )
                )

        return StructuredReflection(
            what_i_am_hearing=data.get("what_i_am_hearing", ""),
            possible_thinking_pattern=data.get("possible_thinking_pattern", ""),
            evidence_check=evidence_check,
            balanced_thought=data.get("balanced_thought", ""),
            small_next_step=data.get("small_next_step", ""),
            raw_text=response_text,
            parse_ok=True
        )
    except Exception:
        from app.schemas import StructuredReflection
        return StructuredReflection(
            what_i_am_hearing="",
            possible_thinking_pattern="",
            evidence_check=[],
            balanced_thought="",
            small_next_step="",
            raw_text=response_text,
            parse_ok=False
        )


def generate_final_reflection(
    belief: str,
    bias_result: Any,
    selected_evidence: List[Any],
    reframe_plan: Any
) -> ReflectionResponse:
    """Generates the final CBT reframe reflection using Gemini Call 3."""
    from app.prompt_builder import build_reflection_prompt
    from app.gemini_client import call_gemini_text

    # Extract selected evidence IDs
    evidence_ids = []
    for c in selected_evidence:
        if isinstance(c, dict):
            evidence_ids.append(c.get("evidence_id") or c.get("id") or "unknown")
        else:
            evidence_ids.append(getattr(c, "evidence_id", None) or getattr(c, "id", "unknown"))

    biases = []
    if isinstance(bias_result, dict):
        biases = bias_result.get("biases", [])
    elif hasattr(bias_result, "biases"):
        biases = bias_result.biases

    # 1. Safety Checks (Crisis route must never call Gemini)
    if "crisis" in biases or (isinstance(reframe_plan, dict) and reframe_plan.get("route") == "crisis_response"):
        return ReflectionResponse(
            text=local_crisis_response(),
            evidence_ids=evidence_ids,
            save_allowed=False,
            gemini_calls=0,
            structured=None
        )

    # 2. Privacy Checks (Privacy block route must never call Gemini)
    if isinstance(reframe_plan, dict) and reframe_plan.get("route") == "privacy_block":
        return ReflectionResponse(
            text="Reflection generation blocked due to privacy restrictions.",
            evidence_ids=evidence_ids,
            save_allowed=False,
            gemini_calls=0,
            structured=None
        )

    prompt = build_reflection_prompt(belief, bias_result, selected_evidence, reframe_plan)

    try:
        response_text = call_gemini_text(prompt, "reflection_generation")
        gemini_calls = 1
    except Exception as e:
        response_text = f"Error during reflection generation: {e}"
        gemini_calls = 0

    # Parse structured JSON; validate citations against real evidence IDs
    evidence_map = {}
    for c in selected_evidence:
        eid = c.get("evidence_id") if isinstance(c, dict) else getattr(c, "evidence_id", None)
        if not eid:
            eid = c.get("id") if isinstance(c, dict) else getattr(c, "id", "unknown")
        evidence_map[eid] = c

    structured = _parse_structured_reflection(response_text, evidence_map)

    # Build a readable plain-text fallback from structured data
    if structured.parse_ok and structured.what_i_am_hearing:
        plain_parts = []
        if structured.what_i_am_hearing:
            plain_parts.append(f"**What I'm hearing:** {structured.what_i_am_hearing}")
        if structured.possible_thinking_pattern:
            plain_parts.append(f"**Possible thinking pattern:** {structured.possible_thinking_pattern}")
        if structured.evidence_check:
            ev_list = []
            for item in structured.evidence_check:
                ev_list.append(f"[{item.citation_number}] {item.summary} — {item.why_it_matters}")
            plain_parts.append("**Evidence check:**\n" + "\n".join(ev_list))
        if structured.balanced_thought:
            plain_parts.append(f"**A more balanced thought:** {structured.balanced_thought}")
        if structured.small_next_step:
            plain_parts.append(f"**One small next step:** {structured.small_next_step}")
        plain_text = "\n\n".join(plain_parts)
        
        # Keep only the cited evidence IDs in ReflectionResponse metadata
        evidence_ids = [item.evidence_id for item in structured.evidence_check]
    else:
        plain_text = response_text

    return ReflectionResponse(
        text=plain_text,
        evidence_ids=evidence_ids,
        save_allowed=True,
        gemini_calls=gemini_calls,
        structured=structured
    )


class ReflectionEngine:
    """Legacy class wrapper to support daily or triggered reconciliation loops."""

    def __init__(self, client: GeminiClient, log_path: Optional[str] = None):
        self.client = client
        if log_path is None:
            profile_id = os.getenv("ACTIVE_PROFILE_ID")
            if profile_id:
                self.log_path = f"data/profiles/{profile_id}/reflection_events.jsonl"
            else:
                self.log_path = "data/reflection_events.jsonl"
        else:
            self.log_path = log_path

    def run_reconciliation(self, beliefs: List[Dict], evidence_cards: List[Dict], thoughts: List[Dict]) -> List[Dict]:
        reconciliations = []
        thought_map = {t["id"]: t for t in thoughts}

        for card in evidence_cards:
            if card.get("relationship_type") == "contradict" or card.get("contradicts"):
                belief = next((b for b in beliefs if b["id"] == card.get("belief_id") or b["id"] == card.get("evidence_id")), None)
                thought = thought_map.get(card.get("thought_id") or card.get("source_id"))
                
                if belief and thought:
                    prompt = PromptBuilder.build_reflection_prompt(
                        belief["statement"], 
                        thought.get("raw_text", "")
                    )
                    proposal = self.client.generate_content(prompt)
                    
                    reconciliation = {
                        "belief_id": belief["id"],
                        "thought_id": thought["id"],
                        "original_belief": belief["statement"],
                        "contradiction": thought.get("raw_text"),
                        "proposed_reconciliation": proposal
                    }
                    reconciliations.append(reconciliation)
                    self._log_reflection_event(reconciliation)

        return reconciliations

    def _log_reflection_event(self, event: Dict):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            **event
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
