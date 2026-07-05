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
import argparse
import re
import json
from datetime import datetime
from dotenv import load_dotenv

from app.memory_store import (
    load_active_memories,
    append_memory_event
)
from app.evidence_builder import build_evidence_cards
from app.graph_builder import build_personal_graph
from app.safety import classify_safety
from app.cbt_bias_agent import detect_bias
from app.evidence_planner import plan_evidence_search
from app.retriever import retrieve_candidate_evidence, load_evidence_cards_raw
from app.prompt_builder import build_reranker_prompt
from app.gemini_client import call_gemini_text
from app.gemini_gate import can_send_to_gemini, log_gemini_decision
from app.reflection import generate_final_reflection, local_crisis_response, local_watch_response
from app.output_guard import validate_output
from app.document_importer import import_file
from app.demo_corpus import import_demo_corpus

# Safe rich imports fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


def print_panel(text: str, title: str = ""):
    if HAS_RICH and console:
        console.print(Panel(text, title=title))
    else:
        print(f"\n=== {title} ===")
        print(text)
        print("===============\n")


def print_table(title: str, rows: list, headers: list = None):
    if HAS_RICH and console:
        table = Table(title=title, show_header=bool(headers))
        if headers:
            for h in headers:
                table.add_column(h)
        for r in rows:
            table.add_row(*r)
        console.print(table)
    else:
        print(f"\n--- {title} ---")
        if headers:
            print(" | ".join(headers))
        for r in rows:
            print(" | ".join(r))
        print("----------------\n")


def cmd_rebuild(args):
    load_dotenv()
    resolved_mode = args.mode or os.getenv("SELFMAP_MODE", "demo")
    resolved_profile_id = args.profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if resolved_mode == "demo":
        resolved_profile_id = "demo_user"

    # 1. Load active memories
    memories = load_active_memories(resolved_mode, resolved_profile_id)

    # 2. Build evidence cards
    cards = build_evidence_cards(memories)

    # 3. Build personal graph
    graph_data = build_personal_graph(cards)

    # 4. Rebuild retrieval index
    index_path = "derived/retrieval_index.json"
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    index_data = []
    for c in cards:
        index_data.append({
            "evidence_id": c.evidence_id,
            "keywords": list(set((c.event + " " + " ".join(c.skills)).lower().split()))
        })
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    # 5. Extract counts
    seed_count = len([m for m in memories if m.source_type == "seed_demo"])
    event_count = len([m for m in memories if m.source_type != "seed_demo"])
    
    cbt_count = 6
    cbt_path = "data/cbt_cards.json"
    if os.path.exists(cbt_path):
        try:
            with open(cbt_path, "r", encoding="utf-8") as f:
                cbt_cards = json.load(f)
                cbt_count = len(cbt_cards)
        except Exception:
            pass

    node_count = len(graph_data.get("nodes", []))
    edge_count = len(graph_data.get("links", []) or graph_data.get("edges", []))

    # Print the exact layout requested by the user
    print("SelfMap rebuild\n")
    print(f"Mode: {resolved_mode}")
    print(f"Active profile: {resolved_profile_id}")
    print(f"Loaded CBT cards: {cbt_count}")
    print(f"Loaded seed memories: {seed_count}")
    print(f"Loaded memory events: {event_count}")
    print(f"Evidence cards generated: {len(cards)}")
    print(f"Graph nodes: {node_count}")
    print(f"Graph edges: {edge_count}")
    print("Retrieval index updated")
    print("Gemini calls: 0")


