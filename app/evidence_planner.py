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

from typing import List, Dict, Union, Any
from app.schemas import BiasResult


def plan_evidence_search(belief_text: str, bias_result: Any) -> Dict[str, Any]:
    """Generates a search plan dictionary with target goals to retrieve evidence for a belief."""
    biases = []
    if bias_result:
        if isinstance(bias_result, dict):
            biases = bias_result.get("biases", [])
        elif hasattr(bias_result, "biases"):
            biases = bias_result.biases
        elif isinstance(bias_result, list):
            biases = bias_result

    search_goals = []

    # 1. Overgeneralization
    if "overgeneralization" in biases:
        search_goals.extend([
            "find counterexamples",
            "find completed actions",
            "find learning progress",
            "find recovery from mistakes"
        ])

    # 2. Negativity Bias
    if "negativity_bias" in biases:
        search_goals.extend([
            "find positive feedback",
            "find small wins",
            "find long-term progress"
        ])

    # 3. "I don't know my strengths"
    lower_belief = belief_text.lower()
    if "strength" in lower_belief or "don't know my strengths" in lower_belief:
        search_goals.extend([
            "find repeated skills",
            "find feedback",
            "find completed projects"
        ])

    # Default fallback goals if none were matched
    if not search_goals:
        search_goals.extend([
            "find general experiences",
            "find related memories"
        ])

    # De-duplicate while preserving insertion order
    unique_goals = list(dict.fromkeys(search_goals))

    return {
        "belief_text": belief_text,
        "biases": biases,
        "search_goals": unique_goals
    }


class EvidencePlanner:
    """Plans retrieval queries to find supporting or contradicting evidence for a belief."""

    def create_plan(self, belief_statement: str) -> List[Dict[str, Any]]:
        """Generates list of search tasks/queries to fetch evidence for the belief."""
        from app.cbt_bias_agent import detect_bias
        bias_res = detect_bias(belief_statement)
        plan_dict = plan_evidence_search(belief_statement, bias_res)
        
        plan = []
        for goal in plan_dict["search_goals"]:
            plan.append({
                "query": goal,
                "strategy": "goal_targeted",
                "purpose": f"Search to address goal: {goal}"
            })
        return plan
