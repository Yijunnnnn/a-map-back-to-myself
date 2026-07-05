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
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from app.schemas import MemoryEntry, MemoryEvent, ImportedDocument

# 1. Load environment variables from .env
load_dotenv()

SELFMAP_MODE = os.getenv("SELFMAP_MODE", "demo")
ACTIVE_PROFILE_ID = os.getenv("ACTIVE_PROFILE_ID", "demo_user")
USE_DEMO_SEED = os.getenv("USE_DEMO_SEED", "true").lower() in ("true", "1", "yes")
ALLOW_USER_EVENTS = os.getenv("ALLOW_USER_EVENTS", "true").lower() in ("true", "1", "yes")

_demo_repaired = False


def read_jsonl(path: str) -> List[Dict]:
    """Read a JSONL file and return a list of parsed dictionaries."""
    records = []
    if not os.path.exists(path):
        return records
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception as e:
        raise IOError(f"Failed to read JSONL file at {path}: {str(e)}")
    return records


def write_jsonl(path: str, record: Dict) -> None:
    """Append a dictionary as a JSON line to the specified file path."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception as e:
        raise IOError(f"Failed to create directory for {path}: {str(e)}")
        
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        raise IOError(f"Failed to write record to JSONL file at {path}: {str(e)}")


def load_seed_memories() -> List[MemoryEntry]:
    """Read seed memories from data/seed_memories.readonly.json."""
    path = "data/seed_memories.readonly.json"
    memories = []
    if not os.path.exists(path):
        return memories
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Seed memories file must contain a JSON list.")
            for item in data:
                memories.append(MemoryEntry(
                    id=item.get("id") or str(uuid.uuid4()),
                    profile_id=item.get("profile_id") or "demo_user",
                    source_type=item.get("source_type") or "seed_demo",
                    source_id=item.get("source_id") or item.get("id") or "unknown",
                    date=item.get("date") or item.get("timestamp", "").split("T")[0] or datetime.utcnow().strftime("%Y-%m-%d"),
                    source=item.get("source") or "seed",
                    text=item.get("text") or item.get("content") or "",
                    tags=item.get("tags") or [],
                    emotion=item.get("emotion") or [],
                    privacy_level=item.get("privacy_level") or "public_demo"
                ))
    except Exception as e:
        raise IOError(f"Failed to load seed memories from {path}: {str(e)}")
        
    return memories


def auto_repair_sensitive_demo_records() -> None:
    """Ensure mira_011 and mira_018 are correctly marked as sensitive in all DB files on the fly."""
    global _demo_repaired
    for base_dir in ["data", "data/profiles/demo_user"]:
        docs_path = os.path.join(base_dir, "imported_documents.jsonl")
        events_path = os.path.join(base_dir, "memory_events.jsonl")
        
        # 1. Repair imported_documents.jsonl
        if os.path.exists(docs_path):
            updated_docs = []
            modified_docs = False
            try:
                with open(docs_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            doc = json.loads(line)
                            filename = doc.get("filename", "")
                            if ("mira_011_evening_journal" in filename or "mira_018_evening_journal" in filename) and doc.get("privacy_level") != "sensitive":
                                doc["privacy_level"] = "sensitive"
                                doc["send_to_gemini_allowed"] = False
                                doc["display_detail_allowed"] = False
                                modified_docs = True
                            updated_docs.append(doc)
                        except Exception:
                            pass
                if modified_docs:
                    _demo_repaired = True
                    with open(docs_path, "w", encoding="utf-8") as f:
                        for doc in updated_docs:
                            f.write(json.dumps(doc) + "\n")
            except Exception:
                pass
                        
        # 2. Repair memory_events.jsonl
        if os.path.exists(events_path):
            updated_events = []
            modified_events = False
            try:
                with open(events_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                            text = event.get("text", "")
                            source_id = event.get("source_id", "")
                            
                            is_target = "mira_011" in text or "mira_018" in text or "mira_011" in source_id or "mira_018" in source_id or "[PROTECTED — SENSITIVE]" in text
                            if is_target and (event.get("privacy_level") != "sensitive" or event.get("send_to_gemini_allowed") is not False):
                                event["privacy_level"] = "sensitive"
                                event["send_to_gemini_allowed"] = False
                                if "sensitive" not in event.get("tags", []):
                                    event.setdefault("tags", []).append("sensitive")
                                
                                date_str = event.get("created_at", "").split("T")[0] or "2026-06-20"
                                event["text"] = (
                                    f"[PROTECTED — SENSITIVE] A personal evening reflection was recorded on {date_str}. "
                                    f"Content is protected and not available for evidence retrieval or Gemini calls."
                                )
                                modified_events = True
                            updated_events.append(event)
                        except Exception:
                            pass
                if modified_events:
                    _demo_repaired = True
                    with open(events_path, "w", encoding="utf-8") as f:
                        for event in updated_events:
                            f.write(json.dumps(event) + "\n")
            except Exception:
                pass


def load_memory_events(mode: str = "demo", profile_id: Optional[str] = None) -> List[MemoryEvent]:
    """Read memory events from data/memory_events.jsonl or profile-specific jsonl, skipping deleted events."""
    auto_repair_sensitive_demo_records()
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if mode == "demo":
        path = "data/memory_events.jsonl"
    else:
        path = f"data/profiles/{resolved_profile_id}/memory_events.jsonl"
        
    events = []
    if not os.path.exists(path):
        return events
        
    records = read_jsonl(path)
    for item in records:
        if item.get("deleted", False):
            continue
        try:
            events.append(MemoryEvent(
                event_id=item.get("event_id") or str(uuid.uuid4()),
                type=item.get("type") or "manual",
                created_at=item.get("created_at") or datetime.utcnow().isoformat(),
                profile_id=item.get("profile_id") or "unknown",
                source_type=item.get("source_type") or "manual_input",
                source_id=item.get("source_id") or "unknown",
                text=item.get("text") or "",
                tags=item.get("tags") or [],
                privacy_level=item.get("privacy_level") or "private",
                deleted=False,
                send_to_gemini_allowed=item.get("send_to_gemini_allowed", True),
                original_belief=item.get("original_belief"),
                detected_biases=item.get("detected_biases"),
                selected_evidence_ids=item.get("selected_evidence_ids"),
                reframe=item.get("reframe"),
                next_action=item.get("next_action")
            ))
        except Exception as e:
            raise ValueError(f"Invalid MemoryEvent record in {path}: {str(e)}")
            
    return events


def append_memory_event(text: str, tags: Optional[List[str]] = None, privacy_level: str = "private", profile_id: Optional[str] = None) -> MemoryEvent:
    """Append one memory event to data/memory_events.jsonl."""
    path = "data/memory_events.jsonl"
    event_id = f"evt_{str(uuid.uuid4())[:8]}"
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    
    event = MemoryEvent(
        event_id=event_id,
        type="manual",
        created_at=datetime.utcnow().isoformat(),
        profile_id=resolved_profile_id,
        source_type="manual_input",
        source_id=event_id,
        text=text,
        tags=tags or [],
        privacy_level=privacy_level,
        deleted=False,
        send_to_gemini_allowed=True
    )
    
    # Write to profile directory too if not in demo mode
    write_jsonl(path, event.model_dump())
    if resolved_profile_id != "demo_user":
        profile_path = f"data/profiles/{resolved_profile_id}/memory_events.jsonl"
        write_jsonl(profile_path, event.model_dump())
        
    return event


def append_reflection_memory_event(
    text: str,
    original_belief: str,
    detected_biases: List[str],
    selected_evidence_ids: List[str],
    reframe: str,
    next_action: str,
    source_id: str,
    profile_id: Optional[str] = None
) -> MemoryEvent:
    path = "data/memory_events.jsonl"
    event_id = f"evt_{str(uuid.uuid4())[:8]}"
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    
    event = MemoryEvent(
        event_id=event_id,
        type="reflection_memory",
        created_at=datetime.utcnow().isoformat(),
        profile_id=resolved_profile_id,
        source_type="self_reflection",
        source_id=source_id,
        text=text,
        tags=["self_reflection", "cbt_reframe", "evidence_based"],
        privacy_level="private",
        deleted=False,
        send_to_gemini_allowed=True,
        original_belief=original_belief,
        detected_biases=detected_biases,
        selected_evidence_ids=selected_evidence_ids,
        reframe=reframe,
        next_action=next_action
    )
    
    write_jsonl(path, event.model_dump())
    if resolved_profile_id != "demo_user":
        profile_path = f"data/profiles/{resolved_profile_id}/memory_events.jsonl"
        write_jsonl(profile_path, event.model_dump())
        
    return event


def append_belief_query(query_id: str, raw_text: str, profile_id: str) -> None:
    path = "data/belief_queries.jsonl"
    record = {
        "query_id": query_id,
        "created_at": datetime.utcnow().isoformat(),
        "profile_id": profile_id,
        "raw_text": raw_text
    }
    write_jsonl(path, record)


def append_reflection_event(reflection_id: str, query_id: str, belief: str, text: str, evidence_ids: List[str], profile_id: str) -> None:
    path = "data/reflection_events.jsonl"
    record = {
        "reflection_id": reflection_id,
        "query_id": query_id,
        "created_at": datetime.utcnow().isoformat(),
        "profile_id": profile_id,
        "belief": belief,
        "text": text,
        "evidence_ids": evidence_ids
    }
    write_jsonl(path, record)


def load_imported_documents(mode: str = "demo", profile_id: Optional[str] = None) -> List[ImportedDocument]:
    """Read imported documents based on mode and profile."""
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    if mode == "demo":
        path = "data/imported_documents.jsonl"
    else:
        path = f"data/profiles/{resolved_profile_id}/imported_documents.jsonl"
        
    docs = []
    if not os.path.exists(path):
        return docs
        
    records = read_jsonl(path)
    for item in records:
        docs.append(ImportedDocument(
            document_id=item.get("document_id"),
            filename=item.get("filename"),
            file_type=item.get("file_type"),
            imported_at=item.get("imported_at"),
            profile_id=item.get("profile_id") or "unknown",
            privacy_level=item.get("privacy_level") or "private",
            status=item.get("status") or "success",
            chunks_created=item.get("chunks_created", 0),
            chunks_sent_to_gemini=item.get("chunks_sent_to_gemini", 0),
            send_to_gemini_allowed=item.get("send_to_gemini_allowed", True)
        ))
    return docs


def update_memory_event_privacy(event_id: str, privacy_level: str, send_to_gemini_allowed: bool, mode: str = "demo", profile_id: Optional[str] = None) -> None:
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    paths = ["data/memory_events.jsonl"]
    if mode != "demo":
        paths.append(f"data/profiles/{resolved_profile_id}/memory_events.jsonl")
    
    for path in paths:
        if not os.path.exists(path):
            continue
            
        records = read_jsonl(path)
        updated_records = []
        for item in records:
            if item.get("event_id") == event_id:
                item["privacy_level"] = privacy_level
                item["send_to_gemini_allowed"] = send_to_gemini_allowed
            updated_records.append(item)
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in updated_records:
                f.write(json.dumps(rec) + "\n")


def update_imported_document_privacy(document_id: str, privacy_level: str, send_to_gemini_allowed: bool, mode: str = "demo", profile_id: Optional[str] = None) -> None:
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    paths = ["data/imported_documents.jsonl"]
    if mode != "demo":
        paths.append(f"data/profiles/{resolved_profile_id}/imported_documents.jsonl")
        
    for path in paths:
        if not os.path.exists(path):
            continue
            
        records = read_jsonl(path)
        updated_records = []
        for item in records:
            if item.get("document_id") == document_id:
                item["privacy_level"] = privacy_level
                item["send_to_gemini_allowed"] = send_to_gemini_allowed
            updated_records.append(item)
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in updated_records:
                f.write(json.dumps(rec) + "\n")


def load_active_memories(mode: Optional[str] = None, profile_id: Optional[str] = None) -> List[MemoryEntry]:
    """Load memories based on current SELFMAP_MODE and ACTIVE_PROFILE_ID."""
    global _demo_repaired
    resolved_mode = mode or os.getenv("SELFMAP_MODE", "demo")
    resolved_profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    allow_events = os.getenv("ALLOW_USER_EVENTS", "true").lower() in ("true", "1", "yes")
    
    memories: List[MemoryEntry] = []
    
    if resolved_mode == "demo":
        memories = load_seed_memories()
        if allow_events:
            events = load_memory_events(resolved_mode, resolved_profile_id)
            demo_user_events = [e for e in events if e.profile_id == "demo_user"]
            if not demo_user_events:
                try:
                    from app.demo_corpus import import_demo_corpus
                    import_demo_corpus(silent=True)
                    events = load_memory_events(resolved_mode, resolved_profile_id)
                except Exception:
                    pass
            for evt in events:
                if evt.profile_id == "demo_user":
                    memories.append(MemoryEntry(
                        id=evt.event_id,
                        profile_id=evt.profile_id,
                        source_type=evt.source_type,
                        source_id=evt.source_id,
                        date=evt.created_at.split("T")[0],
                        source="manual",
                        text=evt.text,
                        tags=evt.tags,
                        emotion=[],
                        privacy_level=evt.privacy_level,
                        send_to_gemini_allowed=evt.send_to_gemini_allowed
                    ))
        
    elif resolved_mode == "user":
        if allow_events:
            events = load_memory_events(resolved_mode, resolved_profile_id)
            for evt in events:
                if evt.profile_id == resolved_profile_id:
                    memories.append(MemoryEntry(
                        id=evt.event_id,
                        profile_id=evt.profile_id,
                        source_type=evt.source_type,
                        source_id=evt.source_id,
                        date=evt.created_at.split("T")[0],
                        source="manual",
                        text=evt.text,
                        tags=evt.tags,
                        emotion=[],
                        privacy_level=evt.privacy_level,
                        send_to_gemini_allowed=evt.send_to_gemini_allowed
                    ))
                    
    elif resolved_mode == "mixed_demo":
        memories.extend(load_seed_memories())
        if allow_events:
            events = load_memory_events(resolved_mode, resolved_profile_id)
            for evt in events:
                if evt.profile_id == resolved_profile_id:
                    memories.append(MemoryEntry(
                        id=evt.event_id,
                        profile_id=evt.profile_id,
                        source_type=evt.source_type,
                        source_id=evt.source_id,
                        date=evt.created_at.split("T")[0],
                        source="manual",
                        text=evt.text,
                        tags=evt.tags,
                        emotion=[],
                        privacy_level=evt.privacy_level,
                        send_to_gemini_allowed=evt.send_to_gemini_allowed
                    ))
    else:
        raise ValueError(f"Unknown SELFMAP_MODE: '{resolved_mode}'. Must be 'demo', 'user', or 'mixed_demo'.")
        
    # Check if cached manual cards contain deleted events
    try:
        cards_path = "derived/evidence_cards.json"
        if os.path.exists(cards_path):
            with open(cards_path, "r", encoding="utf-8") as f:
                cached_cards = json.load(f)
            cached_source_ids = {c.get("source_id") for c in cached_cards if c.get("source_type") == "manual_input"}
            active_ids = {m.id for m in memories if m.source == "manual"}
            if not cached_source_ids.issubset(active_ids):
                _demo_repaired = True
    except Exception:
        pass

    if _demo_repaired:
        _demo_repaired = False
        try:
            from app.evidence_builder import build_evidence_cards
            from app.graph_builder import build_personal_graph
            cards = build_evidence_cards(memories)
            build_personal_graph(cards)
        except Exception:
            pass

    return memories


class MemoryStore:
    """Legacy class wrapper to support calls to MemoryStore."""
    def __init__(self, mode: Optional[str] = None, profile_id: Optional[str] = None):
        self.mode = mode or os.getenv("SELFMAP_MODE", "demo")
        self.profile_id = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")

    def get_all_memories(self) -> List[MemoryEntry]:
        old_mode = os.environ.get("SELFMAP_MODE")
        old_profile = os.environ.get("ACTIVE_PROFILE_ID")
        if self.mode:
            os.environ["SELFMAP_MODE"] = self.mode
        if self.profile_id:
            os.environ["ACTIVE_PROFILE_ID"] = self.profile_id
        
        try:
            return load_active_memories()
        finally:
            if old_mode is not None:
                os.environ["SELFMAP_MODE"] = old_mode
            else:
                os.environ.pop("SELFMAP_MODE", None)
            if old_profile is not None:
                os.environ["ACTIVE_PROFILE_ID"] = old_profile
            else:
                os.environ.pop("ACTIVE_PROFILE_ID", None)

    def add_memory(self, memory: Dict):
        text = memory.get("content") or memory.get("text") or ""
        tags = memory.get("tags") or []
        privacy_level = memory.get("privacy_level") or "private"
        profile_id = memory.get("profile_id") or self.profile_id
        append_memory_event(text, tags=tags, privacy_level=privacy_level, profile_id=profile_id)
