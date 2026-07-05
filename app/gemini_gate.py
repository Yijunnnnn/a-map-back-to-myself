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
from typing import Tuple, List, Dict, Any, Optional
from dotenv import load_dotenv

from app.gemini_client import GeminiClient
from app.privacy import PrivacyEngine
from app.safety import SafetyGate
from app.output_guard import OutputGuard

load_dotenv()


def can_send_to_gemini(payload: dict) -> Tuple[bool, str]:
    """Evaluates payload criteria to decide if a call can be sent to Gemini."""
    if payload.get("contains_raw_file") is True:
        return False, "Block: Payload contains raw unredacted files."
        
    if payload.get("contains_hidden_memory") is True:
        return False, "Block: Payload contains hidden/private memories."
        
    if payload.get("requests_full_memory_dump") is True:
        return False, "Block: Requesting full memory dump is prohibited."
        
    if payload.get("contains_api_key_or_secret") is True:
        return False, "Block: Payload contains API keys or secrets."
        
    if payload.get("contains_sensitive_data") is True and payload.get("explicit_consent") is not True:
        return False, "Block: Payload contains sensitive data without explicit user consent."
        
    if payload.get("route") == "crisis_response":
        return False, "Block: Gemini call blocked due to safety gate crisis response route."
        
    if payload.get("route") == "privacy_block":
        return False, "Block: Gemini call blocked due to privacy redaction block route."
        
    return True, "Allowed"


def log_gemini_decision(
    call_type: str,
    allowed: bool,
    reason: str,
    evidence_ids: Optional[List[str]] = None
) -> None:
    """Logs the gate decision directly to privacy_events.jsonl."""
    profile_id = os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    log_path = f"data/profiles/{profile_id}/privacy_events.jsonl" if profile_id else "data/privacy_events.jsonl"
    
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "call_type": call_type,
            "allowed": allowed,
            "reason": reason,
            "evidence_ids": evidence_ids or []
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


class GeminiGate:
    """Combines Privacy, Safety, and Output verification around Gemini Client calls."""

    def __init__(self, client: GeminiClient):
        self.client = client
        self.privacy = PrivacyEngine()
        self.safety = SafetyGate()
        self.output_guard = OutputGuard()

    def process_query(self, raw_input: str) -> Tuple[bool, str, List[Dict]]:
        """Processes raw user input safely using safety, privacy, and decision logging."""
        # 1. Safety Check
        is_unsafe, safety_msg = self.safety.check_safety(raw_input)
        
        # Build evaluation payload
        payload = {
            "contains_raw_file": False,
            "contains_hidden_memory": False,
            "requests_full_memory_dump": False,
            "contains_api_key_or_secret": False,
            "contains_sensitive_data": False,
            "explicit_consent": True,
            "route": "crisis_response" if is_unsafe else "evidence_reflection"
        }
        
        # Simple string heuristics for API keys/secrets check
        if "api_key" in raw_input.lower() or "secret" in raw_input.lower():
            payload["contains_api_key_or_secret"] = True
            
        allowed, reason = can_send_to_gemini(payload)
        log_gemini_decision("distortion_analysis", allowed, reason)
        
        if not allowed:
            return False, f"Gate blocked call: {reason}", []

        # 2. Privacy Redaction
        redacted_input, _ = self.privacy.redact_pii(raw_input)

        # 3. Model Generation
        response = self.client.generate_content(redacted_input)

        # 4. Output validation
        is_valid, error, parsed = self.output_guard.validate_cbt_output(response)
        if not is_valid:
            return False, f"Output validation failed: {error}. Raw: {response}", []

        return True, response, parsed
