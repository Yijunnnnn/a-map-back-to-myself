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

import re
import json
import os
from datetime import datetime
from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()


def redact_sensitive_text(text: str) -> str:
    """Scrubs sensitive PII text from user-provided inputs."""
    engine = PrivacyEngine()
    redacted, _ = engine.redact_pii(text)
    return redacted


class PrivacyEngine:
    """Detects and redacts PII like names, phone numbers, and email addresses."""

    def __init__(self, log_path: Optional[str] = None):
        if log_path is None:
            profile_id = os.getenv("ACTIVE_PROFILE_ID")
            if profile_id:
                self.log_path = f"data/profiles/{profile_id}/privacy_events.jsonl"
            else:
                self.log_path = "data/privacy_events.jsonl"
        else:
            self.log_path = log_path


    def redact_pii(self, text: str) -> Tuple[str, bool]:
        """Redacts phone numbers, emails, and names from text.

        Returns:
            (redacted_text, is_redacted)
        """
        redacted = text
        is_redacted = False

        # Email Regex
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        if re.search(email_pattern, redacted):
            redacted = re.sub(email_pattern, "[EMAIL_REDACTED]", redacted)
            is_redacted = True

        # Phone Regex
        phone_pattern = r'\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b'
        if re.search(phone_pattern, redacted):
            redacted = re.sub(phone_pattern, "[PHONE_REDACTED]", redacted)
            is_redacted = True

        if is_redacted:
            self._log_privacy_event(text, redacted)

        return redacted, is_redacted

    def _log_privacy_event(self, original: str, redacted: str):
        """Append privacy logs."""
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "original_length": len(original),
            "redacted_length": len(redacted),
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
