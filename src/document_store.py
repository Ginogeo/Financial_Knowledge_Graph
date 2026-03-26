import json
import os
import re
import uuid
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_ROOT = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_ROOT = os.path.join(BASE_DIR, "data", "processed")
REGISTRY_PATH = os.path.join(PROCESSED_ROOT, "document_registry.json")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "document"


def make_document_id(filename: str) -> str:
    stem, _ = os.path.splitext(filename)
    short_uuid = uuid.uuid4().hex[:8]
    return f"{_slugify(stem)}-{short_uuid}"


def load_registry() -> dict:
    if not os.path.exists(REGISTRY_PATH):
        return {}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def get_document_paths(document_id: str, filename: str) -> dict:
    raw_dir = os.path.join(RAW_ROOT, document_id)
    processed_dir = os.path.join(PROCESSED_ROOT, document_id)
    raw_pdf_path = os.path.join(raw_dir, filename)
    parsed_json_path = os.path.join(processed_dir, "parsed_sections.json")
    return {
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "raw_pdf_path": raw_pdf_path,
        "parsed_json_path": parsed_json_path,
    }


def upsert_document(document_id: str, name: str, filename: str, status: str, error: str = "", stats: Optional[dict] = None) -> None:
    registry = load_registry()
    existing = registry.get(document_id, {})
    paths = get_document_paths(document_id, filename)

    entry = {
        "id": document_id,
        "name": name,
        "filename": filename,
        "status": status,
        "error": error,
        "uploaded_at": existing.get("uploaded_at") or datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "raw_pdf_path": os.path.relpath(paths["raw_pdf_path"], BASE_DIR),
        "parsed_json_path": os.path.relpath(paths["parsed_json_path"], BASE_DIR),
        "stats": stats or existing.get("stats", {}),
    }
    registry[document_id] = entry
    save_registry(registry)


def list_documents() -> list:
    registry = load_registry()
    docs = list(registry.values())
    docs.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
    return docs


def get_document(document_id: str) -> Optional[dict]:
    return load_registry().get(document_id)


def get_latest_ready_document_id() -> Optional[str]:
    for doc in list_documents():
        if doc.get("status") == "READY":
            return doc.get("id")
    return None
