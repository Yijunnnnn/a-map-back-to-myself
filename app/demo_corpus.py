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
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any
from app.memory_store import (
    read_jsonl,
    write_jsonl,
    load_active_memories
)
from app.schemas import MemoryEvent, ImportedDocument
from app.evidence_builder import build_evidence_cards
from app.graph_builder import build_personal_graph

# 30 Synthetic Mira Vale Diary Entries
MIRA_DEMO_ENTRIES = [
    # TXT (1-5)
    {
        "id": "mira_001",
        "filename": "txt/mira_001_morning_journal.txt",
        "title": "Morning Journal: A Fresh Beginning",
        "date": "2026-06-01",
        "body": "Today I woke up early to start working on the new exhibition design. I felt anxious about whether my artistic choices would resonate with the curators, but I also felt a deep spark of creative energy. I want to build a clear, structured framework to guide my creative workflow. Breaking the canvas design down into small steps is the best way to handle this complexity."
    },
    {
        "id": "mira_002",
        "filename": "txt/mira_002_archive_work_log.txt",
        "title": "Archive Work Log: Design System Alignment",
        "date": "2026-06-02",
        "body": "Spent the afternoon in the studio organizing the digital asset archive. I reached out to the lead developer to clarify the naming conventions for our shared graphics library. Communicating early helped us resolve three potential namespace conflicts before they became real blockers."
    },
    {
        "id": "mira_003",
        "filename": "txt/mira_003_studio_journal.txt",
        "title": "Studio Journal: Strains of Painting",
        "date": "2026-06-03",
        "body": "It was a challenging session stretching the large linen canvases. The canvas ripped twice, and my hands are quite sore. However, I didn't give up. I re-stretched the frame for a third time, paying closer attention to the tension points. Persistence paid off, and now it stands sturdy and ready for the first layers of gesso."
    },
    {
        "id": "mira_004",
        "filename": "txt/mira_004_critique_reflection.txt",
        "title": "Critique Reflection: Simplifying the Flow",
        "date": "2026-06-04",
        "body": "Had a constructive critique session with the senior designer. They suggested that my portfolio layout was a bit cluttered. Instead of feeling defensive, I listened to their advice and brainstormed three ways to simplify the grid system. I'm excited to apply these modifications tomorrow."
    },
    {
        "id": "mira_005",
        "filename": "txt/mira_005_learning_log.txt",
        "title": "Learning Log: Cognitive Biases and Systems",
        "date": "2026-06-05",
        "body": "I read an interesting article about cognitive distortions today, specifically overgeneralization and negativity bias. Understanding these mental patterns makes me realize how often we jump to conclusions without checking the facts. I'd like to use evidence-based reframing in my personal journal to stay grounded."
    },

    # PDF (6-20)
    {
        "id": "mira_006",
        "filename": "pdf/mira_006_personal_reflection.pdf",
        "title": "Personal Reflection: Managing Timelines",
        "date": "2026-06-06",
        "body": "The gallery deadline is approaching quickly, and I felt overwhelmed this morning. To manage my stress, I broke the remaining tasks down into a day-by-day roadmap. Realizing that I have enough time if I stick to the schedule helped me regain my calm and start working productively."
    },
    {
        "id": "mira_007",
        "filename": "pdf/mira_007_archive_work_log.pdf",
        "title": "Archive Work Log: Handoff Specifications",
        "date": "2026-06-07",
        "body": "I finalized the documentation for the archive handoff today. I scheduled a quick 15-minute call with the product manager to walk through the folder structure. They appreciated the proactive alignment, and we agreed on the metadata standards."
    },
    {
        "id": "mira_008",
        "filename": "pdf/mira_008_morning_journal.pdf",
        "title": "Morning Journal: Senior Mentorship",
        "date": "2026-06-08",
        "body": "Had coffee with my mentor today. We discussed how to balance commercial freelance work with personal fine art projects. They shared their own experience of setting strict boundaries, which was a very valuable lesson in professional resilience."
    },
    {
        "id": "mira_009",
        "filename": "pdf/mira_009_friend_feedback.pdf",
        "title": "Friend Feedback: Empathetic Designs",
        "date": "2026-06-09",
        "body": "A fellow artist reviewed my draft designs. They mentioned that the layouts are deeply empathetic and user-focused, though some areas could be streamlined. Their feedback is a great reminder to design for clarity above all else."
    },
    {
        "id": "mira_010",
        "filename": "pdf/mira_010_studio_journal.pdf",
        "title": "Studio Journal: Experimenting with Texture",
        "date": "2026-06-10",
        "body": "Spent five hours painting. I experimented with a new heavy gel medium to add physical texture to the background. Some parts dried unevenly, but I learned how the material reacts to different drying temperatures. I'll adjust my technique on the next attempt."
    },
    {
        "id": "mira_011",
        "filename": "pdf/mira_011_evening_journal.pdf",
        "title": "Evening Journal: Psychological Feedback Loops",
        "date": "2026-06-11",
        "privacy_level": "sensitive",
        "body": "Reflected tonight on feedback loops in digital design. Creating clear visual cues helps users feel in control of the interface. This matches my goal of designing intuitive, stress-free user experiences."
    },
    {
        "id": "mira_012",
        "filename": "pdf/mira_012_learning_log.pdf",
        "title": "Learning Log: Advanced Figma Library Management",
        "date": "2026-06-12",
        "body": "Finished a comprehensive tutorial on Figma auto-layout and variable scoping. It took three hours of focused practice, but I now feel confident using these advanced techniques to build highly responsive layout systems."
    },
    {
        "id": "mira_013",
        "filename": "pdf/mira_013_archive_work_log.pdf",
        "title": "Archive Work Log: Branch Conflicts Resolved",
        "date": "2026-06-13",
        "body": "Encountered a major branch conflict in our shared repository today. I worked closely with the development team to isolate the changes, manually reviewing the conflicting code snippets. We successfully merged the branches without losing any design assets."
    },
    {
        "id": "mira_014",
        "filename": "pdf/mira_014_studio_journal.pdf",
        "title": "Studio Journal: Studio Organization",
        "date": "2026-06-14",
        "body": "Spent the morning reorganizing my brushes and paints. A clean, organized workspace reduces cognitive load and allows me to focus fully on the creative process. It feels great to start the week with a tidy environment."
    },
    {
        "id": "mira_015",
        "filename": "pdf/mira_015_cbt_reflection_note.pdf",
        "title": "CBT Reflection Note: Overcoming Career Worries",
        "date": "2026-06-15",
        "body": "I had a sudden thought that I'm not making fast enough progress in my career. I stopped and wrote down the evidence: I've successfully completed three major client projects in the last six months, and received excellent feedback. Career growth is a gradual journey, and the evidence shows I am moving forward."
    },
    {
        "id": "mira_016",
        "filename": "pdf/mira_016_portfolio_review.pdf",
        "title": "Portfolio Review: Clarity and Structure",
        "date": "2026-06-16",
        "body": "The gallery curator reviewed my portfolio case studies. They praised the clear structure and the logical flow of my design explanations. It's rewarding to see that my focus on clarity is appreciated by industry professionals."
    },
    {
        "id": "mira_017",
        "filename": "pdf/mira_017_archive_work_log.pdf",
        "title": "Archive Work Log: Documenting Tokens",
        "date": "2026-06-17",
        "body": "I finished documenting the typography design tokens today. Writing down the specifications for spacing and font sizes ensures that our design system remains consistent across all digital and print mediums."
    },
    {
        "id": "mira_018",
        "filename": "pdf/mira_018_evening_journal.pdf",
        "title": "Evening Journal: AI and Traditional Art",
        "date": "2026-06-18",
        "privacy_level": "sensitive",
        "body": "Discussed the intersection of artificial intelligence and traditional oil painting with a fellow artist. We brainstormed how generative systems can act as rapid sketching tools to explore composition before moving to the canvas."
    },
    {
        "id": "mira_019",
        "filename": "pdf/mira_019_studio_journal.pdf",
        "title": "Studio Journal: Watercolor Moisture Control",
        "date": "2026-06-19",
        "body": "Had a challenging session with watercolors, trying to paint a soft gradient. The paper buckled because I used too much water. I waited for it to dry, pressed it flat, and tried again with drier brush techniques. Learning to control paper moisture is a slow but satisfying skill."
    },
    {
        "id": "mira_020",
        "filename": "pdf/mira_020_personal_reflection.pdf",
        "title": "Personal Reflection: Proof of Growth",
        "date": "2026-06-20",
        "body": "I felt a brief wave of self-doubt today, thinking I haven't grown as an artist. I pulled out my sketchbooks from two years ago and compared them to my current canvases. The difference in composition control and color harmony was clear. The evidence is solid: my practice has led to real improvement."
    },

    # DOCX (21-25)
    {
        "id": "mira_021",
        "filename": "docx/mira_021_archive_work_log.docx",
        "title": "Archive Work Log: Developer Feedback Integration",
        "date": "2026-06-21",
        "body": "Updated the export formats in the design specification sheets based on developer feedback. Standardizing the file types will prevent rendering issues and make the asset handoff process much smoother."
    },
    {
        "id": "mira_022",
        "filename": "docx/mira_022_studio_journal.docx",
        "title": "Studio Journal: Exhibition Poster Draft",
        "date": "2026-06-22",
        "body": "Completed the initial draft for the gallery exhibition poster. I focused on clean typography and balanced whitespace to ensure the key dates and location details are immediately legible from a distance."
    },
    {
        "id": "mira_023",
        "filename": "docx/mira_023_presentation_practice_log.docx",
        "title": "Presentation Practice Log: Improving Pitch Timing",
        "date": "2026-06-23",
        "body": "Practiced my upcoming presentation for the design sprint today. By focusing on key speaking points and removing repetitive slides, I managed to improve my timing by 2 minutes, bringing the presentation exactly to the 10-minute mark."
    },
    {
        "id": "mira_024",
        "filename": "docx/mira_024_portfolio_reflection.docx",
        "title": "Portfolio Reflection: Case Study Structure",
        "date": "2026-06-24",
        "body": "I decided to restructure my online portfolio to focus on case studies that show the entire process from research to delivery. Explaining the reasoning behind design choices will showcase my strategic thinking much better."
    },
    {
        "id": "mira_025",
        "filename": "docx/mira_025_friend_feedback.docx",
        "title": "Friend Feedback: Sprint Retrospectives",
        "date": "2026-06-25",
        "body": "A coworker thanked me today for facilitating the retrospective session. They mentioned that my structure allowed the team to address critical issues constructively, which was a great boost to my communication confidence."
    },

    # Markdown (26-30)
    {
        "id": "mira_026",
        "filename": "md/mira_026_archive_work_log.md",
        "title": "Archive Work Log: Handoff Documentation",
        "date": "2026-06-26",
        "body": "Drafted clear markdown documentation for the developer handoff. Having a single source of truth for design patterns and variable names will save time for both designers and developers."
    },
    {
        "id": "mira_027",
        "filename": "md/mira_027_studio_journal.md",
        "title": "Studio Journal: Recovering a Print",
        "date": "2026-06-27",
        "body": "One of my linocut prints smeared during the ink transfer. Instead of throwing it away, I cut out the clean portions and used them as elements in a mixed-media collage. The resulting piece has a unique, layered character that I couldn't have planned."
    },
    {
        "id": "mira_028",
        "filename": "md/mira_028_selfmap_reflection_note.md",
        "title": "SelfMap Reflection Note: Tracking distortions",
        "date": "2026-06-28",
        "body": "Used SelfMap to analyze some automatic negative thoughts I wrote down last week. Seeing the evidence mapped out helped me recognize that my fear of missing timelines was an overgeneralization. Realizing this allowed me to proceed with confidence."
    },
    {
        "id": "mira_029",
        "filename": "md/mira_029_process_note.md",
        "title": "Process Note: Testing Protocols",
        "date": "2026-06-29",
        "body": "Refined the user testing protocol for our prototype. I simplified the tasks to focus on the primary navigation. This will help us gather cleaner, less biased feedback from our participants."
    },
    {
        "id": "mira_030",
        "filename": "md/mira_030_evening_journal.md",
        "title": "Evening Journal: End of Sprint Reflections",
        "date": "2026-06-30",
        "body": "End of the sprint today. Reflecting on our progress, I'm proud of the collaboration within the team. We hit all major milestones and maintained clear communication despite tight schedules. A solid end to a productive month."
    }
]


