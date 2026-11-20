"""Élément indexé : la plus petite unité recherchable et citable du corpus."""

from dataclasses import asdict, dataclass, field

ELEMENT_TYPES = ("paragraph", "table", "figure", "page", "ocr_text", "photo")
# Éléments portant une image (canal visuel) ; les autres n'ont que du texte.
VISUAL_TYPES = ("figure", "page", "photo")


@dataclass
class Element:
    document_id: str
    element_id: str            # figure_1_1, table_2_1, paragraph_1_3, page_1, ocr_1_1, photo_1
    element_type: str
    page: int
    text: str                  # texte brut (affichage, BM25, reranker)
    heading: str = ""
    bbox: tuple[float, float, float, float] | None = None   # points PDF ; None pour une photo
    image_path: str | None = None   # chemin relatif à index_dir/assets
    ocr: bool = False
    # Métadonnées héritées du document (recopiées pour le filtrage dans l'index)
    version: str = ""
    title: str = ""
    family: str = ""
    equipment_ids: tuple[str, ...] = ()
    doc_type: str = ""
    status: str = "active"
    superseded_by: str | None = None
    access_groups: tuple[str, ...] = ()
    confidentiality: str = "interne"
    language: str = "fr"
    sha256: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Identifiant global, stable : document_id#element_id."""
        return f"{self.document_id}#{self.element_id}"

    @property
    def embed_text(self) -> str:
        """Texte enrichi du contexte (titre, page, rubrique) utilisé pour les embeddings."""
        head = f"{self.title} — p.{self.page}"
        if self.heading:
            head += f" — {self.heading}"
        return f"{head}\n{self.text}"

    def payload(self) -> dict:
        d = asdict(self)
        d["key"] = self.key
        d["equipment_ids"] = list(self.equipment_ids)
        d["access_groups"] = list(self.access_groups)
        d["bbox"] = list(self.bbox) if self.bbox else None
        return d

    @classmethod
    def from_payload(cls, d: dict) -> "Element":
        d = {k: v for k, v in d.items() if k != "key"}
        d["equipment_ids"] = tuple(d.get("equipment_ids") or ())
        d["access_groups"] = tuple(d.get("access_groups") or ())
        d["bbox"] = tuple(d["bbox"]) if d.get("bbox") else None
        return cls(**d)
