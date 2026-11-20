"""Catalogue du corpus : réunit inventaire.csv (registre officiel) et manifest.yaml (statut, versions, figures).

L'inventaire est la source de vérité pour les identifiants, les fichiers et les groupes d'accès.
Le manifeste apporte le statut (actif / remplacé), les liens de remplacement et l'empreinte SHA-256.
"""

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DocumentMeta:
    document_id: str
    file: Path
    title: str
    family: str                 # pompes | compresseurs | transverse
    equipment_ids: tuple[str, ...]
    doc_type: str
    version: str
    pages: int
    language: str
    format: str                 # pdf_texte | pdf_scanne | image
    access_groups: tuple[str, ...]
    usage_test: str
    status: str = "active"      # active | superseded
    supersedes: str | None = None
    superseded_by: str | None = None
    sha256: str | None = None
    confidentiality: str = "interne"
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def is_image(self) -> bool:
        return self.format == "image"


def manifest_key(manifest_id: str) -> str:
    """MDP-BT-2025-01 -> mdp_bt_2025_01 (identifiant de l'inventaire)."""
    return manifest_id.lower().replace("-", "_")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_catalog(corpus_dir: Path) -> list[DocumentMeta]:
    manifest = yaml.safe_load((corpus_dir / "manifest.yaml").read_text(encoding="utf-8"))
    by_key = {manifest_key(d["document_id"]): d for d in manifest["documents"]}
    docs = []
    with open(corpus_dir / "inventaire.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            m = by_key.get(row["document_id"], {})
            groups = tuple(g.strip() for g in row["groupe_acces"].split(";") if g.strip())
            equip = tuple(e.strip() for e in row["equipement_id"].split(";") if e.strip())
            docs.append(DocumentMeta(
                document_id=row["document_id"],
                file=corpus_dir / row["fichier"],
                title=row["titre"],
                family=row["famille_equipement"],
                equipment_ids=equip,
                doc_type=row["type_document"],
                version=row["version"].split(" ")[0],
                pages=int(row["nb_pages"]),
                language=row["langue"],
                format=row["format"],
                access_groups=groups,
                usage_test=row["usage_test"],
                status=m.get("status", "active"),
                supersedes=manifest_key(m["supersedes"]) if m.get("supersedes") else None,
                superseded_by=manifest_key(m["superseded_by"]) if m.get("superseded_by") else None,
                sha256=m.get("sha256"),
                confidentiality=m.get("confidentiality", "interne"),
                extra={"remarques": row["remarques"], "elements_visuels": row["elements_visuels"]},
            ))
    return docs


@dataclass(frozen=True)
class User:
    user_id: str
    role: str
    groups: tuple[str, ...]


def load_users(fixtures_dir: Path) -> dict[str, User]:
    data = yaml.safe_load((fixtures_dir / "users.yaml").read_text(encoding="utf-8"))
    return {u["user_id"]: User(u["user_id"], u["role"], tuple(u["groups"])) for u in data["users"]}
