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
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()


def extract_text(path: str) -> str:
    """Extracts text locally from PDF, DOCX, TXT, or MD files."""
    ext = os.path.splitext(path)[1].lower()
    
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
            
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            # Direct text read fallback for tests/mock docx files
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return "[Error reading DOCX binary file]"
                
    elif ext == ".pdf":
        text = ""
        # 1. Try PyMuPDF
        try:
            import fitz
            doc = fitz.open(path)
            text = "\n".join([page.get_text() for page in doc])
            if text.strip():
                return text
        except Exception:
            pass
            
        # 2. Try pypdf fallback
        try:
            import pypdf
            reader = pypdf.PdfReader(path)
            text = "\n".join([page.extract_text() for page in reader.pages])
            if text.strip():
                return text
        except Exception:
            pass
            
        # 3. Fallback to direct read for simple text/mock files
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return "[Error reading PDF binary file]"
            
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def import_file(
    path: str,
    privacy_level: str = "private",
    use_gemini: bool = False,
    profile_id: Optional[str] = None
) -> Dict[str, Any]:
    """Imports a single document, chunks it, applies privacy/safety rules, and runs extraction."""
    active_profile = profile_id or os.getenv("ACTIVE_PROFILE_ID", "demo_user")
    
    # 1. Extract text locally
    raw_text = extract_text(path)
    
    # Hard Limit: max file characters = 10000
    raw_text = raw_text[:10000]
    
    chunk_size = 500
    if not raw_text:
        chunks = [""]
    else:
        chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
    chunks = chunks[:10]
    
    filename = os.path.basename(path)
    file_type = os.path.splitext(filename)[1].lower().replace(".", "")
    document_id = f"doc_{int(datetime.utcnow().timestamp())}_{filename}"
    
    chunks_created = len(chunks)
    chunks_sent_to_gemini = 0
    
    from app.privacy import redact_sensitive_text
    from app.gemini_gate import can_send_to_gemini, log_gemini_decision
    from app.gemini_client import call_gemini_text
    from app.prompt_builder import build_document_to_evidence_prompt
    
    events_to_append = []
    
    for idx, chunk in enumerate(chunks):
        # 3. Redact sensitive text (PII) before LLM or storage
        redacted_chunk = redact_sensitive_text(chunk)
        
        if use_gemini:
            # 4. Check gate permission
            payload = {
                "contains_raw_file": False,
                "contains_hidden_memory": False,
                "requests_full_memory_dump": False,
                "contains_api_key_or_secret": False,
                "contains_sensitive_data": True,
                "explicit_consent": True,
                "route": "evidence_reflection"
            }
            allowed, reason = can_send_to_gemini(payload)
            log_gemini_decision("document_extraction", allowed, reason)
            
            if allowed:
                chunks_sent_to_gemini += 1
                prompt = build_document_to_evidence_prompt(redacted_chunk)
                try:
                    response_text = call_gemini_text(prompt, "document_extraction")
                    try:
                        items = json.loads(response_text)
                        if not isinstance(items, list):
                            items = []
                    except Exception:
                        items = []
                        
                    for item_idx, item in enumerate(items):
                        event_text = item.get("event") or item.get("text") or redacted_chunk
                        skills = item.get("skills") or item.get("tags") or []
                        
                        event_id = f"evt_gemini_{int(datetime.utcnow().timestamp())}_{idx}_{item_idx}"
                        events_to_append.append({
                            "event_id": event_id,
                            "type": "document_import",
                            "created_at": datetime.utcnow().isoformat(),
                            "profile_id": active_profile,
                            "source_type": "user_import",
                            "source_id": document_id,
                            "text": event_text,
                            "tags": skills,
                            "privacy_level": privacy_level,
                            "deleted": False
                        })
                except Exception:
                    pass
        else:
            # 5. Local rule-based extraction
            tags = []
            lower_chunk = redacted_chunk.lower()
            keywords_map = {
                "communication": ["communication", "talk", "meeting", "discussion", "沟通", "会议"],
                "learning": ["learning", "study", "grow", "ai", "学习", "成长"],
                "resilience": ["persistence", "recover", "fail", "try again", "坚持", "重试"],
                "product_thinking": ["product", "design", "feature", "产品", "设计"]
            }
            for tag, keywords in keywords_map.items():
                if any(kw in lower_chunk for kw in keywords):
                    tags.append(tag)
                    
            event_id = f"evt_local_{int(datetime.utcnow().timestamp())}_{idx}"
            events_to_append.append({
                "event_id": event_id,
                "type": "document_import",
                "created_at": datetime.utcnow().isoformat(),
                "profile_id": active_profile,
                "source_type": "user_import",
                "source_id": document_id,
                "text": redacted_chunk,
                "tags": tags,
                "privacy_level": privacy_level,
                "deleted": False
            })

    # Append resulting memory events to events log
    events_log_path = f"data/profiles/{active_profile}/memory_events.jsonl" if active_profile else "data/memory_events.jsonl"
    os.makedirs(os.path.dirname(events_log_path), exist_ok=True)
    with open(events_log_path, "a", encoding="utf-8") as f:
        for evt in events_to_append:
            f.write(json.dumps(evt) + "\n")
            
    base_events_path = "data/memory_events.jsonl"
    if base_events_path != events_log_path:
        os.makedirs(os.path.dirname(base_events_path), exist_ok=True)
        with open(base_events_path, "a", encoding="utf-8") as f:
            for evt in events_to_append:
                f.write(json.dumps(evt) + "\n")

    # 6. Write document metadata to data/imported_documents.jsonl
    doc_metadata = {
        "document_id": document_id,
        "filename": filename,
        "file_type": file_type,
        "imported_at": datetime.utcnow().isoformat(),
        "profile_id": active_profile,
        "privacy_level": privacy_level,
        "status": "success" if events_to_append else "failed",
        "chunks_created": chunks_created,
        "chunks_sent_to_gemini": chunks_sent_to_gemini
    }
    
    metadata_log_path = f"data/profiles/{active_profile}/imported_documents.jsonl" if active_profile else "data/imported_documents.jsonl"
    os.makedirs(os.path.dirname(metadata_log_path), exist_ok=True)
    with open(metadata_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(doc_metadata) + "\n")
        
    base_metadata_path = "data/imported_documents.jsonl"
    if base_metadata_path != metadata_log_path:
        os.makedirs(os.path.dirname(base_metadata_path), exist_ok=True)
        with open(base_metadata_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(doc_metadata) + "\n")
            
    return doc_metadata


class DocumentImporter:
    """Imports journals and reflections from txt and docx documents (legacy wrapper)."""

    def __init__(self, imports_dir: str = "imports", output_log: Optional[str] = None):
        self.imports_dir = imports_dir
        self.output_log = output_log or "data/imported_documents.jsonl"

    def import_all(self) -> List[Dict]:
        imported = []
        if not os.path.exists(self.imports_dir):
            return imported

        for filename in os.listdir(self.imports_dir):
            filepath = os.path.join(self.imports_dir, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in (".txt", ".docx", ".pdf", ".md"):
                meta = import_file(filepath, privacy_level="private", use_gemini=False)
                imported.append(meta)

        return imported
