"""Stockage des métadonnées (PostgreSQL ou SQLite) et des fichiers (S3 ou dossier local).

Le mode est choisi par la configuration :
  - DATABASE_URL défini  -> PostgreSQL (docker compose) ; sinon SQLite (data/index/metadata.sqlite) ;
  - S3_ENDPOINT défini   -> stockage objet S3 (SeaweedFS en local) ; sinon dossier data/index/assets.
Les deux implémentations ont la même interface : le reste du code ne sait pas laquelle il utilise.
"""

from __future__ import annotations

import json
from pathlib import Path

from maintidoc.ingestion.elements import Element

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY, title TEXT, family TEXT, doc_type TEXT, version TEXT, status TEXT,
  superseded_by TEXT, access_groups JSONB, confidentiality TEXT, file TEXT, sha256 TEXT, pages INTEGER,
  format TEXT, n_elements INTEGER);
CREATE TABLE IF NOT EXISTS elements (
  key TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(document_id) ON DELETE CASCADE,
  element_id TEXT, element_type TEXT, page INTEGER, heading TEXT, text TEXT, bbox JSONB, image_path TEXT,
  ocr BOOLEAN, access_groups TEXT[], payload JSONB);
CREATE INDEX IF NOT EXISTS elements_groups_idx ON elements USING GIN (access_groups);
CREATE INDEX IF NOT EXISTS elements_doc_idx ON elements (document_id);
CREATE TABLE IF NOT EXISTS index_runs (run_id TEXT PRIMARY KEY, created_at TIMESTAMPTZ, info JSONB);
CREATE TABLE IF NOT EXISTS access_events (
  id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), user_id TEXT, action TEXT, target TEXT, allowed BOOLEAN);
"""


class PgMetadataStore:
    """Même interface que retrieval.index.MetadataStore, sur PostgreSQL."""

    def __init__(self, url: str):
        self.url = url
        self.con = self._connect()
        with self.con.cursor() as cur:
            cur.execute(PG_SCHEMA)
        self.con.commit()

    def _connect(self):
        import psycopg
        # keepalive : la connexion reste ouverte pendant les calculs longs (reranker sur CPU)
        return psycopg.connect(self.url, keepalives=1, keepalives_idle=30, keepalives_interval=10,
                               keepalives_count=3)

    def _ensure(self):
        if self.con.closed or self.con.broken:
            self.con = self._connect()

    def reset(self):
        with self.con.cursor() as cur:
            cur.execute("TRUNCATE elements, documents")

    def add_document(self, meta, n_elements: int):
        with self.con.cursor() as cur:
            cur.execute("""INSERT INTO documents VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (document_id) DO UPDATE SET n_elements = EXCLUDED.n_elements""", (
                meta.document_id, meta.title, meta.family, meta.doc_type, meta.version, meta.status,
                meta.superseded_by, json.dumps(list(meta.access_groups)), meta.confidentiality, meta.file.name,
                meta.sha256, meta.pages, meta.format, n_elements))

    def add_elements(self, elements: list[Element]):
        with self.con.cursor() as cur:
            cur.executemany("""INSERT INTO elements VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                               ON CONFLICT (key) DO UPDATE SET payload = EXCLUDED.payload""", [
                (e.key, e.document_id, e.element_id, e.element_type, e.page, e.heading, e.text,
                 json.dumps(list(e.bbox)) if e.bbox else None, e.image_path, e.ocr, list(e.access_groups),
                 json.dumps(e.payload(), ensure_ascii=False)) for e in elements])

    def add_run(self, run_id: str, created_at: str, info: dict):
        with self.con.cursor() as cur:
            cur.execute("INSERT INTO index_runs VALUES (%s,%s,%s) ON CONFLICT (run_id) DO UPDATE SET "
                        "created_at = EXCLUDED.created_at, info = EXCLUDED.info", (run_id, created_at, json.dumps(info)))

    def commit(self):
        self.con.commit()

    def all_elements(self) -> list[Element]:
        with self.con.cursor() as cur:
            cur.execute("SELECT payload FROM elements ORDER BY key")
            return [Element.from_payload(r[0]) for r in cur.fetchall()]

    def get(self, key: str) -> Element | None:
        with self.con.cursor() as cur:
            cur.execute("SELECT payload FROM elements WHERE key = %s", (key,))
            r = cur.fetchone()
        return Element.from_payload(r[0]) if r else None

    def elements_for_groups(self, groups) -> list[str]:
        """Contrôle d'accès exprimé en SQL (utilisé pour vérifier la cohérence avec le filtre Qdrant)."""
        with self.con.cursor() as cur:
            cur.execute("SELECT key FROM elements WHERE access_groups && %s::text[]", (list(groups),))
            return [r[0] for r in cur.fetchall()]

    def last_run(self) -> dict | None:
        with self.con.cursor() as cur:
            cur.execute("SELECT run_id, created_at, info FROM index_runs ORDER BY created_at DESC LIMIT 1")
            r = cur.fetchone()
        return {"run_id": r[0], "created_at": r[1].isoformat(), **r[2]} if r else None

    def log_access(self, user_id, action, target, allowed):
        import psycopg
        for attempt in (1, 2):   # une reconnexion si le serveur a coupé une connexion inactive
            try:
                self._ensure()
                with self.con.cursor() as cur:
                    cur.execute("INSERT INTO access_events (user_id, action, target, allowed) "
                                "VALUES (%s,%s,%s,%s)", (user_id, action, target, allowed))
                self.con.commit()
                return
            except psycopg.OperationalError:
                if attempt == 2:
                    raise
                self.con = self._connect()

    def close(self):
        self.con.close()


def open_metadata_store(settings):
    if settings.database_url:
        return PgMetadataStore(settings.database_url)
    from maintidoc.retrieval.index import MetadataStore
    return MetadataStore(settings.metadata_db)


# ------------------------------------------------------------------ fichiers

class LocalAssetStore:
    kind = "local"

    def __init__(self, root: Path):
        self.root = root

    def put_dir(self, local_dir: Path) -> int:
        return sum(1 for p in local_dir.rglob("*") if p.is_file())   # déjà en place

    def read(self, rel_path: str) -> bytes:
        return (self.root / rel_path).read_bytes()

    def exists(self, rel_path: str) -> bool:
        return (self.root / rel_path).exists()


class S3AssetStore:
    """Pages, figures et photos dans un bucket S3 privé ; lecture uniquement via open_asset (droits vérifiés)."""

    kind = "s3"

    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str):
        import boto3
        from botocore.config import Config
        self.bucket = bucket
        self.s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key, region_name="us-east-1",
                               config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}))
        try:
            self.s3.head_bucket(Bucket=bucket)
        except Exception:
            self.s3.create_bucket(Bucket=bucket)

    def put_dir(self, local_dir: Path) -> int:
        n = 0
        for p in sorted(local_dir.rglob("*")):
            if p.is_file():
                self.s3.upload_file(str(p), self.bucket, p.relative_to(local_dir).as_posix(),
                                    ExtraArgs={"ContentType": "image/png"})
                n += 1
        return n

    def read(self, rel_path: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=rel_path)["Body"].read()

    def exists(self, rel_path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=rel_path)
            return True
        except Exception:
            return False


def open_asset_store(settings):
    if settings.s3_endpoint:
        return S3AssetStore(settings.s3_endpoint, settings.s3_bucket, settings.s3_access_key, settings.s3_secret_key)
    return LocalAssetStore(settings.assets_dir)
