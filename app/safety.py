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
from typing import Tuple, Optional
from dotenv import load_dotenv

from app.schemas import SafetyResult

load_dotenv()


def classify_safety(text: str) -> SafetyResult:
    """Classifies the input text for mental health safety risks."""
    lower_text = text.lower()
    
    crisis_keywords = [
        "i want to hurt myself", "kill myself", "end my life", "suicide", "self-harm",
        "自杀", "伤害自己", "不想活", "活不下去", "结束生命"
    ]
    
    watch_keywords = [
        "worthless", "hopeless", "completely useless", "nobody cares",
        "没有价值", "没救了", "一无是处", "完全没用"
    ]
    
    # 1. Check for crisis
    for kw in crisis_keywords:
        if kw in lower_text:
            return SafetyResult(
                risk_level="crisis",
                route="crisis_response",
                normal_reflection_allowed=False,
                reason=f"Crisis keyword detected: '{kw}'"
            )
            
    # 2. Check for watch
    for kw in watch_keywords:
        if kw in lower_text:
            return SafetyResult(
                risk_level="watch",
                route="supportive_reflection_limited",
                normal_reflection_allowed=True,
                reason=f"Watch keyword detected: '{kw}'"
            )
            
    # 3. Normal / Safe
    return SafetyResult(
        risk_level="normal",
        route="evidence_reflection",
        normal_reflection_allowed=True,
        reason="No safety keywords detected."
    )


class SafetyGate:
    """Interceptors to check for mental health crises and self-harm keywords."""

    CRISIS_RESOURCES = (
        "It sounds like you may be going through a very difficult time. "
        "If you are in distress, please consider reaching out to a professional. "
        "You can connect with the Suicide & Crisis Lifeline by calling or texting 988 (USA/Canada), "
        "or contact local crisis support lines in your area."
    )

    def __init__(self, log_path: Optional[str] = None):
        if log_path is None:
            profile_id = os.getenv("ACTIVE_PROFILE_ID")
            if profile_id:
                self.log_path = f"data/profiles/{profile_id}/safety_events.jsonl"
            else:
                self.log_path = "data/safety_events.jsonl"
        else:
            self.log_path = log_path

    def check_safety(self, text: str) -> Tuple[bool, str]:
        """Check if user input contains self-harm or critical safety issues.

        Returns:
            (is_unsafe, safety_response)
        """
        result = classify_safety(text)
        if result.risk_level == "crisis":
            self._log_safety_event(result.reason)
            return True, self.CRISIS_RESOURCES
        return False, ""

    def _log_safety_event(self, triggered_term: str):
        """Append safety logs."""
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "triggered_term": triggered_term,
            "action": "crisis_resources_intercept"
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