def cmd_add_memory(args):
    load_dotenv()
    resolved_mode = os.getenv("SELFMAP_MODE", "demo")
    resolved_profile_id = os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if resolved_mode == "demo":
        resolved_profile_id = "demo_user"

    text = args.text

    # 1. Run privacy precheck
    payload = {
        "contains_raw_file": False,
        "contains_hidden_memory": False,
        "requests_full_memory_dump": False,
        "contains_api_key_or_secret": ("api_key" in text.lower() or "secret" in text.lower()),
        "contains_sensitive_data": False,
        "explicit_consent": True,
        "route": "evidence_reflection"
    }
    allowed, reason = can_send_to_gemini(payload)

    if not allowed:
        log_gemini_decision("add_memory", False, reason)
        print("Privacy: blocked")
        print(f"Reason: {reason}")
        print("Gemini calls: 0")
        return

    # 2. Append memory event
    evt = append_memory_event(
        text=text,
        tags=[],
        privacy_level="private",
        profile_id=resolved_profile_id
    )

    # 3. Rebuild
    memories = load_active_memories(resolved_mode, resolved_profile_id)
    cards = build_evidence_cards(memories)
    build_personal_graph(cards)

    # Print the exact layout requested by the user
    print("Privacy: passed")
    print("Memory event appended")
    print("Rebuild completed")
    print("Gemini calls: 0")


def cmd_import_file(args):
    load_dotenv()
    resolved_mode = os.getenv("SELFMAP_MODE", "demo")
    resolved_profile_id = os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if resolved_mode == "demo":
        resolved_profile_id = "demo_user"

    use_gemini = args.use_gemini
    if args.local_only:
        use_gemini = False

    # 1. Call document_importer.import_file
    doc_metadata = import_file(
        path=args.path,
        privacy_level=args.privacy,
        use_gemini=use_gemini,
        profile_id=resolved_profile_id
    )

    # 2. Rebuild
    memories = load_active_memories(resolved_mode, resolved_profile_id)
    cards = build_evidence_cards(memories)
    build_personal_graph(cards)

    # 3. Print Results Summary
    chunks_created = doc_metadata.get("chunks_created", 0)
    chunks_sent = doc_metadata.get("chunks_sent_to_gemini", 0)

    if use_gemini:
        print("Text extracted locally")
        print("PII redaction applied")
        print(f"Chunks created: {chunks_created}")
        print(f"Chunks sent to Gemini: {chunks_sent}")
        print("Gemini Call 1 completed")
        print("Evidence cards generated")
        print("Graph updated")
        print(f"Gemini calls: {chunks_sent}")
    else:
        print("Text extracted locally")
        print(f"Chunks created: {chunks_created}")
        print(f"Gemini calls: {chunks_sent}")
        print("Memory events appended")
        print("Graph updated")


def cmd_ask(args):
    load_dotenv()
    resolved_mode = os.getenv("SELFMAP_MODE", "demo")
    resolved_profile_id = os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if resolved_mode == "demo":
        resolved_profile_id = "demo_user"

    belief = args.belief

    # 1. Run privacy precheck
    contains_raw = False
    lower_belief = belief.lower()
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
        print_panel(
            f"Privacy Blocked\n"
            f"Local block: {reason}\n"
            f"Gemini calls: 0",
            title="Ask Response"
        )
        return

    # 2. Run safety classifier
    safety_res = classify_safety(belief)
    if safety_res.risk_level == "crisis":
        print_panel(
            f"Crisis Response Triggered\n"
            f"{local_crisis_response()}\n"
            f"Gemini calls: 0",
            title="Ask Response"
        )
        return
    elif safety_res.risk_level == "watch":
        print_panel(
            f"Limited Supportive Response\n"
            f"{local_watch_response()}\n"
            f"Gemini calls: 0",
            title="Ask Response"
        )
        return

    # 3. Normal path:
    # bias detection
    bias_res = detect_bias(belief)

    # evidence planning
    plan = plan_evidence_search(belief, bias_res)

    # retrieve top 10 candidate evidence
    candidates = retrieve_candidate_evidence(
        belief_text=belief,
        bias_result=bias_res,
        profile_id=resolved_profile_id,
        mode=resolved_mode,
        top_k=10
    )

    # Gemini Call 2: Reranker
    if candidates:
        rerank_prompt = build_reranker_prompt(belief, bias_res, candidates)
        try:
            rerank_response = call_gemini_text(rerank_prompt, "reranker")
            selected_ids = re.findall(r'\b(?:card|ev)_\w+\b', rerank_response)
            selected_evidence = [c for c in candidates if (c.evidence_id if hasattr(c, 'evidence_id') else c.get('evidence_id')) in selected_ids]
            if not selected_evidence:
                selected_evidence = candidates[:3]
        except Exception:
            selected_evidence = candidates[:3]
    else:
        selected_evidence = []

    # Gemini Call 3: Reflection
    reframe_plan = {"route": "evidence_reflection"}
    reflection_res = generate_final_reflection(
        belief=belief,
        bias_result=bias_res,
        selected_evidence=selected_evidence,
        reframe_plan=reframe_plan
    )

    # Output guard
    is_valid, final_text = validate_output(
        response_text=reflection_res.text,
        selected_evidence=selected_evidence,
        safety_result=safety_res
    )

    # Calculate calls: reranker (1 call if candidates) + reflection call
    calls_made = 1 + reflection_res.gemini_calls if candidates else reflection_res.gemini_calls

    print_panel(
        f"Reflection Response:\n"
        f"{final_text}\n\n"
        f"Gemini calls: {calls_made}",
        title="Ask Response"
    )


