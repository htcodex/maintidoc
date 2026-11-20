"""Contrôle d'accès documentaire.

Règle : un utilisateur voit un élément si et seulement si l'intersection entre ses groupes et les
`access_groups` de l'élément est non vide. La règle est appliquée :
  1. dans la requête à l'index (filtre Qdrant, avant toute récupération) — CP2 ;
  2. de nouveau sur chaque résultat avant de le renvoyer (défense en profondeur) ;
  3. à l'ouverture d'un fichier ou d'une image (`open_asset`).
Un refus ne révèle ni le titre ni l'existence du document.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from maintidoc.catalog import User

log = logging.getLogger("maintidoc.access")


class AccessDenied(Exception):
    """Accès refusé. Le message reste générique pour ne rien divulguer."""

    def __init__(self):
        super().__init__("Accès refusé.")


def can_read(user: User, access_groups) -> bool:
    return bool(set(user.groups) & set(access_groups))


@dataclass
class AccessLog:
    """Journal d'accès : métadonnées uniquement (utilisateur, objet, décision), jamais de contenu."""

    path: Path | None = None
    store: object | None = None   # PgMetadataStore : table access_events

    def record(self, user_id: str, action: str, target: str, allowed: bool):
        event = {"ts": round(time.time(), 3), "user": user_id, "action": action, "target": target, "allowed": allowed}
        log.info(json.dumps(event))
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        if self.store is not None and hasattr(self.store, "log_access"):
            self.store.log_access(user_id, action, target, allowed)


def open_asset(user: User, element_access_groups, asset, journal: AccessLog | None = None, store=None) -> bytes:
    """Lit un fichier (page, figure, photo) seulement si l'utilisateur y a droit.

    `asset` : chemin local (Path) ou clé relative lue dans `store` (S3 ou dossier local).
    """
    allowed = can_read(user, element_access_groups)
    if journal:
        journal.record(user.user_id, "open_asset", Path(str(asset)).name, allowed)
    if not allowed:
        raise AccessDenied()
    if store is not None:
        return store.read(str(asset))
    return Path(asset).read_bytes()
