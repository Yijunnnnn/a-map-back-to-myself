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

from typing import List
from app.schemas import BiasResult, Distortion, Thought


def detect_bias(text: str) -> BiasResult:
    """Detects cognitive distortions/biases in the input text without calling Gemini."""
    lower_text = text.lower()
    biases = []
    reasons = []

    # 1. Overgeneralization
    overgen_kws = ["always", "never", "every time", "at all", "completely", "一直", "从来", "每次", "永远", "完全"]
    for kw in overgen_kws:
        if kw in lower_text:
            biases.append("overgeneralization")
            reasons.append(f"Detected overgeneralization keyword: '{kw}'")
            break

    # 2. Negativity Bias
    neg_kws = ["no progress", "failed", "useless", "not good enough", "没有进步", "没有成长", "失败", "没用"]
    for kw in neg_kws:
        if kw in lower_text:
            biases.append("negativity_bias")
            reasons.append(f"Detected negativity bias keyword: '{kw}'")
            break

    # 3. Catastrophizing
    cat_kws = ["ruined", "hopeless", "over", "disaster", "完了", "毁了", "没救了"]
    for kw in cat_kws:
        if kw in lower_text:
            biases.append("catastrophizing")
            reasons.append(f"Detected catastrophizing keyword: '{kw}'")
            break

    # 4. Impostor-like Thought
    impostor_kws = ["fraud", "luck", "don't deserve", "骗子", "运气", "不配"]
    for kw in impostor_kws:
        if kw in lower_text:
            biases.append("impostor_like_thought")
            reasons.append(f"Detected impostor-like thought keyword: '{kw}'")
            break

    # 5. Emotional Reasoning
    if "i feel" in lower_text or "感觉" in lower_text or "觉得" in lower_text or "feel" in lower_text:
        biases.append("emotional_reasoning")
        reasons.append("Detected emotional reasoning phrase / feeling expression.")

    # 6. Extract simple core_belief
    core = text.strip()
    core = core.rstrip(".!?。！？")
    lower_core = core.lower()
    
    prefixes = ["i feel like ", "i feel ", "i felt like ", "i felt ", "i think ", "感觉我", "觉得我", "感觉", "觉得"]
    for prefix in prefixes:
        if lower_core.startswith(prefix):
            core = core[len(prefix):]
            lower_core = core.lower()
            
    replacements = {
        "haven't": "have not",
        "don't": "do not",
        "didn't": "did not",
        "can't": "cannot",
        "won't": "will not",
        "isn't": "is not",
        "aren't": "are not",
        "any ": "",
    }
    for old, new in replacements.items():
        core = core.replace(old, new)
        core = core.replace(old.capitalize(), new.capitalize())
        
    core_belief = " ".join(core.split())

    reason = "; ".join(reasons) if reasons else "No cognitive distortions detected."
    
    return BiasResult(
        biases=biases,
        core_belief=core_belief,
        reason=reason
    )


class CBTBiasAgent:
    """Identifies cognitive distortions/biases in thoughts using CBT models."""

    def __init__(self, client=None):
        self.client = client

    def analyze_thought(self, thought: Thought) -> List[Distortion]:
        bias_res = detect_bias(thought.raw_text)
        distortions = []
        name_map = {
            "overgeneralization": "Overgeneralization",
            "negativity_bias": "Negativity Bias",
            "catastrophizing": "Catastrophizing",
            "impostor_like_thought": "Impostor-like Thought",
            "emotional_reasoning": "Emotional Reasoning"
        }
        for b in bias_res.biases:
            distortions.append(Distortion(
                id=b,
                name=name_map.get(b, b.capitalize()),
                confidence=0.9,
                justification=bias_res.reason
            ))
        return distortions