# IDs marked as sensitive — protected evidence card behavior applies
SENSITIVE_ENTRY_IDS = {"mira_011", "mira_018"}


def generate_demo_files(base_dir: str = "imports/demo_mira") -> None:
    """Generate the 30 synthetic files locally if they do not exist."""
    for entry in MIRA_DEMO_ENTRIES:
        file_path = os.path.join(base_dir, entry["filename"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Respect per-entry privacy level (default private)
        privacy_level = entry.get("privacy_level", "private")
        
        # Build document text content in the required format
        content_lines = [
            f"Title: {entry['title']}",
            f"Date: {entry['date']}",
            f"Source: {os.path.basename(entry['filename'])}",
            "Demo Persona: Mira Vale",
            f"Privacy Level: {privacy_level}",
            "",
            entry["body"]
        ]
        file_content = "\n".join(content_lines)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)


def import_demo_corpus(base_dir: str = "imports/demo_mira", silent: bool = False) -> Dict[str, Any]:
    """Import the demo corpus files.
    - profile_id = demo_user, source_type = demo_import
    - local-only extraction (Gemini calls = 0 always)
    - mira_011 and mira_018 are sensitive:
        * send_to_gemini_allowed = False
        * display_detail_allowed = False
        * produces protected evidence cards (abstract, confidence <= 0.5)
    - deduplication by filename to prevent double imports
    - rebuilds evidence cards and personal graph
    """
    generate_demo_files(base_dir)

    txt_count = 0
    pdf_count = 0
    docx_count = 0
    md_count = 0
    private_count = 0
    sensitive_count = 0
    events_created = 0
    protected_cards_created = 0

    # Load existing imported documents to avoid duplicates
    existing_docs = read_jsonl("data/imported_documents.jsonl")
    existing_filenames = {d.get("filename") for d in existing_docs}

    for entry in MIRA_DEMO_ENTRIES:
        filename = os.path.basename(entry["filename"])
        file_path = os.path.join(base_dir, entry["filename"])
        ext = os.path.splitext(filename)[1].lower()

        # Duplicate detection by filename
        if filename in existing_filenames:
            if not silent:
                print(f"Skipping duplicate file: {filename}")
            continue

        # Count by file type
        if ext == ".txt":
            txt_count += 1
        elif ext == ".pdf":
            pdf_count += 1
        elif ext == ".docx":
            docx_count += 1
        elif ext == ".md":
            md_count += 1

        doc_id = f"doc_{str(uuid.uuid4())[:8]}"

        # Determine privacy level for this entry
        is_sensitive = entry.get("id") in SENSITIVE_ENTRY_IDS
        privacy_level = "sensitive" if is_sensitive else "private"
        send_to_gemini_allowed = not is_sensitive
        display_detail_allowed = not is_sensitive

        if is_sensitive:
            sensitive_count += 1
        else:
            private_count += 1

        # Append to imported_documents.jsonl
        doc_metadata = {
            "document_id": doc_id,
            "filename": filename,
            "file_type": ext[1:] if ext.startswith(".") else ext,
            "imported_at": datetime.utcnow().isoformat(),
            "profile_id": "demo_user",
            "privacy_level": privacy_level,
            "status": "success",
            "chunks_created": 1,
            "chunks_sent_to_gemini": 0,
            "send_to_gemini_allowed": send_to_gemini_allowed,
            "display_detail_allowed": display_detail_allowed
        }
        write_jsonl("data/imported_documents.jsonl", doc_metadata)
        write_jsonl("data/profiles/demo_user/imported_documents.jsonl", doc_metadata)

        # Create memory event
        tags = ["demo_import"]
        body_lower = entry["body"].lower()
        if any(kw in body_lower for kw in ["communication", "retrospective", "feedback", "conflict"]):
            tags.append("communication")
        if any(kw in body_lower for kw in ["resilience", "persist", "anxious", "doubt"]):
            tags.append("resilience")
        if any(kw in body_lower for kw in ["learning", "learn", "tutorial", "read"]):
            tags.append("learning")
        if any(kw in body_lower for kw in ["product", "design", "canvas"]):
            tags.append("product_thinking")
        if is_sensitive:
            tags.append("sensitive")

        # For sensitive entries: store abstract summary instead of raw body
        if is_sensitive:
            memory_text = (
                f"[PROTECTED — {privacy_level.upper()}] "
                f"A personal evening reflection was recorded on {entry['date']}. "
                f"Content is protected and not available for evidence retrieval or Gemini calls."
            )
        else:
            memory_text = entry["body"]

        event = MemoryEvent(
            event_id=f"evt_local_{str(uuid.uuid4())[:8]}",
            type="document_import",
            created_at=datetime.utcnow().isoformat(),
            profile_id="demo_user",
            source_type="demo_import",
            source_id=doc_id,
            text=memory_text,
            tags=tags,
            privacy_level=privacy_level,
            deleted=False,
            send_to_gemini_allowed=send_to_gemini_allowed
        )
        write_jsonl("data/memory_events.jsonl", event.model_dump())
        write_jsonl("data/profiles/demo_user/memory_events.jsonl", event.model_dump())
        events_created += 1

        # Write a protected evidence card for sensitive entries directly into derived/evidence_cards.json
        if is_sensitive:
            protected_card = {
                "evidence_id": f"card_{str(uuid.uuid4())[:8]}",
                "source_id": doc_id,
                "profile_id": "demo_user",
                "date": entry["date"],
                "source_type": "demo_import",
                "event": f"[Protected] An evening reflection was recorded ({entry['date']})",
                "skills": ["self-awareness"],
                "tags": tags,
                "privacy_level": "sensitive",
                "send_to_gemini_allowed": False,
                "display_detail_allowed": False,
                "needs_review": True,
                "extraction_method": "local_sensitive_template",
                "confidence": 0.3
            }
            # Append to evidence_cards.json
            cards_path = "derived/evidence_cards.json"
            existing_cards = []
            if os.path.exists(cards_path):
                try:
                    with open(cards_path, "r", encoding="utf-8") as f:
                        existing_cards = json.load(f)
                except Exception:
                    existing_cards = []
            existing_cards.append(protected_card)
            os.makedirs("derived", exist_ok=True)
            with open(cards_path, "w", encoding="utf-8") as f:
                json.dump(existing_cards, f, indent=2)
            protected_cards_created += 1

    # Rebuild Evidence Cards and Personal Graph
    memories = load_active_memories("demo", "demo_user")
    cards = build_evidence_cards(memories)
    build_personal_graph(cards)

    return {
        "txt_imported": txt_count,
        "pdf_imported": pdf_count,
        "docx_imported": docx_count,
        "md_imported": md_count,
        "private_count": private_count,
        "sensitive_count": sensitive_count,
        "events_created": events_created,
        "cards_generated": len(cards),
        "sensitive_gemini_calls": 0,
        "protected_cards_created": protected_cards_created,
        "gemini_calls": 0
    }
