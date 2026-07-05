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
import re
from typing import Tuple, List, Dict, Any

# Safe fallback message
SAFE_FALLBACK_TEXT = (
    "I want to make sure I support you safely. I cannot provide a detailed reflection "
    "on this right now, but please know that your thoughts are important. If you need immediate "
    "support, please consider contacting a professional or a helpline like 988."
)


def validate_output(
    response_text: str,
    selected_evidence: List[Any],
    safety_result: Any
) -> Tuple[bool, str]:
    """Validates the response text for safety compliance, privacy leaks, and correctness.
    
    Returns:
        (is_valid, sanitized_or_fallback_text)
    """
    lower_response = response_text.lower()

    # 1. No nonexistent evidence IDs (only check prose text, skip structured JSON bodies)
    valid_ids = set()
    for c in selected_evidence:
        if isinstance(c, dict):
            valid_ids.add(c.get("evidence_id") or c.get("id"))
        else:
            valid_ids.add(getattr(c, "evidence_id", None) or getattr(c, "id", None))
    valid_ids.discard(None)

    # Only run the hallucination check when the response is plain prose (not JSON).
    # Structured JSON responses legitimately echo evidence IDs from our own prompt, so
    # checking them would produce false positives and return SAFE_FALLBACK_TEXT.
    response_stripped = response_text.strip()
    is_json_response = response_stripped.startswith("{") or response_stripped.startswith("[")
    if not is_json_response:
        found_ids = re.findall(r'\b(?:card|ev(?:_local)?|doc)_\w+\b', response_text)
        for f_id in found_ids:
            if f_id not in valid_ids:
                return False, SAFE_FALLBACK_TEXT

    # 2. No hidden evidence leak
    for c in selected_evidence:
        p_level = c.get("privacy_level") if isinstance(c, dict) else getattr(c, "privacy_level", None)
        if p_level == "hidden":
            ev_id = c.get("evidence_id") or c.get("id") if isinstance(c, dict) else getattr(c, "evidence_id", None) or getattr(c, "id", None)
            if ev_id and ev_id in response_text:
                return False, SAFE_FALLBACK_TEXT
            ev_event = c.get("event") if isinstance(c, dict) else getattr(c, "event", "")
            if ev_event and ev_event in response_text:
                return False, SAFE_FALLBACK_TEXT

    # 3. No email / phone / API key-like strings
    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', response_text):
        return False, SAFE_FALLBACK_TEXT
    if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', response_text):
        return False, SAFE_FALLBACK_TEXT
    if re.search(r'\b(?:AIzaSy[A-Za-z0-9_-]{33})\b', response_text):
        return False, SAFE_FALLBACK_TEXT

    # 4. No diagnosis language
    diag_terms = ["you have depression", "you are clinically", "diagnosis"]
    for term in diag_terms:
        if term in lower_response:
            return False, SAFE_FALLBACK_TEXT

    # 5. No full memory dump
    dump_terms = ["full memory dump", "all memories", "memory dump"]
    for term in dump_terms:
        if term in lower_response:
            return False, SAFE_FALLBACK_TEXT

    # 6. No SelfBook if safety risk is crisis
    is_crisis = False
    if safety_result:
        if isinstance(safety_result, dict):
            is_crisis = safety_result.get("risk_level") == "crisis"
        elif hasattr(safety_result, "risk_level"):
            is_crisis = safety_result.risk_level == "crisis"

    if is_crisis and "selfbook" in lower_response:
        return False, SAFE_FALLBACK_TEXT

    return True, response_text


class OutputGuard:
    """Validates model responses for syntax consistency and clinical policy compliance."""

    def __init__(self):
        self.prohibited_diagnostic_terms = [
            "depression", "major depressive disorder", "mdd",
            "generalized anxiety disorder", "gad", "obsessive compulsive disorder", "ocd",
            "ptsd", "bipolar", "schizophrenia", "personality disorder"
        ]

    def validate_cbt_output(self, response_text: str) -> Tuple[bool, str, List[Dict]]:
        lower_response = response_text.lower()
        for term in self.prohibited_diagnostic_terms:
            if term in lower_response:
                return False, f"Violation: Response contains prohibited diagnostic term: '{term}'", []

        try:
            parsed = json.loads(response_text)
            if not isinstance(parsed, list):
                return False, "Violation: Output is not a JSON list", []
            return True, "", parsed
        except Exception as e:
            return False, f"Violation: Failed to parse JSON: {str(e)}", []

