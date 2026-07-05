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
from typing import List, Dict, Optional
from dotenv import load_dotenv
import networkx as nx
from networkx.readwrite import json_graph

from app.schemas import EvidenceCard

load_dotenv()


def build_personal_graph(evidence_cards: List[EvidenceCard]) -> Dict:
    """Constructs a Directed Graph (DiGraph) representing the personal belief network."""
    G = nx.DiGraph()
    
    for card in evidence_cards:
        p_id = card.profile_id
        
        # 1. Evidence Node
        if not G.has_node(card.evidence_id):
            G.add_node(card.evidence_id, type="Evidence", label=card.event, profile_id=p_id)
            
        # 2. Profile Node
        if p_id:
            if not G.has_node(p_id):
                G.add_node(p_id, type="Profile", label=p_id, profile_id=p_id)
            G.add_edge(card.evidence_id, p_id, type="BELONGS_TO_PROFILE", profile_id=p_id)
            
        # 3. Date Node
        if card.date:
            if not G.has_node(card.date):
                G.add_node(card.date, type="Date", label=card.date, profile_id=p_id)
            G.add_edge(card.evidence_id, card.date, type="HAPPENED_ON", profile_id=p_id)
            
        # 4. Source Node
        if card.source_id:
            if not G.has_node(card.source_id):
                G.add_node(card.source_id, type="Source", label=card.citation or card.source_id, profile_id=p_id)
            G.add_edge(card.evidence_id, card.source_id, type="FROM_SOURCE", profile_id=p_id)
            
        # 5. Emotion Nodes
        if card.emotions:
            for emo in card.emotions:
                if not G.has_node(emo):
                    G.add_node(emo, type="Emotion", label=emo, profile_id=p_id)
                G.add_edge(card.evidence_id, emo, type="HAS_EMOTION", profile_id=p_id)
                
        # 6. Skill Nodes
        if card.skills:
            for skill in card.skills:
                if not G.has_node(skill):
                    G.add_node(skill, type="Skill", label=skill, profile_id=p_id)
                G.add_edge(card.evidence_id, skill, type="SUPPORTS", profile_id=p_id)
                
        # 7. Belief Nodes (Supports)
        if card.supports:
            for belief in card.supports:
                if not G.has_node(belief):
                    G.add_node(belief, type="Belief", label=belief, profile_id=p_id)
                G.add_edge(card.evidence_id, belief, type="SUPPORTS", profile_id=p_id)
                
        # 8. Belief Nodes (Contradicts)
        if card.contradicts:
            for belief in card.contradicts:
                if not G.has_node(belief):
                    G.add_node(belief, type="Belief", label=belief, profile_id=p_id)
                G.add_edge(card.evidence_id, belief, type="CONTRADICTS", profile_id=p_id)
                
    output_path = "derived/personal_graph.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generate node-link representation
    graph_data = json_graph.node_link_data(G)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
        
    return graph_data


class GraphBuilder:
    """Legacy class wrapper to support GraphBuilder calls."""

    def __init__(self, output_path: Optional[str] = None):
        self.output_path = output_path or "derived/personal_graph.json"

    def update_graph(self, beliefs: List[Dict], evidence_cards: List[Dict]) -> Dict:
        cards = []
        for c in evidence_cards:
            if isinstance(c, dict):
                cards.append(EvidenceCard(
                    evidence_id=c.get("evidence_id") or c.get("id") or "ev_unknown",
                    profile_id=c.get("profile_id") or "demo_user",
                    source_type=c.get("source_type") or "unknown",
                    source_id=c.get("source_id") or c.get("thought_id") or "unknown",
                    date=c.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                    event=c.get("event") or c.get("justification") or "",
                    skills=c.get("skills") or [],
                    emotions=c.get("emotions") or [],
                    supports=c.get("supports") or ([c.get("belief_id")] if c.get("relationship_type") == "support" else []),
                    contradicts=c.get("contradicts") or ([c.get("belief_id")] if c.get("relationship_type") == "contradict" else []),
                    citation=c.get("citation") or "legacy",
                    privacy_level=c.get("privacy_level") or "public_demo",
                    redacted=c.get("redacted", True),
                    send_to_gemini_allowed=c.get("send_to_gemini_allowed", True),
                    confidence=c.get("confidence", 0.75)
                ))
            else:
                cards.append(c)

        graph_data = build_personal_graph(cards)
        
        if self.output_path != "derived/personal_graph.json":
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2)
                
        return graph_data
