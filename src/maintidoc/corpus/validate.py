"""Validation du manifeste de corpus : schéma, règles d'accès, cohérence et intégrité des fichiers.

Usage : python -m maintidoc.corpus.validate [corpus/manifest.yaml]
"""

import hashlib
import sys
from collections import Counter
from pathlib import Path

import yaml

from maintidoc.corpus.schema import Manifest

MIN_DOCS, MAX_DOCS = 30, 50
FORBIDDEN_GROUPS = {"MDP": {"grp_compresseurs"}, "MDC": {"grp_pompes"}}
# Pièges que le corpus doit contenir pour les tests de la semaine 5.
REQUIRED_FLAGS = {"injection", "contradiction", "superseded", "restricted", "ocr"}


def load_manifest(path: Path) -> Manifest:
    with open(path, encoding="utf-8") as f:
        return Manifest.model_validate(yaml.safe_load(f))


def check_manifest(manifest: Manifest, corpus_root: Path | None = None) -> list[str]:
    """Retourne la liste des erreurs (vide si le corpus est conforme)."""
    errors = []
    docs = manifest.documents
    by_id = {d.document_id: d for d in docs}

    if not MIN_DOCS <= len(docs) <= MAX_DOCS:
        errors.append(f"{len(docs)} documents : attendu entre {MIN_DOCS} et {MAX_DOCS}")
    for doc_id, n in Counter(d.document_id for d in docs).items():
        if n > 1:
            errors.append(f"identifiant dupliqué : {doc_id}")
    families = {d.equipment_family for d in docs}
    if not {"MDP", "MDC"} <= families:
        errors.append(f"les deux familles MDP et MDC doivent être couvertes (trouvé : {sorted(families)})")

    for d in docs:
        leaked = FORBIDDEN_GROUPS.get(d.equipment_family, set()) & set(d.access_groups)
        if leaked:
            errors.append(f"{d.document_id}: groupe non autorisé pour la famille {d.equipment_family} : {leaked}")
        if "grp_prestataires" in d.access_groups and d.doc_type not in ("securite", "glossaire"):
            errors.append(f"{d.document_id}: les prestataires n'ont accès qu'à la sécurité et au glossaire")
        if d.superseded_by:
            target = by_id.get(d.superseded_by)
            if target is None or target.supersedes != d.document_id:
                errors.append(f"{d.document_id}: superseded_by={d.superseded_by} sans lien réciproque")
        if d.supersedes:
            target = by_id.get(d.supersedes)
            if target is None or target.superseded_by != d.document_id:
                errors.append(f"{d.document_id}: supersedes={d.supersedes} sans lien réciproque")
        if d.scanned and "ocr" not in d.test_flags:
            errors.append(f"{d.document_id}: document scanné sans le marqueur 'ocr'")

    present = {flag for d in docs for flag in d.test_flags}
    for flag in sorted(REQUIRED_FLAGS - present):
        errors.append(f"aucun document ne porte le marqueur de test '{flag}'")

    if corpus_root is not None:
        for entry in [*docs, *manifest.photos]:
            path = corpus_root / entry.file
            if not path.exists():
                errors.append(f"fichier manquant : {entry.file}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != entry.sha256:
                errors.append(f"empreinte SHA-256 différente : {entry.file}")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("corpus/manifest.yaml")
    manifest = load_manifest(path)
    errors = check_manifest(manifest, corpus_root=path.parent)
    families = Counter(d.equipment_family for d in manifest.documents)
    print(f"{len(manifest.documents)} documents ({dict(families)}), {len(manifest.photos)} photos, "
          f"{sum(d.pages for d in manifest.documents)} pages, "
          f"{sum(len(d.figures) for d in manifest.documents)} figures")
    for e in errors:
        print(f"ERREUR  {e}")
    print("Manifeste conforme." if not errors else f"{len(errors)} erreur(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