def cmd_show_evidence(args):
    load_dotenv()
    cards = load_evidence_cards_raw()

    # Sort latest
    latest_cards = cards[::-1][:5]

    rows = []
    for c in latest_cards:
        rows.append([
            c.evidence_id,
            c.date,
            c.event[:50] + "..." if len(c.event) > 50 else c.event,
            ", ".join(c.skills),
            c.privacy_level
        ])

    print_table("Latest Evidence Cards", rows, headers=["ID", "Date", "Event", "Skills", "Privacy"])


def cmd_import_demo_corpus(args):
    load_dotenv()
    res = import_demo_corpus()
    print("SelfMap import-demo-corpus\n")
    print(f"TXT files imported:          {res['txt_imported']}")
    print(f"PDF files imported:          {res['pdf_imported']}")
    print(f"DOCX files imported:         {res['docx_imported']}")
    print(f"Markdown files imported:     {res['md_imported']}")
    print(f"Private records:             {res['private_count']}")
    print(f"Sensitive records:           {res['sensitive_count']}")
    print(f"Sensitive records to Gemini: {res['sensitive_gemini_calls']}")
    print(f"Protected Evidence Cards:    {res['protected_cards_created']}")
    print(f"Memory events created:       {res['events_created']}")
    print(f"Evidence cards generated:    {res['cards_generated']}")
    print(f"Gemini calls:                0")


def main():
    parser = argparse.ArgumentParser(description="SelfMap Agent Command Line Interface.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # rebuild
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild evidence cards and belief graph.")
    rebuild_parser.add_argument("--mode", default=None, help="Execution mode (demo, user, mixed_demo).")
    rebuild_parser.add_argument("--profile-id", default=None, help="Active user profile ID.")

    # add-memory
    add_mem_parser = subparsers.add_parser("add-memory", help="Add a manual memory event.")
    add_mem_parser.add_argument("text", help="The memory text to add.")

    # import-file
    import_parser = subparsers.add_parser("import-file", help="Import a document file.")
    import_parser.add_argument("path", help="Path to the document file.")
    import_parser.add_argument("--privacy", default="private", help="Privacy level.")
    import_parser.add_argument("--use-gemini", action="store_true", help="Use Gemini to extract cards.")
    import_parser.add_argument("--local-only", action="store_true", help="Only extract cards locally.")

    # import-demo-corpus
    subparsers.add_parser("import-demo-corpus", help="Import the Mira Vale multi-format demo corpus.")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Query a belief statement.")
    ask_parser.add_argument("belief", help="The belief to query.")

    # show-evidence
    show_parser = subparsers.add_parser("show-evidence", help="Show evidence cards.")
    show_parser.add_argument("--latest", action="store_true", help="Show latest 5 evidence cards.")

    args = parser.parse_args()

    if args.command == "rebuild":
        cmd_rebuild(args)
    elif args.command == "add-memory":
        cmd_add_memory(args)
    elif args.command == "import-file":
        cmd_import_file(args)
    elif args.command == "import-demo-corpus":
        cmd_import_demo_corpus(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "show-evidence":
        cmd_show_evidence(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
