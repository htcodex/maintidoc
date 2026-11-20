"""Configuration centrale (chemins, modèles, paramètres de recherche).

Toutes les valeurs peuvent être surchargées par variables d'environnement (voir .env.example).
Aucun secret ici.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:  # .env local (jamais commité) : secrets et URL des services docker compose
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    corpus_dir: Path = field(default_factory=lambda: Path(_env("MAINTIDOC_CORPUS_DIR", str(ROOT / "corpus"))))
    fixtures_dir: Path = field(default_factory=lambda: ROOT / "data" / "fixtures")
    index_dir: Path = field(default_factory=lambda: Path(_env("MAINTIDOC_INDEX_DIR", str(ROOT / "data" / "index"))))

    # Qdrant : chemin local (mode embarqué, sans Docker) ou URL d'un serveur (docker compose).
    qdrant_url: str = field(default_factory=lambda: _env("QDRANT_URL", ""))
    # PostgreSQL (métadonnées) et stockage S3 (fichiers) ; vides = SQLite et dossier local
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", ""))
    s3_endpoint: str = field(default_factory=lambda: _env("S3_ENDPOINT", ""))
    s3_bucket: str = field(default_factory=lambda: _env("S3_BUCKET", "maintidoc-assets"))
    s3_access_key: str = field(default_factory=lambda: _env("S3_ACCESS_KEY", ""), repr=False)
    s3_secret_key: str = field(default_factory=lambda: _env("S3_SECRET_KEY", ""), repr=False)

    # Modèles (révisions figées dans config/models.lock.yaml après téléchargement)
    text_model: str = field(default_factory=lambda: _env("MAINTIDOC_TEXT_MODEL", "BAAI/bge-m3"))
    image_model: str = field(default_factory=lambda: _env("MAINTIDOC_IMAGE_MODEL", "sentence-transformers/clip-ViT-B-32"))
    image_text_model: str = field(default_factory=lambda: _env(
        "MAINTIDOC_IMAGE_TEXT_MODEL", "sentence-transformers/clip-ViT-B-32-multilingual-v1"))
    reranker_model: str = field(default_factory=lambda: _env("MAINTIDOC_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"))
    ocr_languages: tuple = ("fr", "en")

    # Rendu des pages et des figures
    page_dpi: int = 110
    figure_dpi: int = 150
    ocr_dpi: int = 300

    # Recherche
    candidates_per_channel: int = 30
    rrf_k: int = 60
    rerank_top_n: int = 20
    # Poids RRF par canal : la requête texte -> CLIP est bruitée (pages entières), la photo jointe est forte.
    channel_weights: dict = field(default_factory=lambda: {"bm25": 1.0, "dense": 1.0, "image": 0.25, "photo": 1.0})
    superseded_weight: float = 0.5  # pénalité RRF des documents remplacés (ils restent visibles, signalés)

    @property
    def qdrant_path(self) -> Path:
        return self.index_dir / "qdrant"

    @property
    def metadata_db(self) -> Path:
        return self.index_dir / "metadata.sqlite"

    @property
    def assets_dir(self) -> Path:
        return self.index_dir / "assets"


def get_settings() -> Settings:
    return Settings()


def local_settings(**overrides) -> Settings:
    """Mode autonome sans services (tests, CI) : Qdrant embarqué, SQLite, fichiers locaux."""
    import dataclasses
    base = dict(qdrant_url="", database_url="", s3_endpoint="")
    return dataclasses.replace(Settings(), **{**base, **overrides})
