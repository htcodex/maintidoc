"""Index : Qdrant (vecteurs + payload filtrable) et base SQLite de métadonnées.

Deux collections Qdrant :
  - `elements_text`  : tous les éléments, vecteur BGE-M3 (1024) du texte enrichi ;
  - `elements_image` : éléments visuels (pages, figures, photos), vecteur CLIP (512) de l'image.
Le payload de chaque point contient les métadonnées complètes, dont `access_groups`, indexé en mot-clé
pour filtrer AVANT la récupération.

Qdrant tourne en mode embarqué (dossier local) par défaut, ou sur un serveur si QDRANT_URL est défini
(docker compose). Le mode embarqué rend la semaine 2 reproductible sans Docker.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models

from maintidoc.ingestion.elements import VISUAL_TYPES, Element

TEXT_COLLECTION = "elements_text"
IMAGE_COLLECTION = "elements_image"
NAMESPACE = uuid.UUID("6f1d3c1e-6a43-4f3a-9a52-0b6a0d0c2a11")


def point_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def open_client(settings) -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.qdrant_path))


def access_filter(groups, extra: list | None = None) -> models.Filter:
    must = [models.FieldCondition(key="access_groups", match=models.MatchAny(any=list(groups)))]
    return models.Filter(must=must + (extra or []))


def recreate_collections(client: QdrantClient, text_dim: int, image_dim: int, server: bool = False):
    for name, dim in ((TEXT_COLLECTION, text_dim), (IMAGE_COLLECTION, image_dim)):
        if client.collection_exists(name):
            client.delete_collection(name)
        client.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
        if not server:  # mode embarqué : le filtre fonctionne sans index de payload
            continue
        for field in ("access_groups", "document_id", "family", "element_type", "status"):
            client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)


def upsert(client: QdrantClient, collection: str, elements: list[Element], vectors):
    points = [models.PointStruct(id=point_id(e.key), vector=v.tolist(), payload=e.payload())
              for e, v in zip(elements, vectors)]
    for i in range(0, len(points), 64):
        client.upsert(collection, points[i:i + 64])


# ------------------------------------------------------------------ métadonnées (SQLite)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY, title TEXT, family TEXT, doc_type TEXT, version TEXT, status TEXT,
  superseded_by TEXT, access_groups TEXT, confidentiality TEXT, file TEXT, sha256 TEXT, pages INTEGER,
  format TEXT, n_elements INTEGER);
CREATE TABLE IF NOT EXISTS elements (
  key TEXT PRIMARY KEY, document_id TEXT, element_id TEXT, element_type TEXT, page INTEGER, heading TEXT,
  text TEXT, bbox TEXT, image_path TEXT, ocr INTEGER, payload TEXT);
CREATE TABLE IF NOT EXISTS index_runs (
  run_id TEXT PRIMARY KEY, created_at TEXT, info TEXT);
"""


class MetadataStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)

    def reset(self):
        self.con.executescript("DELETE FROM documents; DELETE FROM elements;")

    def add_document(self, meta, n_elements: int):
        self.con.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            meta.document_id, meta.title, meta.family, meta.doc_type, meta.version, meta.status, meta.superseded_by,
            json.dumps(list(meta.access_groups)), meta.confidentiality, str(meta.file.name), meta.sha256, meta.pages,
            meta.format, n_elements))

    def add_elements(self, elements: list[Element]):
        self.con.executemany("INSERT OR REPLACE INTO elements VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            (e.key, e.document_id, e.element_id, e.element_type, e.page, e.heading, e.text,
             json.dumps(list(e.bbox)) if e.bbox else None, e.image_path, int(e.ocr),
             json.dumps(e.payload(), ensure_ascii=False)) for e in elements])

    def add_run(self, run_id: str, created_at: str, info: dict):
        self.con.execute("INSERT OR REPLACE INTO index_runs VALUES (?,?,?)", (run_id, created_at, json.dumps(info)))

    def commit(self):
        self.con.commit()

    def all_elements(self) -> list[Element]:
        rows = self.con.execute("SELECT payload FROM elements ORDER BY key").fetchall()
        return [Element.from_payload(json.loads(r[0])) for r in rows]

    def get(self, key: str) -> Element | None:
        r = self.con.execute("SELECT payload FROM elements WHERE key=?", (key,)).fetchone()
        return Element.from_payload(json.loads(r[0])) if r else None

    def last_run(self) -> dict | None:
        r = self.con.execute("SELECT run_id, created_at, info FROM index_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return {"run_id": r[0], "created_at": r[1], **json.loads(r[2])} if r else None


def is_visual(e: Element) -> bool:
    return e.element_type in VISUAL_TYPES and bool(e.image_path)
