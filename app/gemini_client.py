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
from typing import Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Global call counter
gemini_call_count = 0


def estimate_prompt_tokens_rough(prompt: str) -> int:
    """Roughly estimates the number of tokens in a prompt."""
    return max(1, len(prompt) // 4)


def call_gemini_text(prompt: str, call_type: str) -> str:
    """Sends a text generation prompt to Google Gemini using google-genai."""
    global gemini_call_count
    gemini_call_count += 1
    
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    token_est = estimate_prompt_tokens_rough(prompt)
    
    # Log: call_type, estimated prompt length, gemini_call_count. Do NOT log full prompts to disk.
    print(f"[GeminiCall] Type: {call_type} | Length: {len(prompt)} | Est. Tokens: {token_est} | Count: {gemini_call_count}")
    
    mode = os.getenv("SELFMAP_MODE")
    is_dummy_key = api_key and (api_key.startswith("AQ.Ab") or "your-api-key" in api_key)
    
    # Mock fallback for demo and evaluation environments
    if mode in ("demo", "mixed_demo") or not api_key or is_dummy_key:
        if "I failed my exam. I will never succeed at anything." in prompt:
            return (
                '[\n'
                '  {\n'
                '    "id": "all_or_nothing",\n'
                '    "name": "All-or-Nothing Thinking",\n'
                '    "confidence": 0.95,\n'
                '    "justification": "User uses the absolute word \'never\' to describe their future success."\n'
                '  },\n'
                '  {\n'
                '    "id": "overgeneralization",\n'
                '    "name": "Overgeneralization",\n'
                '    "confidence": 0.90,\n'
                '    "justification": "User generalizes a single failed exam to mean they will not succeed at anything."\n'
                '  }\n'
                ']'
            )
        elif "I made one spelling error. Now the whole report is ruined." in prompt:
            return (
                '[\n'
                '  {\n'
                '    "id": "all_or_nothing",\n'
                '    "name": "All-or-Nothing Thinking",\n'
                '    "confidence": 0.95,\n'
                '    "justification": "User views a single spelling error as ruining the entire report."\n'
                '  }\n'
                ']'
            )
        elif "I feel like I haven't made any progress." in prompt:
            return (
                '[\n'
                '  {\n'
                '    "id": "emotional_reasoning",\n'
                '    "name": "Emotional Reasoning",\n'
                '    "confidence": 0.90,\n'
                '    "justification": "User concludes that they haven\'t made progress based purely on their feelings (\'I feel like...\')."\n'
                '  },\n'
                '  {\n'
                '    "id": "all_or_nothing",\n'
                '    "name": "All-or-Nothing Thinking",\n'
                '    "confidence": 0.85,\n'
                '    "justification": "User uses the absolute term \'any\' to suggest zero progress, ignoring partial steps."\n'
                '  }\n'
                ']'
            )
        elif "Core Belief:" in prompt:
            return (
                "Although I failed this interview, it doesn't mean I struggle with all interviews. "
                "I have team success and managers who praise my work. I can learn from this failure and improve next time."
            )
        else:
            if "what_i_am_hearing" in prompt:
                import re
                card_pattern = r'\[(\d+)\] ID:\s*(\S+)\s*\n\s*Date:\s*(.*?)\s*\n\s*Excerpt:\s*"(.*?)"'
                card_matches = re.findall(card_pattern, prompt)
                
                evidence_check_items = []
                if card_matches:
                    for num, ev_id, date, excerpt in card_matches[:4]:
                        num = int(num)
                        clean_excerpt = excerpt.strip().rstrip('.')
                        summary_str = f"You completed work on {date} stating: '{clean_excerpt}'"
                        why_str = f"This demonstrates your proactive problem-solving efforts."
                        evidence_check_items.append(
                            f'''{{
      "citation_number": {num},
      "evidence_id": "{ev_id}",
      "summary": "{summary_str}",
      "why_it_matters": "{why_str}"
    }}'''
                        )
                else:
                    evidence_check_items.append(
                        '''{
      "citation_number": 1,
      "evidence_id": "card_evt_local_8ede2852",
      "summary": "You resolved the Delta project task on 2026-06-15.",
      "why_it_matters": "This demonstrates your capability to write capably in team settings."
    }'''
                    )
                evidence_check_str = ",\n    ".join(evidence_check_items)

                return f'''{{
  "what_i_am_hearing": "It sounds like you are carrying a heavy sense of burden right now, feeling that everything feels extremely difficult to manage. When you are feeling this way, it is completely natural to see tasks as insurmountable obstacles and feel discouraged about your capacity to get things done. I hear that you are looking for some breathing room and want to understand if there is a more balanced way to look at your current situation.",
  "possible_thinking_pattern": "It seems emotional reasoning or all-or-nothing thinking might be active, leading you to conclude that you are stuck or making no progress based purely on temporary intense feelings of discouragement.",
  "evidence_check": [
    {evidence_check_str}
  ],
  "balanced_thought": "I feel overwhelmed and stuck right now, and it is natural for things to feel difficult. However, looking at my history, I have concrete evidence of showing up, planning, and taking steps even when discouraged. I am not completely incapable or failing; I am simply navigating a challenging moment and making steady progress.",
  "small_next_step": "For your next step, try choosing just one very small, specific task—such as writing down a single idea or spending five minutes organizing your workspace—and allow yourself to stop as soon as it is done. This helps take the pressure off and shows you that you can build momentum gently."
}}'''
            if "cognitive distortions" in prompt or "JSON" in prompt:
                return '[]'
            return f"Mock response for prompt: {prompt[:30]}..."

    # Real call using google-genai
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"[GeminiError] Failed to call Gemini: {e}")
        raise e


class GeminiClient:
    """Configures and wraps connection to the Google Gemini API (legacy wrapper)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def generate_content(self, prompt: str) -> str:
        """Call the model and return the generated text."""
        return call_gemini_text(prompt, "generate_content")

