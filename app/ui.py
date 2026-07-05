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
import re
import json
import html as html_mod
import tempfile
import sys
import uuid

import importlib

# Ensure parent directory is in sys.path so 'app' and 'eval' can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Force reload local modules if they are already in memory to avoid Streamlit caching/hot-reload import errors
if "app.schemas" in sys.modules:
    importlib.reload(sys.modules["app.schemas"])
if "app.memory_store" in sys.modules:
    importlib.reload(sys.modules["app.memory_store"])
if "app.evidence_builder" in sys.modules:
    importlib.reload(sys.modules["app.evidence_builder"])
if "app.retriever" in sys.modules:
    importlib.reload(sys.modules["app.retriever"])
if "app.safety" in sys.modules:
    importlib.reload(sys.modules["app.safety"])
if "app.cbt_bias_agent" in sys.modules:
    importlib.reload(sys.modules["app.cbt_bias_agent"])
if "app.gemini_client" in sys.modules:
    importlib.reload(sys.modules["app.gemini_client"])
if "app.output_guard" in sys.modules:
    importlib.reload(sys.modules["app.output_guard"])
# Reload prompt_builder and reflection AFTER schemas and gemini_client so they pick up the updated
# ReflectionResponse class and updated client helpers.
if "app.prompt_builder" in sys.modules:
    importlib.reload(sys.modules["app.prompt_builder"])
if "app.reflection" in sys.modules:
    importlib.reload(sys.modules["app.reflection"])

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Ensure app modules can be loaded
from app.memory_store import (
    load_active_memories,
    append_memory_event,
    append_reflection_memory_event,
    append_belief_query,
    append_reflection_event,
    load_imported_documents,
    update_memory_event_privacy,
    update_imported_document_privacy,
    load_memory_events
)
from app.evidence_builder import build_evidence_cards
from app.graph_builder import build_personal_graph
from app.safety import classify_safety
from app.cbt_bias_agent import detect_bias
from app.retriever import retrieve_candidate_evidence
from app.prompt_builder import build_reranker_prompt
from app.gemini_client import call_gemini_text
from app.gemini_gate import can_send_to_gemini, log_gemini_decision
from app.reflection import generate_final_reflection, local_crisis_response, local_watch_response
from app.output_guard import validate_output
from app.document_importer import import_file
from eval.eval_runner import run_eval

load_dotenv()

