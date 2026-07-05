import os
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict

# Load configuration
load_dotenv()

from app.memory_store import MemoryStore, load_active_memories
from app.retriever import retrieve_evidence, load_evidence_cards
from app.gemini_client import GeminiClient
from app.gemini_gate import GeminiGate
from app.schemas import Thought, Belief, EvidenceDard
from app.document_importer import DocumentImporter
from app.evidence_builder import EvidenceBuilder
from app.graph_builder import GraphBuilder

# Page configuration
st.set_page_config(
    page_title="SelfMap Agent - Cognitive Companion & Belief Map",
    page_icon="🧠",
    layout="wide"
)

# Custom Styling for Premium Aesthetics
st.markdown("""
<style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    .card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)


# 1. Header & Mode Status Bar
st.title("🧠 SelfMap Agent Dashboard")

mode = os.getenv("SELFMAP_MODE", "demo")
if mode == "demo":
    profile_id = "demo_user"
else:
    profile_id = os.getenv("ACTIVE_PROFILE_ID", "default_user")

if mode == "demo":
    st.info("**Current Mode:** Demo Mode  \nUsing synthetic seed memories only.")
elif mode == "user":
    st.success(f"**Current Mode:** User Mode (Profile: `{profile_id}`)  \nUsing imported/manual memories only.")
elif mode == "mixed_demo":
    st.warning(f"**Current Mode:** Mixed Demo Mode (Profile: `{profile_id}`)  \n⚠️ **Notice:** Demo seed memories (`demo_user`) and user memories are currently mixed!")
else:
    st.success(f"**Current Mode:** Mode `{mode}` (Profile: `{profile_id}`)  \nActive in the environment.")


# Sidebar Controls
st.sidebar.title("Configuration & Status")
st.sidebar.markdown(f"**Active Profile:** `{profile_id}`")
st.sidebar.markdown(f"**Use Demo Seed:** `{os.getenv('USE_DEMO_SEED', 'true')}`")

# Active Memories List in Sidebar
st.sidebar.subheader("Active Memory Count")
try:
    active_mems = load_active_memories(mode, profile_id)
    st.sidebar.metric(label="Active Memories Loaded", value=len(active_mems))
except Exception as e:
    st.sidebar.error(f"Error loading memories: {e}")

# Main Tabs
tab1, tab2, tab3 = st.tabs(["💭 CBT Distortion Analyzer", "🔍 Evidence Retriever", "📂 Document Importer"])

with tab1:
    st.header("CBT Distortion Analyzer")
    st.write("Submit an automatic thought to analyze it for cognitive distortions (e.g., all-or-nothing thinking, catastrophizing).")
    
    thought_input = st.text_area(
        "Enter your automatic thought:",
        placeholder="Type something here (e.g., 'I failed my exam. I will never succeed at anything.')",
        height=100
    )
    
    if st.button("Analyze Thought"):
        if not thought_input.strip():
            st.warning("Please enter a valid thought.")
        else:
            with st.spinner("Processing through Gemini Gate..."):
                client = GeminiClient()
                gate = GeminiGate(client)
                
                success, response_text, parsed_json = gate.process_query(thought_input)
                
                if not success:
                    st.error(f"Analysis Intercepted: {response_text}")
                else:
                    st.subheader("Analysis Results")
                    
                    # Original vs Redacted
                    privacy_engine = gate.privacy
                    redacted, is_redacted = privacy_engine.redact_pii(thought_input)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Original Text:**")
                        st.write(thought_input)
                    with col2:
                        st.markdown("**PII Redacted Text:**")
                        st.write(redacted)
                    
                    st.divider()
                    
                    if not parsed_json:
                        st.info("No cognitive distortions identified in this thought.")
                    else:
                        st.write("### Identified Distortions")
                        for dist in parsed_json:
                            with st.container():
                                st.markdown(f"""
                                <div class="card">
                                    <h4>🎯 {dist.get('name', 'Unknown Distortion')}</h4>
                                    <p><b>Confidence:</b> {dist.get('confidence', 1.0)*100:.1f}%</p>
                                    <p><b>Justification:</b> {dist.get('justification', '')}</p>
                                </div>
                                """, unsafe_allow_html=True)

with tab2:
    st.header("Evidence Retriever")
    st.write("Retrieve and rank evidence card records associated with core beliefs.")
    
    belief_input = st.text_input(
        "Enter a Core Belief to query evidence for:",
        placeholder="e.g., 'I failed my exam'"
    )
    
    if st.button("Search Evidence"):
        if not belief_input.strip():
            st.warning("Please enter a core belief.")
        else:
            with st.spinner("Retrieving evidence cards..."):
                results = retrieve_evidence(belief_input, profile_id, mode)
                
                if not results:
                    st.info("No evidence cards found matching the query.")
                else:
                    st.write(f"Found {len(results)} evidence card(s):")
                    for card in results:
                        with st.container():
                            st.markdown(f"""
                            <div class="card">
                                <h4>📦 Card ID: {card.evidence_id} (Profile: {card.profile_id})</h4>
                                <p><b>Event:</b> {card.event}</p>
                                <p><b>Source:</b> {card.source_type} ({card.source_id})</p>
                                <p><b>Associated Skills:</b> {', '.join(card.skills)}</p>
                                <p><b>Privacy Level:</b> {card.privacy_level}</p>
                            </div>
                            """, unsafe_allow_html=True)

with tab3:
    st.header("Document Importer")
    st.write("Scan and ingest journal entries from the imports directory.")
    
    imports_dir = "imports"
    st.markdown(f"Scanning directory: `{os.path.abspath(imports_dir)}`")
    
    if os.path.exists(imports_dir):
        files = os.listdir(imports_dir)
        valid_files = [f for f in files if f.endswith(('.txt', '.docx'))]
        
        if not valid_files:
            st.info("No new documents (.txt or .docx) found in the imports directory.")
        else:
            st.write("Pending files for ingestion:")
            for vf in valid_files:
                st.markdown(f"- 📄 `{vf}`")
                
            if st.button("Ingest Documents"):
                with st.spinner("Ingesting raw files..."):
                    importer = DocumentImporter()
                    results = importer.import_all()
                    st.success(f"Successfully ingested {len(results)} document(s).")
    else:
        st.error("Imports directory not found.")