# Streamlit Page Settings
st.set_page_config(
    page_title="SelfMap - Cognitive Companion",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Centered container with exactly 1/6 (16.67%) whitespace on each side */
    .main .block-container, [data-testid="stAppViewBlockContainer"], .block-container, div.block-container {
        max-width: 100% !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    @media (min-width: 768px) {
        .main .block-container, [data-testid="stAppViewBlockContainer"], .block-container, div.block-container {
            padding-left: 16.67% !important;
            padding-right: 16.67% !important;
        }
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #000000;
        margin-bottom: 2rem;
    }
    
    /* Separate the last tab (EvaluationSuite) and push it to the far right */
    div[data-testid="stTabs"] button:last-child {
        margin-left: auto !important;
        border: 1px solid rgba(0, 0, 0, 0.2);
        border-radius: 4px;
        background-color: rgba(0, 0, 0, 0.05);
    }
    
    /* Style unselected tab buttons */
    div[data-testid="stTabs"] button[aria-selected="false"] {
        font-size: 0.8rem !important;
        transition: font-size 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stTabs"] button[aria-selected="false"] * {
        font-size: 0.8rem !important;
    }
    
    /* Style selected tab button (3 times larger font size than unselected) */
    div[data-testid="stTabs"] button[aria-selected="true"] {
        font-size: 2.4rem !important;
        font-weight: 700 !important;
        color: #000000 !important;
        transition: font-size 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stTabs"] button[aria-selected="true"] * {
        font-size: 2.4rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header Area
st.markdown("<div class='main-title'>A Map Back to Myself</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>When self-doubt feels true, let your evidence speak.</div>", unsafe_allow_html=True)

# App Mode Selection
# Check if there is any imported documents or memories in the private profile (default_user)
has_private_data = False
private_docs_path = "data/profiles/default_user/imported_documents.jsonl"
private_mems_path = "data/profiles/default_user/memory_events.jsonl"

if os.path.exists(private_docs_path):
    with open(private_docs_path, "r", encoding="utf-8") as f:
        if any(line.strip() for line in f):
            has_private_data = True
if not has_private_data and os.path.exists(private_mems_path):
    with open(private_mems_path, "r", encoding="utf-8") as f:
        if any(line.strip() for line in f):
            has_private_data = True

if "selfmap_mode_selection" not in st.session_state:
    st.session_state.selfmap_mode_selection = "Private Mode" if has_private_data else "Demo Mode"

mode_option = st.radio(
    "Active Mode",
    ["Private Mode", "Demo Mode"],
    key="selfmap_mode_selection",
    horizontal=True,
    help="Private Mode: Uses your personal isolated data only. Demo Mode: Loads synthetic pre-configured memories."
)

if mode_option == "Demo Mode":
    resolved_mode = "demo"
    resolved_profile_id = "demo_user"
    use_demo_seed = True
else:
    resolved_mode = "user"
    env_profile = os.getenv("ACTIVE_PROFILE_ID", "default_user")
    resolved_profile_id = "default_user" if env_profile == "demo_user" else env_profile
    use_demo_seed = False

allow_user_events = os.getenv("ALLOW_USER_EVENTS", "true").lower() in ("true", "1")

# Sidebar Configuration Stats
st.sidebar.markdown("### ⚙️ SelfMap Config")
st.sidebar.markdown(f"**Execution Mode:** `{resolved_mode}`")
st.sidebar.markdown(f"**Active Profile:** `{resolved_profile_id}`")
st.sidebar.markdown(f"**Seed Memories Active:** `{'Yes' if use_demo_seed else 'No'}`")
st.sidebar.markdown(f"**Allow Memory Events:** `{'Yes' if allow_user_events else 'No'}`")

# Info Banner
if resolved_mode == "demo":
    st.info("💡 **Demo Seed memories are active.** The system loaded pre-configured memories for simulation purposes.")
else:
    st.success("🔒 **Private mode active.** The system runs entirely on personal data isolated for your profile.")

# Main Navigation Tabs
tab_examine, tab_import, tab_add, tab_browse, tab_eval = st.tabs([
    "🔍 I feel ...",
    "📥 Import File",
    "➕ Add memory",
    "📂 Browse Memories",
    "📊 EvaluationSuite"
])

# ---------------------------------------------------------
# Tab 1: I feel ...
# ---------------------------------------------------------
with tab_examine:
    st.header("I feel ...")
    st.write("*Write one thought about yourself that feels true right now. SelfMap will gently check it against your own evidence.*")

    belief_input = st.text_input(
        "Belief / Automatic Thought",
        placeholder="e.g., I will never pass my exams.",
        help="""Please tell me how you feel right now.

Examples:
- I feel like I haven't made any progress.
- I don't know what my strengths are.
- I feel proud of how I handled the presentation.
- I feel anxious about starting this new project.

This is not a place to upload a full diary or private document. Use Import File for longer texts. Please do not enter passwords, API keys, addresses, or other highly sensitive personal data here."""
    )
    
    # Render previous success message if any
    if st.session_state.get("save_reflection_success"):
        st.success(f"✅ Reflection successfully saved to your memory!\n\n**Saved Memory Event Summary:**\n\"{st.session_state.get('last_saved_memory_text')}\"")
        # Clear success state so it doesn't linger forever
        st.session_state.save_reflection_success = False

    # Button to execute
    if st.button("Examine with evidence"):
        if belief_input.strip():
            # Clear old pending state
            st.session_state.show_save_reflection_ui = False
            st.session_state.pending_belief = None
            st.session_state.pending_reflection = None
            st.session_state.pending_selected_evidence = None
            st.session_state.pending_biases = None
            st.session_state.pending_query_id = None
            st.session_state.pending_reflection_id = None

            with st.spinner("Examining your thought against your evidence..."):
                # 1. Run privacy precheck
                contains_raw = False
                lower_belief = belief_input.lower()
                if "seed" in lower_belief and any(act in lower_belief for act in ["edit", "write", "modify", "change", "update", "save"]):
                    contains_raw = True

                payload = {
                    "contains_raw_file": contains_raw,
                    "contains_hidden_memory": False,
                    "requests_full_memory_dump": ("full memory dump" in lower_belief or "all memories" in lower_belief),
                    "contains_api_key_or_secret": ("api_key" in lower_belief or "secret" in lower_belief),
                    "contains_sensitive_data": False,
                    "explicit_consent": True,
                    "route": "evidence_reflection"
                }
                allowed, reason = can_send_to_gemini(payload)

                if not allowed:
                    log_gemini_decision("reflection_generation", False, reason)
                    st.error(f"🔒 **Privacy Blocked:** {reason}")
                else:
                    # 2. Safety classifier
                    safety_res = classify_safety(belief_input)
                    if safety_res.risk_level == "crisis":
                        st.error("⚠️ **We're here for you**")
                        st.write(local_crisis_response())
                    elif safety_res.risk_level == "watch":
                        st.warning("💙 **A gentle note before we continue**")
                        st.write(local_watch_response())
                    else:
                        # 3. CBT Bias detection (silent — moved to advanced)
                        bias_res = detect_bias(belief_input)

                        # 4. Retrieval
                        candidates = retrieve_candidate_evidence(
                            belief_text=belief_input,
                            bias_result=bias_res,
                            profile_id=resolved_profile_id,
                            mode=resolved_mode,
                            top_k=20
                        )

                        # 5. Rerank → select evidence
                        if candidates:
                            rerank_prompt = build_reranker_prompt(belief_input, bias_res, candidates)
                            try:
                                rerank_response = call_gemini_text(rerank_prompt, "reranker")
                                selected_ids = re.findall(r'\b(?:card|ev|doc)_\w+\b', rerank_response)
                                selected_evidence = [c for c in candidates if c.evidence_id in selected_ids]
                                if not selected_evidence:
                                    selected_evidence = candidates[:10]
                            except Exception:
                                selected_evidence = candidates[:10]
                        else:
                            selected_evidence = []

                        reframe_plan = {"route": "evidence_reflection"}
                        reflection_res = generate_final_reflection(
                            belief=belief_input,
                            bias_result=bias_res,
                            selected_evidence=selected_evidence,
                            reframe_plan=reframe_plan
                        )

                        is_valid, final_text = validate_output(
                            response_text=reflection_res.text,
                            selected_evidence=selected_evidence,
                            safety_result=safety_res
                        )

                        calls_made = 1 + reflection_res.gemini_calls if candidates else reflection_res.gemini_calls

                        # ─────────────────────────────────────────────────────
                        # SECTION 1: What your evidence suggests (reflection)
                        # ─────────────────────────────────────────────────────
                        st.markdown("---")
                        st.markdown("## 🌿 What your evidence suggests")

                        structured = reflection_res.structured

                        def _linkify_citations(text: str) -> str:
                            """Replace [N] with <a href='#evidence-N'>[N]</a>."""
                            return re.sub(
                                r'\[(\d+)\]',
                                lambda m: f'<a href="#evidence-{m.group(1)}" style="color:#000000;font-weight:700;text-decoration:underline;">[{m.group(1)}]</a>',
                                text
                            )

                        if structured and structured.parse_ok and structured.what_i_am_hearing:
                            st.markdown("""
<style>
.reflection-card {
    background: linear-gradient(135deg, rgba(0,0,0,0.01), rgba(0,0,0,0.03));
    border: 1px solid rgba(0,0,0,0.12);
    border-radius: 14px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.2rem;
    width: 100% !important;
    max-width: 100% !important;
}
.reflection-section-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #000000;
    margin-bottom: 0.35rem;
}
.reflection-section-body {
    font-size: 1.05rem;
    line-height: 1.65;
    color: inherit;
    margin-bottom: 0;
}
</style>
""", unsafe_allow_html=True)

                            #🎙️ What I'm hearing
                            hearing_safe = html_mod.escape(structured.what_i_am_hearing)
                            st.markdown(f"""
<div class="reflection-card">
  <div class="reflection-section-title">🎙️ What I&#39;m hearing</div>
  <div class="reflection-section-body">{hearing_safe}</div>
</div>""", unsafe_allow_html=True)

                            #🧠 Possible thinking pattern
                            thinking_safe = html_mod.escape(structured.possible_thinking_pattern)
                            st.markdown(f"""
<div class="reflection-card">
  <div class="reflection-section-title">🧠 Possible thinking pattern</div>
  <div class="reflection-section-body">{thinking_safe}</div>
</div>""", unsafe_allow_html=True)

                            #📄 Evidence check
                            evidence_check_safe = ""
                            if structured.evidence_check:
                                evidence_html_items = []
                                for item in structured.evidence_check:
                                    num = item.citation_number
                                    summary_safe = html_mod.escape(item.summary)
                                    why_safe = html_mod.escape(item.why_it_matters)
                                    evidence_html_items.append(
                                        f'<div class="ev-check-item" style="margin-bottom: 0.8rem; border-left: 3px solid #000000; padding-left: 0.8rem;">'
                                        f'<a href="#evidence-{num}" style="color:#000000;font-weight:700;margin-right:0.5rem;text-decoration:underline;">[{num}]</a> '
                                        f'<strong style="color: inherit;">{summary_safe}</strong>'
                                        f'<div style="font-size: 0.9rem; opacity: 0.85; margin-top: 0.2rem;">{why_safe}</div>'
                                        f'</div>'
                                    )
                                evidence_check_safe = "\n".join(evidence_html_items)

                            st.markdown(f"""
<div class="reflection-card">
  <div class="reflection-section-title">📄 Evidence check</div>
  <div class="reflection-section-body" style="margin-top: 0.5rem;">{evidence_check_safe}</div>
</div>""", unsafe_allow_html=True)

                            #⚖️ A more balanced thought
                            balanced_safe = _linkify_citations(html_mod.escape(structured.balanced_thought))
                            st.markdown(f"""
<div class="reflection-card">
  <div class="reflection-section-title">⚖️ A more balanced thought</div>
  <div class="reflection-section-body">{balanced_safe}</div>
</div>""", unsafe_allow_html=True)

                            #🌱 One small next step
                            next_step_safe = html_mod.escape(structured.small_next_step)
                            st.markdown(f"""
<div class="reflection-card">
  <div class="reflection-section-title">🌱 One small next step</div>
  <div class="reflection-section-body">{next_step_safe}</div>
</div>""", unsafe_allow_html=True)

                        else:
                            # Fallback: if parse failed show raw response; otherwise plain text
                            if structured and structured.raw_text:
                                st.markdown(structured.raw_text)
                            else:
                                st.markdown(final_text)

                        # ─────────────────────────────────────────────────────
                        # SECTION 2: Evidence behind this reflection
                        # ─────────────────────────────────────────────────────
                        st.markdown("---")
                        st.markdown("## 📋 Evidence behind this reflection")

                        # Determine which evidence IDs were actually cited
                        cited_ids = set()
                        if structured and structured.parse_ok and structured.evidence_check:
                            for item in structured.evidence_check:
                                cited_ids.add(item.evidence_id)
                        # Fall back to showing all selected if no citations parsed
                        if not cited_ids:
                            cited_ids = {c.evidence_id for c in selected_evidence}

                        # Build citation number map: evidence_id → number
                        citation_num_map = {}
                        if structured and structured.evidence_check:
                            for item in structured.evidence_check:
                                citation_num_map[item.evidence_id] = item.citation_number

                        # Filter to cited evidence only
                        cited_evidence = [c for c in selected_evidence if c.evidence_id in cited_ids]

                        if not cited_evidence:
                            st.info("No specific evidence was retrieved for this reflection.")
                        else:
                            st.markdown("""
<style>
.evidence-card {
    border: 1px solid rgba(255,75,75,0.18);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    background: rgba(255,255,255,0.02);
    position: relative;
    width: 100% !important;
    max-width: 100% !important;
}
.ev-card-grid {
    display: flex;
    align-items: flex-start;
}
.ev-grid-left {
    flex-shrink: 0;
    width: 2.2rem;
}
.ev-grid-right {
    flex-grow: 1;
}
.ev-citation-badge {
    color: #000000;
    font-weight: 800;
    font-size: 1.15rem;
    margin-top: 0.1rem;
    display: inline-block;
}
.ev-excerpt {
    font-style: italic;
    color: #222222;
    font-size: 0.95rem;
    border-left: 3px solid #000000;
    padding-left: 0.8rem;
    margin: 0 0 0.6rem 0;
}
.ev-why {
    font-size: 0.9rem;
    color: #333333;
    margin-bottom: 0.6rem;
}
.ev-date {
    font-size: 0.78rem;
    color: #555555;
    margin-top: 0.5rem;
}
.ev-sensitive {
    color: #000000;
    font-size: 0.9rem;
    padding: 0.5rem 0.8rem;
    background: rgba(0,0,0,0.05);
    border-radius: 8px;
    margin: 0 0 0.6rem 0;
}
.ev-details {
    margin-top: 0.5rem;
    font-size: 0.85rem;
}
.ev-details-summary {
    cursor: pointer;
    color: #4F46E5;
    font-weight: 500;
    user-select: none;
    margin-bottom: 0.3rem;
}
.ev-details-summary:hover {
    text-decoration: underline;
}
.ev-details-content {
    margin-top: 0.3rem;
    padding: 0.6rem 0.8rem;
    background: #f9fafb;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
    color: #374151;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

                            for c in cited_evidence:
                                ev_id = c.evidence_id
                                ev_num = citation_num_map.get(ev_id, "?")
                                ev_event = getattr(c, "event", "") or ""
                                ev_date = getattr(c, "date", "") or ""
                                ev_skills = getattr(c, "skills", []) or []
                                ev_contradicts = getattr(c, "contradicts", []) or []
                                ev_privacy = getattr(c, "privacy_level", "private")
                                is_sensitive = ev_privacy == "sensitive"

                                # Short event title = first sentence
                                from app.prompt_builder import _safe_excerpt
                                ev_short_title = ev_event.split(".")[0].strip()[:120] if ev_event else "(untitled)"
                                ev_excerpt = _safe_excerpt(ev_event, max_chars=200)

                                # Why this matters = derived from skills/contradicts
                                if ev_contradicts:
                                    why_matters = f"This evidence challenges the belief by showing: {ev_contradicts[0]}"
                                elif ev_skills:
                                    why_matters = f"This demonstrates a strength in: {', '.join(ev_skills[:2])}"
                                else:
                                    why_matters = "This experience is directly relevant to your current thought."

                                if is_sensitive:
                                    card_html = (
                                        f'<div id="evidence-{ev_num}" class="evidence-card">'
                                        f'<div class="ev-card-grid">'
                                        f'<div class="ev-grid-left">'
                                        f'<span class="ev-citation-badge">[{ev_num}]</span>'
                                        f'</div>'
                                        f'<div class="ev-grid-right">'
                                        f'<div class="ev-sensitive">🔒 Details hidden for privacy — this record is marked sensitive and its contents are protected.</div>'
                                        f'<div class="ev-why"><strong>Why this matters:</strong> {why_matters}</div>'
                                        f'<div class="ev-date">📅 {ev_date}</div>'
                                        f'</div>'
                                        f'</div>'
                                        f'</div>'
                                    )
                                else:
                                    card_html = (
                                        f'<div id="evidence-{ev_num}" class="evidence-card">'
                                        f'<div class="ev-card-grid">'
                                        f'<div class="ev-grid-left">'
                                        f'<span class="ev-citation-badge">[{ev_num}]</span>'
                                        f'</div>'
                                        f'<div class="ev-grid-right">'
                                        f'<div class="ev-excerpt">"{ev_excerpt}"</div>'
                                        f'<div class="ev-why"><strong>Why this matters:</strong> {why_matters}</div>'
                                        f'<details class="ev-details">'
                                        f'<summary class="ev-details-summary">View original context</summary>'
                                        f'<div class="ev-details-content">{ev_event}</div>'
                                        f'</details>'
                                        f'<div class="ev-date">📅 {ev_date}</div>'
                                        f'</div>'
                                        f'</div>'
                                        f'</div>'
                                    )
                                
                                st.markdown(card_html, unsafe_allow_html=True)

                        # ─────────────────────────────────────────────────────
                        # SECTION 3: Advanced details (collapsed)
                        # ─────────────────────────────────────────────────────
                        st.markdown("---")
                        with st.expander("⚙️ Advanced details", expanded=False):
                            st.markdown(f"**Safety route:** `{safety_res.route}`")
                            bias_list = bias_res.biases if bias_res.biases else ["none detected"]
                            st.markdown(f"**Detected CBT pattern(s):** {', '.join(bias_list)}")
                            st.markdown(f"**Gemini calls:** `{calls_made}`")
                            st.markdown(f"**Retrieval candidates:** `{len(candidates)}`")
                            st.markdown(f"**Selected evidence IDs:** `{[c.evidence_id for c in selected_evidence]}`")
                            if structured and not structured.parse_ok:
                                st.warning("Structured JSON parse failed — reflection shown as plain text.")
                                st.code(structured.raw_text[:600], language="text")

                        if is_valid and reflection_res.save_allowed:
                            # Generate query_id and reflection_id
                            qid = f"qry_{uuid.uuid4().hex[:8]}"
                            rid = f"ref_{uuid.uuid4().hex[:8]}"

                            # Append to belief_queries.jsonl and reflection_events.jsonl immediately
                            selected_ids_list = [c.evidence_id for c in selected_evidence]
                            append_belief_query(qid, belief_input, resolved_profile_id)
                            append_reflection_event(rid, qid, belief_input, final_text, selected_ids_list, resolved_profile_id)

                            # Store in session state for Save UI
                            st.session_state.pending_belief = belief_input
                            st.session_state.pending_reflection = final_text
                            st.session_state.pending_selected_evidence = selected_evidence
                            st.session_state.pending_biases = bias_res.biases
                            st.session_state.pending_query_id = qid
                            st.session_state.pending_reflection_id = rid
                            st.session_state.show_save_reflection_ui = True
        else:
            st.warning("Please enter a thought or feeling first.")

    # Show Save Reflection UI if available in session state
    if st.session_state.get("show_save_reflection_ui"):
        st.write("---")
        st.subheader("Would you like to save this reflection to your memory?")
        
        # We need two columns for the buttons
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("Save Reflection as Memory", key="btn_save_reflection_action"):
                # Execute save logic
                belief = st.session_state.pending_belief
                ref_text = st.session_state.pending_reflection
                evidence = st.session_state.pending_selected_evidence
                biases = st.session_state.pending_biases
                qid = st.session_state.pending_query_id
                rid = st.session_state.pending_reflection_id
                
                # Build neutral summary text
                unique_skills = []
                for c in evidence:
                    for s in c.skills:
                        if s not in unique_skills:
                            unique_skills.append(s)
                
                if unique_skills:
                    if len(unique_skills) == 1:
                        skills_str = unique_skills[0]
                    elif len(unique_skills) == 2:
                        skills_str = f"{unique_skills[0]} and {unique_skills[1]}"
                    else:
                        skills_str = ", ".join(unique_skills[:-1]) + f", and {unique_skills[-1]}"
                    summary_text = f"I examined a negative self-belief and found evidence of progress in {skills_str}."
                else:
                    summary_text = f"I examined a negative self-belief ('{belief}') and reframed it using candidate evidence."
                
                # Extract selected evidence IDs
                sel_ids = [c.evidence_id for c in evidence]
                
                # Call append helper
                append_reflection_memory_event(
                    text=summary_text,
                    original_belief=belief,
                    detected_biases=biases,
                    selected_evidence_ids=sel_ids,
                    reframe=ref_text,
                    next_action="Review evidence cards to reinforce this positive reframe.",
                    source_id=rid,
                    profile_id=resolved_profile_id
                )
                
                # Rebuild database
                memories = load_active_memories(resolved_mode, resolved_profile_id)
                cards = build_evidence_cards(memories)
                build_personal_graph(cards)
                
                # Update session state to show success on next run
                st.session_state.show_save_reflection_ui = False
                st.session_state.save_reflection_success = True
                st.session_state.last_saved_memory_text = summary_text
                st.rerun()
                
        with sc2:
            if st.button("Not now", key="btn_cancel_reflection_action"):
                st.session_state.show_save_reflection_ui = False
                st.rerun()

# ---------------------------------------------------------
# Tab 2: Import File
# ---------------------------------------------------------
with tab_import:
    st.header("Import Document")
    st.write("*Ingest text documents, MD files, PDFs, or Word files to extract cognitive evidence cards.*")
    
    uploaded_file = st.file_uploader(
        "Upload a file",
        type=["txt", "md", "pdf", "docx"],
        help="Supported formats: PDF, DOCX, TXT, MD. (Max character limit: 10,000)"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        privacy_level = st.radio(
            "Privacy level for this file",
            ["private", "sensitive", "hidden"],
            help="Select the privacy level for the imported file."
        )
    with col2:
        allow_gemini = st.checkbox("Allow extraction via Gemini Call 1", value=True)
        local_only = st.checkbox("Local-only rule extraction fallback", value=False)
        
    st.markdown("""
**Private — use normally, after redaction**  
For ordinary personal notes, learning logs, project reflections, or journals. SelfMap may use this content as evidence after removing names, emails, phone numbers, and other sensitive details.

**Sensitive — use only with extra protection**  
For health notes, mental health reflections, relationship issues, family topics, financial stress, or other highly personal content. Sensitive content is not sent to Gemini or used in normal reflections unless explicitly allowed.

**Hidden — save privately, but do not use in reflections**  
For content the user wants to keep in SelfMap but not analyze. Hidden content is not sent to Gemini, not used for evidence retrieval, and not shown in final reflections.
""")
        
    if st.button("Start Ingest & Process"):
        if uploaded_file is not None:
            with st.spinner("Processing file..."):
                # Save file to temp location
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_path = temp_file.name
                
                try:
                    # Ingest
                    use_gemini_extraction = allow_gemini and not local_only
                    doc_metadata = import_file(
                        path=temp_path,
                        privacy_level=privacy_level,
                        use_gemini=use_gemini_extraction,
                        profile_id=resolved_profile_id
                    )
                    
                    # Rebuild database
                    memories = load_active_memories(resolved_mode, resolved_profile_id)
                    cards = build_evidence_cards(memories)
                    build_personal_graph(cards)
                    
                    # Show results
                    st.success("✅ Document Ingestion Successful!")
                    chunks_created = doc_metadata.get("chunks_created", 0)
                    chunks_sent = doc_metadata.get("chunks_sent_to_gemini", 0)
                    privacy_blocks = chunks_created - chunks_sent if use_gemini_extraction else 0
                    
                    doc_id = doc_metadata.get("document_id")
                    ev_count = len([c for c in cards if c.source_id == doc_id])
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Chunks Created", chunks_created)
                    m2.metric("Chunks Sent to Gemini", chunks_sent)
                    m3.metric("Privacy Blocks", privacy_blocks)
                    m4.metric("Evidence Cards Generated", ev_count)
                except Exception as e:
                    st.error(f"Error importing document: {str(e)}")
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        else:
            st.warning("Please upload a file first.")

    st.markdown("---")
    st.subheader("💡 Demo Corpus Import")
    st.write("Import the pre-configured multi-format Mira Vale demo corpus (30 files) to simulate and explore SelfMap's evidence mapping.")
    
    if st.button("Import Mira Demo Corpus"):
        with st.spinner("Importing Mira Vale demo corpus..."):
            try:
                from app.demo_corpus import import_demo_corpus
                res = import_demo_corpus()
                
                st.success("✅ Mira Vale Demo Corpus Imported Successfully!")
                
                c1, c2, c3 = st.columns(3)
                c1.write(f"📄 **TXT files:** {res['txt_imported']}")
                c1.write(f"📄 **PDF files:** {res['pdf_imported']}")
                c1.write(f"📄 **DOCX files:** {res['docx_imported']}")
                c1.write(f"📄 **Markdown files:** {res['md_imported']}")
                c2.write(f"🔒 **Private records:** {res['private_count']}")
                c2.write(f"⚠️ **Sensitive records:** {res['sensitive_count']}")
                c2.write(f"🚫 **Sensitive records to Gemini:** {res['sensitive_gemini_calls']}")
                c2.write(f"🛡️ **Protected Evidence Cards:** {res['protected_cards_created']}")
                c3.write(f"💭 **Memory events created:** {res['events_created']}")
                c3.write(f"🎴 **Evidence cards generated:** {res['cards_generated']}")
                
                st.info(f"🤖 **Gemini calls made:** {res['gemini_calls']}")
                
                st.rerun()
            except Exception as e:
                st.error(f"Error importing demo corpus: {str(e)}")

# ---------------------------------------------------------
# Tab 3: Add Memory
# ---------------------------------------------------------
with tab_add:
    st.header("Add a factual memory directly")
    st.write("*Use this when you want to record a concrete event, achievement, feedback, or moment without running a CBT reflection first.*")
    
    text_content = st.text_area("Memory Text Log", placeholder="Write down what happened or how you feel...")
    add_privacy = st.radio(
        "Memory Event Privacy Level",
        ["private", "sensitive", "hidden"],
        key="add_mem_privacy_radio"
    )
    
    if st.button("Append Memory Event"):
        if text_content.strip():
            with st.spinner("Checking privacy and writing memory..."):
                # 1. Run privacy precheck
                payload = {
                    "contains_raw_file": False,
                    "contains_hidden_memory": False,
                    "requests_full_memory_dump": False,
                    "contains_api_key_or_secret": ("api_key" in text_content.lower() or "secret" in text_content.lower()),
                    "contains_sensitive_data": False,
                    "explicit_consent": True,
                    "route": "evidence_reflection"
                }
                allowed, reason = can_send_to_gemini(payload)
                
                if not allowed:
                    log_gemini_decision("add_memory", False, reason)
                    st.error(f"❌ Blocked by Privacy Precheck: {reason}")
                else:
                    # 2. Append event
                    evt = append_memory_event(
                        text=text_content,
                        tags=[],
                        privacy_level=add_privacy,
                        profile_id=resolved_profile_id
                    )
                    
                    # 3. Rebuild
                    memories = load_active_memories(resolved_mode, resolved_profile_id)
                    cards = build_evidence_cards(memories)
                    build_personal_graph(cards)
                    
                    st.success("✅ Memory Event successfully written to database!")
                    st.write(f"**Event ID:** `{evt.event_id}`")
                    st.write("Database rebuilt successfully.")
        else:
            st.warning("Please enter some text log content.")

# ---------------------------------------------------------
# Tab 4: Browse Memories
# ---------------------------------------------------------
with tab_browse:
    st.header("📂 Browse Memory Database")
    st.write("*Browse and manage all manually added documents and session memories inside a Notion-style table grid.*")
    
    sub_import, sub_memory = st.tabs(["📥 Imported Files", "💭 Session Memories"])
    
    # 1. Imported Files Tab
    with sub_import:
        docs = load_imported_documents(resolved_mode, resolved_profile_id)
        # Filter by profile
        docs = [d for d in docs if d.profile_id == resolved_profile_id]
        
        if not docs:
            st.info("No imported files found.")
        else:
            # Sorting Controls
            sort_option_doc = st.selectbox(
                "Sort files by:",
                ["Addition Time (Newest First)", "Addition Time (Oldest First)", "Privacy Level"],
                key="sort_docs"
            )
            
            # Apply Sorting
            if sort_option_doc == "Addition Time (Newest First)":
                docs.sort(key=lambda x: x.imported_at, reverse=True)
            elif sort_option_doc == "Addition Time (Oldest First)":
                docs.sort(key=lambda x: x.imported_at)
            else:
                docs.sort(key=lambda x: {"private": 1, "sensitive": 2, "hidden": 3}.get(x.privacy_level, 0))
                
            # Build DataFrame
            df_docs = pd.DataFrame([
                {
                    "ID": doc.document_id,
                    "Filename": doc.filename,
                    "Type": doc.file_type.upper(),
                    "Imported At": doc.imported_at.replace("T", " ")[:19],
                    "Privacy Level": doc.privacy_level,
                    "Allow LLM Access": doc.send_to_gemini_allowed
                } for doc in docs
            ])
            
            # Render Notion-style Table
            edited_docs = st.data_editor(
                df_docs,
                column_config={
                    "ID": None,
                    "Filename": st.column_config.TextColumn("Filename", disabled=True, width="medium"),
                    "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                    "Imported At": st.column_config.TextColumn("Imported At", disabled=True, width="medium"),
                    "Privacy Level": st.column_config.SelectboxColumn(
                        "Privacy Level",
                        options=["private", "sensitive", "hidden"],
                        required=True,
                        width="medium"
                    ),
                    "Allow LLM Access": st.column_config.CheckboxColumn(
                        "Allow LLM Access",
                        width="small"
                    )
                },
                hide_index=True,
                width="stretch",
                key="editor_docs"
            )
            
            # Save Changes Check
            if not edited_docs.equals(df_docs):
                st.warning("⚠️ You have unsaved changes in your document settings.")
                if st.button("💾 Save Document Settings Changes", key="save_docs_btn"):
                    orig_lookup = {row["ID"]: row for _, row in df_docs.iterrows()}
                    for _, row in edited_docs.iterrows():
                        orig_row = orig_lookup.get(row["ID"])
                        if orig_row is not None:
                            if (row["Privacy Level"] != orig_row["Privacy Level"]) or (row["Allow LLM Access"] != orig_row["Allow LLM Access"]):
                                update_imported_document_privacy(
                                    row["ID"], 
                                    row["Privacy Level"], 
                                    row["Allow LLM Access"],
                                    resolved_mode,
                                    resolved_profile_id
                                )
                    st.success("Document settings saved successfully!")
                    st.rerun()
                        
    # 2. Session Memories Tab
    with sub_memory:
        events = load_memory_events(resolved_mode, resolved_profile_id)
        # Filter by profile and manual/reflection_memory types
        events = [e for e in events if e.profile_id == resolved_profile_id and e.type in ["manual", "reflection_memory"]]
        
        if not events:
            st.info("No session memories found.")
        else:
            # Sorting Controls
            sort_option_mem = st.selectbox(
                "Sort memories by:",
                ["Addition Time (Newest First)", "Addition Time (Oldest First)", "Privacy Level"],
                key="sort_events"
            )
            
            # Apply Sorting
            if sort_option_mem == "Addition Time (Newest First)":
                events.sort(key=lambda x: x.created_at, reverse=True)
            elif sort_option_mem == "Addition Time (Oldest First)":
                events.sort(key=lambda x: x.created_at)
            else:
                events.sort(key=lambda x: {"private": 1, "sensitive": 2, "hidden": 3}.get(x.privacy_level, 0))
                
            # Build DataFrame
            df_memories = pd.DataFrame([
                {
                    "ID": evt.event_id,
                    "Type": "Manual Entry" if evt.type == "manual" else "LLM Reframe",
                    "Created At": evt.created_at.replace("T", " ")[:19],
                    "Content": evt.text,
                    "Privacy Level": evt.privacy_level,
                    "Allow LLM Access": evt.send_to_gemini_allowed
                } for evt in events
            ])
            
            # Render Notion-style Table
            edited_memories = st.data_editor(
                df_memories,
                column_config={
                    "ID": None,
                    "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                    "Created At": st.column_config.TextColumn("Created At", disabled=True, width="medium"),
                    "Content": st.column_config.TextColumn("Content", disabled=True, width="large"),
                    "Privacy Level": st.column_config.SelectboxColumn(
                        "Privacy Level",
                        options=["private", "sensitive", "hidden"],
                        required=True,
                        width="medium"
                    ),
                    "Allow LLM Access": st.column_config.CheckboxColumn(
                        "Allow LLM Access",
                        width="small"
                    )
                },
                hide_index=True,
                width="stretch",
                key="editor_memories"
            )
            
            # Save Changes Check
            if not edited_memories.equals(df_memories):
                st.warning("⚠️ You have unsaved changes in your memory settings.")
                if st.button("💾 Save Memory Settings Changes", key="save_mem_btn"):
                    orig_lookup = {row["ID"]: row for _, row in df_memories.iterrows()}
                    for _, row in edited_memories.iterrows():
                        orig_row = orig_lookup.get(row["ID"])
                        if orig_row is not None:
                            if (row["Privacy Level"] != orig_row["Privacy Level"]) or (row["Allow LLM Access"] != orig_row["Allow LLM Access"]):
                                update_memory_event_privacy(
                                    row["ID"],
                                    row["Privacy Level"],
                                    row["Allow LLM Access"],
                                    resolved_mode,
                                    resolved_profile_id
                                )
                    # Rebuild DB after updates
                    memories = load_active_memories(resolved_mode, resolved_profile_id)
                    cards = build_evidence_cards(memories)
                    build_personal_graph(cards)
                    
                    st.success("Memory settings saved successfully and database rebuilt!")
                    st.rerun()

# ---------------------------------------------------------
# Tab 5: Evaluation
# ---------------------------------------------------------
with tab_eval:
    st.header("EvaluationSuite Dashboard")
    st.write("*Run the automated SelfMap Evaluation Suite locally to verify safety, PII redaction, bias detection, and Gemini suppression metrics.*")
    
    with_gemini_eval = st.checkbox("Include LLM (Gemini API calls) in suite execution", value=False)
    
    if st.button("Run Evaluation Suite"):
        with st.spinner("Executing test cases..."):
            try:
                rows = run_eval(with_gemini=with_gemini_eval)
                
                st.success("🎉 Evaluation Suite Executed Successfully!")
                
                # Show key metrics in columns
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(rows[0][0], f"{rows[0][2]}/{rows[0][1]}", rows[0][3])
                c2.metric(rows[1][0], f"{rows[1][2]}/{rows[1][1]}", rows[1][3])
                c3.metric(rows[2][0], f"{rows[2][2]}/{rows[2][1]}", rows[2][3])
                c4.metric(rows[4][0], f"{rows[4][2]}/{rows[4][1]}", rows[4][3])
                
                st.write("---")
                st.write("### 📊 Metrics Summary Table")
                df_eval = pd.DataFrame(rows, columns=["Metric / Check", "Total Cases", "Passed", "Pass Rate"])
                st.table(df_eval)
            except Exception as e:
                st.error(f"Evaluation runner failed: {str(e)}")
